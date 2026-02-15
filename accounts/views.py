# accounts/views.py

import csv
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction
from django.contrib.auth import login as auth_login, authenticate, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model
from django.http import Http404, HttpResponseForbidden, StreamingHttpResponse
from django.db.models import Q, Count

from .forms import SignupWithProfileForm, CustomErrorList, ProfileEditForm
from .models import Profile

class Echo:
    """An object that implements write() to return the string its writer was given."""
    def write(self, value):
        return value

def _is_employer(user):
    return Profile.objects.filter(
        user=user,
        account_type=Profile.AccountType.EMPLOYER
    ).exists()


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
        success_rate = 0
        if user.apps_sent > 0:
            success_rate = (user.successful_hires / user.apps_sent) * 100
        
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
    
    rows.append([
        'PLATFORM TOTALS', '', '', '', '', 
        total_apps, total_jobs, total_hires, f"{platform_conversion:.1f}%"
    ])

    pseudo_buffer = Echo()
    writer = csv.writer(pseudo_buffer)
    response = StreamingHttpResponse(
        (writer.writerow(row) for row in rows),
        content_type="text/csv",
    )
    response['Content-Disposition'] = 'attachment; filename="platform_usage_report.csv"'
    return response

@login_required
def logout(request):
    auth_logout(request)
    return redirect("home.index")


def login(request):
    template_data = {"title": "Login"}
    if request.method == "GET":
        return render(request, "accounts/login.html", {"template_data": template_data})

    user = authenticate(
        request,
        username=request.POST["username"],
        password=request.POST["password"]
    )
    if user is None:
        template_data["error"] = "The username or password is incorrect."
        return render(request, "accounts/login.html", {"template_data": template_data})

    auth_login(request, user)
    return redirect("home.index")


def signup(request):
    template_data = {"title": "Sign Up"}

    if request.method == "GET":
        template_data["form"] = SignupWithProfileForm()
        return render(request, "accounts/signup.html", {"template_data": template_data})

    form = SignupWithProfileForm(request.POST, request.FILES, error_class=CustomErrorList)
    template_data["form"] = form

    if not form.is_valid():
        return render(request, "accounts/signup.html", {"template_data": template_data})

    with transaction.atomic():
        user = form.save()
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
            profile.headline = ""
            profile.skills = ""
            profile.education = ""
            profile.work_experience = ""
        else:
            profile.headline = form.cleaned_data.get("headline", "")
            profile.skills = form.cleaned_data.get("skills", "")
            profile.education = form.cleaned_data.get("education", "")
            profile.work_experience = form.cleaned_data.get("work_experience", "")
            profile.company_name = ""
            profile.company_website = ""
            profile.company_description = ""

        profile.save()

        for i in range(2):
            label = request.POST.get(f"link_label_{i}", "").strip()
            url = request.POST.get(f"link_url_{i}", "").strip()
            if url:
                profile.links.create(label=label, url=url)

    return redirect("accounts.login")


@login_required
def profile(request, user_id=None):
    User = get_user_model()

    if user_id:
        user_to_view = get_object_or_404(User, id=user_id)
        title = f"{user_to_view.username}'s Profile"
    else:
        user_to_view = request.user
        title = "My Profile"

    prof, _ = Profile.objects.get_or_create(user=user_to_view)
    is_own = (user_to_view == request.user)

    if not is_own:
        if prof.account_type != Profile.AccountType.APPLICANT:
            raise Http404("Profile not available.")
        if not prof.visible_to_recruiters:
            raise Http404("Profile not available.")

    template_data = {
        "title": title,
        "profile": prof,
        "viewed_user": user_to_view,
        "is_own_profile": is_own,
        "has_links": prof.links.exists(),
    }
    return render(request, "accounts/profile.html", {"template_data": template_data})


@login_required
def edit_profile(request, username=None):
    if username is not None and username != request.user.get_username():
        return HttpResponseForbidden("You can only edit your own profile.")

    profile, _ = Profile.objects.get_or_create(user=request.user)
    template_data = {"title": "Edit Profile"}
    template_data["highlight_account_type"] = request.GET.get("highlight") == "account_type"

    if request.method == "GET":
        template_data["form"] = ProfileEditForm(instance=profile)
        return render(request, "accounts/edit_profile.html", {"template_data": template_data})

    form = ProfileEditForm(request.POST, request.FILES, instance=profile)
    template_data["form"] = form

    if not form.is_valid():
        return render(request, "accounts/edit_profile.html", {"template_data": template_data})

    with transaction.atomic():
        prof = form.save(commit=False)
        prof.account_type = profile.account_type

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

    return redirect("accounts.profile")


@staff_member_required
def manage_users(request):
    query = request.GET.get('search', '').strip()
    profiles = Profile.objects.all().select_related('user')

    if query:
        profiles = profiles.filter(
            Q(user__username__icontains=query) | 
            Q(user__email__icontains=query)
        )

    template_data = {
        "title": "Manage Users",
        "users": profiles,
        "search_query": query,
    }
    return render(request, "accounts/manage_users.html", {"template_data": template_data})


@staff_member_required
def edit_user(request, user_id):
    template_data = {"title": "Edit User"}
    profile = get_object_or_404(Profile, id=user_id)
    template_data["user"] = profile

    if profile.user.is_superuser and not request.user.is_superuser:
        return redirect("accounts.manage_users")

    if request.method == "GET":
        template_data["form"] = ProfileEditForm(instance=profile)
        return render(request, "accounts/edit_user.html", {"template_data": template_data})

    form = ProfileEditForm(request.POST, request.FILES, instance=profile)
    template_data["form"] = form

    if not form.is_valid():
        return render(request, "accounts/edit_user.html", {"template_data": template_data})

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

    return redirect("accounts.manage_users")

@staff_member_required
def remove_user(request, user_id):
    if request.method == "POST":
        prof = Profile.objects.get(id=user_id)
        prof.user.delete()
    return redirect("accounts.manage_users")


def public_profile(request, username):
    User = get_user_model()
    user = get_object_or_404(User, username=username)
    profile, _ = Profile.objects.get_or_create(user=user)

    is_owner = request.user.is_authenticated and request.user == user

    if profile.account_type != Profile.AccountType.APPLICANT:
        raise Http404("Profile not available.")

    if not is_owner and not profile.visible_to_recruiters:
        raise Http404("Profile not available.")

    template_data = {
        "title": f"{user.username} Profile",
        "profile": profile,
        "public_view": True,
        "is_owner": is_owner,
        "has_links": profile.links.exists(),
    }
    return render(request, "accounts/public_profile.html", {"template_data": template_data})


@login_required
def candidate_search(request):
    if not _is_employer(request.user):
        return HttpResponseForbidden("Only employers can access candidate search.")

    template_data = {"title": "Candidate Search"}

    qs = Profile.objects.filter(
        account_type=Profile.AccountType.APPLICANT,
        visible_to_recruiters=True,
    ).select_related("user").order_by("user__username")

    skills = request.GET.get("skills", "").strip()
    location = request.GET.get("location", "").strip()
    projects = request.GET.get("projects", "").strip()

    if skills:
        terms = [t.strip() for t in skills.split(",") if t.strip()]
        for t in terms:
            qs = qs.filter(skills__icontains=t)

    if location:
        qs = qs.filter(location__icontains=location)

    if projects:
        qs = qs.filter(Q(projects__icontains=projects) | Q(headline__icontains=projects))

    template_data["candidates"] = qs
    template_data["filters"] = {"skills": skills, "location": location, "projects": projects}

    return render(request, "accounts/candidate_search.html", {"template_data": template_data})
