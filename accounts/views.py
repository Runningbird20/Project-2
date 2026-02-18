import csv
import json
from collections import Counter
from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction
from django.conf import settings
from django.contrib.auth import login as auth_login, authenticate, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth import get_user_model
from django.http import Http404, HttpResponseForbidden, StreamingHttpResponse
from django.db.models import Q, Count
from django.contrib import messages
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

from .forms import SignupWithProfileForm, CustomErrorList, ProfileEditForm
from .models import Profile, SavedCandidateSearch
from map.services import OfficeLocationGeocodingError, geocode_office_address

class Echo:
    """An object that implements write() to return the string its writer was given."""
    def write(self, value):
        return value

def _is_employer(user):
    return Profile.objects.filter(
        user=user,
        account_type=Profile.AccountType.EMPLOYER
    ).exists()


superuser_required = user_passes_test(lambda u: u.is_authenticated and u.is_superuser)

@staff_member_required
def export_usage_report(request):
    User = get_user_model()
    users = User.objects.select_related('profile').annotate(
        apps_sent=Count('application', distinct=True),
        jobs_posted=Count('job_posts', distinct=True), 
        successful_hires=Count(
            'application', 
            filter=Q(application__status__in=['offer', 'closed']), 
            distinct=True
        )
    )

    rows = []
    rows.append([
        'Full Name', 'Email', 'Account Type', 'Date Joined', 
        'Last Login', 'Apps Sent', 'Jobs Posted', 'Successful Hires', 'Success Rate %'
    ])

    total_apps = 0
    total_jobs = 0
    total_hires = 0

    for user in users:
        success_rate = (user.successful_hires / user.apps_sent * 100) if user.apps_sent > 0 else 0
        total_apps += user.apps_sent
        total_jobs += user.jobs_posted
        total_hires += user.successful_hires

        rows.append([
            user.get_full_name() or user.username,
            user.email,
            user.profile.get_account_type_display() if hasattr(user, 'profile') else 'N/A',
            user.date_joined.strftime('%Y-%m-%d'),
            user.last_login.strftime('%Y-%m-%d') if user.last_login else 'Never',
            user.apps_sent,
            user.jobs_posted,
            user.successful_hires,
            f"{success_rate:.1f}%"
        ])

    rows.append([''] * 9) 
    platform_conversion = (total_hires / total_apps * 100) if total_apps > 0 else 0
    rows.append(['PLATFORM TOTALS', '', '', '', '', total_apps, total_jobs, total_hires, f"{platform_conversion:.1f}%"])

    pseudo_buffer = Echo()
    writer = csv.writer(pseudo_buffer)
    response = StreamingHttpResponse((writer.writerow(row) for row in rows), content_type="text/csv")
    response['Content-Disposition'] = 'attachment; filename="platform_usage_report.csv"'
    return response


@staff_member_required
def send_test_email(request):
    if request.method != "POST":
        return redirect("accounts.manage_users")

    recipient = (request.POST.get("test_email_to") or "").strip()
    if not recipient:
        messages.error(request, "Provide a recipient email.")
        return redirect("accounts.manage_users")

    try:
        validate_email(recipient)
    except ValidationError:
        messages.error(request, "Enter a valid recipient email.")
        return redirect("accounts.manage_users")

    try:
        sender = (settings.EMAIL_HOST_USER or settings.DEFAULT_FROM_EMAIL or "no-reply@pandapulse.local").strip()
        sent_count = send_mail(
            subject="PandaPulse test email",
            message=(
                "This is a test email from PandaPulse.\n\n"
                "If you received this message, SMTP delivery is working."
            ),
            from_email=sender,
            recipient_list=[recipient],
            fail_silently=False,
        )
    except Exception as exc:
        messages.error(request, f"Test email failed: {exc}")
        return redirect("accounts.manage_users")

    if sent_count < 1:
        messages.error(
            request,
            f"Test email was not accepted by the backend (from: {sender}, to: {recipient}).",
        )
        return redirect("accounts.manage_users")

    messages.success(request, f"Test email queued (from: {sender}, to: {recipient}).")
    return redirect("accounts.manage_users")

@login_required
def logout(request):
    auth_logout(request)
    messages.info(request, "You have been logged out.")
    return redirect("home.index")

def login(request):
    template_data = {"title": "Login"}
    if request.method == "GET":
        return render(request, "accounts/login.html", {"template_data": template_data})

    user = authenticate(request, username=request.POST["username"], password=request.POST["password"])
    if user is None:
        template_data["error"] = "The username or password is incorrect."
        return render(request, "accounts/login.html", {"template_data": template_data})

    auth_login(request, user)
    messages.success(request, f"Welcome back, {user.username}!")
    return redirect("home.index")


def forgot_username(request):
    template_data = {"title": "Forgot Username"}
    if request.method == "GET":
        return render(request, "accounts/forgot_username.html", {"template_data": template_data})

    email = request.POST.get("email", "").strip()
    if email:
        user_model = get_user_model()
        matches = user_model.objects.filter(email__iexact=email).order_by("username")
        if matches.exists():
            usernames = ", ".join([u.username for u in matches])
            send_mail(
                subject="Your PandaPulse username reminder",
                message=(
                    "You requested your PandaPulse username.\n\n"
                    f"Username(s) for this email: {usernames}\n\n"
                    "If you did not request this, you can ignore this email."
                ),
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@pandapulse.local"),
                recipient_list=[email],
                fail_silently=True,
            )

    messages.info(
        request,
        "If that email exists in our system, we sent your username reminder."
    )
    return redirect("accounts.login")

def signup(request):
    template_data = {"title": "Sign Up"}
    if request.method == "GET":
        template_data["form"] = SignupWithProfileForm()
        return render(request, "accounts/signup.html", {"template_data": template_data})

    form = SignupWithProfileForm(request.POST, request.FILES, error_class=CustomErrorList)
    if not form.is_valid():
        template_data["form"] = form
        return render(request, "accounts/signup.html", {"template_data": template_data})

    with transaction.atomic():
        user = form.save()
        user.email = form.cleaned_data.get("email", "")
        user.save(update_fields=["email"])
        profile, _ = Profile.objects.get_or_create(user=user)
        acct = form.cleaned_data.get("account_type", Profile.AccountType.APPLICANT)
        
        profile.account_type = acct
        profile.profile_picture = form.cleaned_data.get("profile_picture")
        profile.location = form.cleaned_data.get("location", "")
        profile.projects = form.cleaned_data.get("projects", "")

        if acct == Profile.AccountType.EMPLOYER:
            profile.company_name = form.cleaned_data.get("company_name", "")
            profile.company_website = form.cleaned_data.get("company_website", "")
            profile.company_description = form.cleaned_data.get("company_description", "")
            profile.headline = profile.skills = profile.education = profile.work_experience = ""
        else:
            profile.headline = form.cleaned_data.get("headline", "")
            profile.skills = form.cleaned_data.get("skills", "")
            profile.education = form.cleaned_data.get("education", "")
            profile.work_experience = form.cleaned_data.get("work_experience", "")
            profile.company_name = profile.company_website = profile.company_description = ""

        profile.save()
        for i in range(2):
            label = request.POST.get(f"link_label_{i}", "").strip()
            url = request.POST.get(f"link_url_{i}", "").strip()
            if url: profile.links.create(label=label, url=url)

    messages.success(request, "Account created! Please log in.")
    return redirect("accounts.login")

@login_required
def profile(request, user_id=None):
    User = get_user_model()
    user_to_view = get_object_or_404(User, id=user_id) if user_id else request.user
    prof, _ = Profile.objects.get_or_create(user=user_to_view)
    is_own = (user_to_view == request.user)

    if not is_own:
        if prof.account_type != Profile.AccountType.APPLICANT or not prof.visible_to_recruiters:
            raise Http404("Profile not available.")

    template_data = {
        "title": f"{user_to_view.username}'s Profile" if user_id else "My Profile",
        "profile": prof,
        "viewed_user": user_to_view,
        "is_own_profile": is_own,
        "has_links": prof.links.exists(),
    }
    return render(request, "accounts/profile.html", {"template_data": template_data})

@login_required
def edit_profile(request, username=None):
    if username and username != request.user.get_username():
        return HttpResponseForbidden("You can only edit your own profile.")

    profile, _ = Profile.objects.get_or_create(user=request.user)
    
    if request.method == "POST":
        form = ProfileEditForm(request.POST, request.FILES, instance=profile, user=request.user)
        if form.is_valid():
            with transaction.atomic():
                prof = form.save(commit=False)
                
                if prof.account_type == Profile.AccountType.EMPLOYER:
                    prof.headline = ""
                    prof.skills = ""
                    prof.education = ""
                    prof.work_experience = ""
                else:
                    prof.company_name = ""
                    prof.company_website = ""
                    prof.company_description = ""
                
                prof.save()
                submitted_email = (form.cleaned_data.get("email") or "").strip()
                if submitted_email and submitted_email != request.user.email:
                    request.user.email = submitted_email
                    request.user.save(update_fields=["email"])
                messages.success(request, "Profile updated successfully!")
                return redirect("accounts.profile")
    else:
        form = ProfileEditForm(instance=profile, user=request.user)

    return render(request, "accounts/edit_profile.html", {"template_data": {"title": "Edit Profile", "form": form}})

@superuser_required
def manage_users(request):
    query = request.GET.get('search', '').strip()
    profiles = Profile.objects.all().select_related('user')
    if query:
        profiles = profiles.filter(Q(user__username__icontains=query) | Q(user__email__icontains=query))
    return render(request, "accounts/manage_users.html", {"template_data": {"title": "Manage Users", "users": profiles, "search_query": query}})

@superuser_required
def edit_user(request, user_id):
    profile = get_object_or_404(Profile, id=user_id)
    if profile.user.is_superuser and not request.user.is_superuser:
        return redirect("accounts.manage_users")

    if request.method == "POST":
        form = ProfileEditForm(request.POST, request.FILES, instance=profile, user=profile.user)
        if form.is_valid():
            with transaction.atomic():
                prof = form.save(commit=False)
                
                if prof.account_type == Profile.AccountType.EMPLOYER:
                    prof.headline = ""
                    prof.skills = ""
                    prof.education = ""
                    prof.work_experience = ""
                else:
                    prof.company_name = ""
                    prof.company_website = ""
                    prof.company_description = ""
                
                prof.save()
                submitted_email = (form.cleaned_data.get("email") or "").strip()
                if submitted_email and submitted_email != profile.user.email:
                    profile.user.email = submitted_email
                    profile.user.save(update_fields=["email"])
                messages.success(request, f"User {profile.user.username} updated.")
                return redirect("accounts.manage_users")
    else:
        form = ProfileEditForm(instance=profile, user=profile.user)

    return render(request, "accounts/edit_user.html", {"template_data": {"title": "Edit User", "form": form, "user": profile}})
@superuser_required
def remove_user(request, user_id):
    if request.method == "POST":
        prof = get_object_or_404(Profile, id=user_id)
        username = prof.user.username
        prof.user.delete()
        messages.warning(request, f"User {username} has been deleted.")
    return redirect("accounts.manage_users")

def public_profile(request, username):
    User = get_user_model()
    user = get_object_or_404(User, username=username)
    profile, _ = Profile.objects.get_or_create(user=user)
    is_owner = request.user.is_authenticated and request.user == user

    if profile.account_type != Profile.AccountType.APPLICANT or (not is_owner and not profile.visible_to_recruiters):
        raise Http404("Profile not available.")

    return render(request, "accounts/public_profile.html", {"template_data": {"title": f"{user.username} Profile", "profile": profile, "public_view": True, "is_owner": is_owner, "has_links": profile.links.exists()}})

@login_required
def candidate_search(request):
    if not _is_employer(request.user):
        return HttpResponseForbidden("Only employers can access candidate search.")

    qs = Profile.objects.filter(account_type=Profile.AccountType.APPLICANT, visible_to_recruiters=True).select_related("user").order_by("user__username")
    skills = request.GET.get("skills", "").strip()
    location = request.GET.get("location", "").strip()
    projects = request.GET.get("projects", "").strip()

    if skills:
        for t in [t.strip() for t in skills.split(",") if t.strip()]:
            qs = qs.filter(skills__icontains=t)
    if location: qs = qs.filter(location__icontains=location)
    if projects: qs = qs.filter(Q(projects__icontains=projects) | Q(headline__icontains=projects))

    return render(request, "accounts/candidate_search.html", {"template_data": {"title": "Candidate Search", "candidates": qs, "filters": {"skills": skills, "location": location, "projects": projects}}})

@login_required
def save_candidate_search(request):
    if request.method == 'POST':
        SavedCandidateSearch.objects.create(
            employer=request.user,
            search_name=request.POST.get('search_name'),
            filters={'skills': request.POST.get('skills', ''), 'location': request.POST.get('location', ''), 'projects': request.POST.get('projects', '')}
        )
        messages.success(request, 'Alert created successfully!')
    return redirect('jobposts.dashboard')

@login_required
def delete_candidate_search(request, search_id):
    search = get_object_or_404(SavedCandidateSearch, id=search_id, employer=request.user)
    if request.method == 'POST':
        name = search.search_name
        search.delete()
        messages.warning(request, f'Alert "{name}" deleted.')
    return redirect('jobposts.dashboard')


@staff_member_required
def applicant_clusters_map(request):
    applicants = Profile.objects.filter(
        account_type=Profile.AccountType.APPLICANT
    ).select_related('user')

    location_counts = Counter()
    for profile in applicants:
        city_state = profile.location_city_state
        if city_state:
            location_counts[city_state] += 1

    clusters = []
    for location_name, applicant_count in location_counts.most_common():
        try:
            latitude, longitude = geocode_office_address(location_name)
        except OfficeLocationGeocodingError:
            continue

        clusters.append(
            {
                "location": location_name,
                "count": applicant_count,
                "latitude": float(latitude),
                "longitude": float(longitude),
            }
        )

    template_data = {
        "title": "Applicant Clusters Map",
        "total_applicants": applicants.count(),
        "cluster_count": len(clusters),
    }
    return render(
        request,
        "accounts/applicant_clusters_map.html",
        {"template_data": template_data, "clusters": clusters},
    )
