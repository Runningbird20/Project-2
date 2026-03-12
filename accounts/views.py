import csv
from collections import Counter
from smtplib import SMTPAuthenticationError

from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import views as auth_views
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.db import IntegrityError
from django.db import transaction
from django.db.models import Count, Q
from django.http import Http404, HttpResponseForbidden, StreamingHttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import ensure_csrf_cookie

from django.core.mail import EmailMessage

from map.services import OfficeLocationGeocodingError, geocode_office_address
from project2.skills import COMMON_SKILLS
from interviews.services import build_skill_badges_for_applicant
from apply.models import Application

from .forms import CompanyProfileForm, CustomErrorList, ProfileEditForm, SignupWithProfileForm
from .models import Profile, SavedCandidateSearch
from jobposts.models import JobPost


class Echo:
    def write(self, value):
        return value


@method_decorator(never_cache, name="dispatch")
@method_decorator(ensure_csrf_cookie, name="dispatch")
class SafePasswordResetView(auth_views.PasswordResetView):
    pass


@method_decorator(never_cache, name="dispatch")
@method_decorator(ensure_csrf_cookie, name="dispatch")
class SafePasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    pass


def _is_employer(user):
    return Profile.objects.filter(
        user=user,
        account_type=Profile.AccountType.EMPLOYER,
    ).exists()


def _is_applicant(user):
    return Profile.objects.filter(
        user=user,
        account_type=Profile.AccountType.APPLICANT,
    ).exists()


def _format_response_time_window(avg_hours):
    if avg_hours < 24:
        rounded_hours = max(1, int(round(avg_hours)))
        label = "hour" if rounded_hours == 1 else "hours"
        return f"~{rounded_hours} {label}"
    rounded_days = max(1, int(round(avg_hours / 24)))
    label = "day" if rounded_days == 1 else "days"
    return f"~{rounded_days} {label}"


def _response_sla_tone(avg_hours):
    if avg_hours < 49:
        return "green"
    if avg_hours > 7 * 24:
        return "red"
    return "yellow"


def _build_response_sla(avg_hours):
    if avg_hours is None:
        return {
            "label": "Response time unavailable",
            "css_class": "is-neutral",
            "hours": None,
        }
    return {
        "label": f"Responds in {_format_response_time_window(avg_hours)}",
        "css_class": f"is-{_response_sla_tone(avg_hours)}",
        "hours": round(avg_hours, 1),
    }


def _build_response_sla_by_employer_ids(employer_ids):
    owner_ids = [owner_id for owner_id in employer_ids if owner_id]
    if not owner_ids:
        return {}

    aggregates = {owner_id: {"total_hours": 0.0, "count": 0} for owner_id in owner_ids}
    response_rows = Application.objects.filter(
        job__owner_id__in=owner_ids,
        responded_at__isnull=False,
    ).values_list("job__owner_id", "applied_at", "responded_at")

    for owner_id, applied_at, responded_at in response_rows:
        if not applied_at or not responded_at or responded_at < applied_at:
            continue
        delta_hours = (responded_at - applied_at).total_seconds() / 3600
        bucket = aggregates[owner_id]
        bucket["total_hours"] += delta_hours
        bucket["count"] += 1

    sla_by_owner = {}
    for owner_id in owner_ids:
        bucket = aggregates[owner_id]
        avg_hours = None
        if bucket["count"] > 0:
            avg_hours = bucket["total_hours"] / bucket["count"]
        sla_by_owner[owner_id] = _build_response_sla(avg_hours)
    return sla_by_owner


superuser_required = user_passes_test(lambda u: u.is_authenticated and u.is_superuser)


@staff_member_required
def export_usage_report(request):
    User = get_user_model()
    users = User.objects.select_related("profile").annotate(
        apps_sent=Count("application", distinct=True),
        jobs_posted=Count("job_posts", distinct=True),
        successful_hires=Count(
            "application",
            filter=Q(application__status__in=["offer", "closed"]),
            distinct=True,
        ),
    )

    rows = [[
        "Full Name", "Email", "Account Type", "Date Joined",
        "Last Login", "Apps Sent", "Jobs Posted", "Successful Hires", "Success Rate %",
    ]]

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
            user.profile.get_account_type_display() if hasattr(user, "profile") else "N/A",
            user.date_joined.strftime("%Y-%m-%d"),
            user.last_login.strftime("%Y-%m-%d") if user.last_login else "Never",
            user.apps_sent,
            user.jobs_posted,
            user.successful_hires,
            f"{success_rate:.1f}%",
        ])

    rows.append([""] * 9)
    platform_conversion = (total_hires / total_apps * 100) if total_apps > 0 else 0
    rows.append(["PLATFORM TOTALS", "", "", "", "", total_apps, total_jobs, total_hires, f"{platform_conversion:.1f}%"])

    pseudo_buffer = Echo()
    writer = csv.writer(pseudo_buffer)
    response = StreamingHttpResponse((writer.writerow(row) for row in rows), content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="platform_usage_report.csv"'
    return response


@superuser_required
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
            message="This is a test email from PandaPulse.\n\nIf you received this, SMTP delivery is working.",
            from_email=sender,
            recipient_list=[recipient],
            fail_silently=False,
        )
    except Exception as exc:
        messages.error(request, f"Test email failed: {exc}")
        return redirect("accounts.manage_users")

    if sent_count < 1:
        messages.error(request, f"Test email was not accepted by backend (from: {sender}, to: {recipient}).")
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
        User = get_user_model()
        matches = User.objects.filter(email__iexact=email).order_by("username")
        if matches.exists():
            usernames = ", ".join([u.username for u in matches])
            send_mail(
                subject="Your PandaPulse Username Request",
                message=(
                    "Hi,\n\n"
                    "We received a request to retrieve the username associated with this "
                    "email address for PandaPulse.\n\n"
                    "Username(s) linked to this email:\n"
                    f"{usernames}\n\n"
                    "If you submitted this request, you can use the username above to sign "
                    "in to your account. If you did not request your username, no action is "
                    "needed and you may safely ignore this message.\n\n"
                    "If you continue to experience trouble accessing your account, please "
                    "contact our support team for assistance.\n\n"
                    "Thank you,\n"
                    "The PandaPulse Team\n"
                ),
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@pandapulse.local"),
                recipient_list=[email],
                fail_silently=True,
            )

    messages.info(request, "If that email exists in our system, we sent your username reminder.")
    return redirect("accounts.login")


def signup(request):
    template_data = {"title": "Sign Up"}
    if request.method == "GET":
        template_data["form"] = SignupWithProfileForm()
        template_data["skill_options"] = COMMON_SKILLS
        return render(request, "accounts/signup.html", {"template_data": template_data})

    form = SignupWithProfileForm(request.POST, request.FILES, error_class=CustomErrorList)
    if not form.is_valid():
        template_data["form"] = form
        template_data["skill_options"] = COMMON_SKILLS
        return render(request, "accounts/signup.html", {"template_data": template_data})

    acct = form.cleaned_data.get("account_type", Profile.AccountType.APPLICANT)
    location_value = (form.cleaned_data.get("location") or "").strip()
    address_line_1 = (form.cleaned_data.get("address_line_1") or "").strip()
    address_line_2 = (form.cleaned_data.get("address_line_2") or "").strip()
    city = (form.cleaned_data.get("city") or "").strip()
    state = (form.cleaned_data.get("state") or "").strip()
    postal_code = (form.cleaned_data.get("postal_code") or "").strip()
    country = (form.cleaned_data.get("country") or "").strip() or "United States"
    if acct == Profile.AccountType.APPLICANT:
        if not location_value:
            form.add_error("address_line_1", "Address is required for applicants.")
            template_data["form"] = form
            template_data["skill_options"] = COMMON_SKILLS
            return render(request, "accounts/signup.html", {"template_data": template_data})
        try:
            geocode_office_address(location_value)
        except OfficeLocationGeocodingError as exc:
            form.add_error("address_line_1", str(exc))
            template_data["form"] = form
            template_data["skill_options"] = COMMON_SKILLS
            return render(request, "accounts/signup.html", {"template_data": template_data})

    try:
        with transaction.atomic():
            user = form.save()
            user.email = form.cleaned_data.get("email", "")
            user.save(update_fields=["email"])

            profile, _ = Profile.objects.get_or_create(user=user)
            profile.account_type = acct
            profile.profile_picture = form.cleaned_data.get("profile_picture")
            profile.location = location_value
            profile.address_line_1 = address_line_1
            profile.address_line_2 = address_line_2
            profile.city = city
            profile.state = state
            profile.postal_code = postal_code
            profile.country = country
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
                if url:
                    profile.links.create(label=label, url=url)
    except IntegrityError:
        form.add_error("username", "This username is already taken.")
        template_data["form"] = form
        template_data["skill_options"] = COMMON_SKILLS
        return render(request, "accounts/signup.html", {"template_data": template_data})

    if user.email:
        try:
            send_mail(
                subject="Welcome to PandaPulse",
                message=(
                    f"Hi {user.username},\n\n"
                    "Your PandaPulse account has been successfully created, and we are "
                    "excited to have you on board.\n\n"
                    "You can now log in to your account and start exploring everything "
                    "PandaPulse has to offer. Be sure to complete your profile and "
                    "customize your settings to get the most out of the platform.\n\n"
                    "If you have any questions or need assistance getting started, our "
                    "support team is here to help.\n\n"
                    "Welcome to PandaPulse,\n"
                    "The PandaPulse Team\n"
                ),
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@pandapulse.local"),
                recipient_list=[user.email],
                fail_silently=False,
            )
        except SMTPAuthenticationError:
            messages.warning(
                request,
                "Account confirmation email could not be sent: Gmail authentication failed. "
                "Use a valid 16-character Google App Password (not your normal Gmail password).",
            )
        except Exception as exc:
            if settings.DEBUG:
                messages.warning(request, f"Account confirmation email could not be sent: {exc}")
            else:
                messages.warning(request, "Account confirmation email could not be sent.")

    authenticated_user = authenticate(
        request,
        username=user.username,
        password=form.cleaned_data.get("password1"),
    )
    if authenticated_user is not None:
        auth_login(request, authenticated_user)
        messages.success(request, "Account created! You're now signed in.")
        if acct == Profile.AccountType.EMPLOYER:
            return redirect("jobposts.dashboard")
        return redirect("apply:application_status")

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
    if prof.account_type == Profile.AccountType.APPLICANT:
        template_data["skill_badges"] = build_skill_badges_for_applicant(user_to_view)
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
                    prof.headline = prof.skills = prof.education = prof.work_experience = ""

                prof.save()

                submitted_email = (form.cleaned_data.get("email") or "").strip()
                if submitted_email and submitted_email != request.user.email:
                    request.user.email = submitted_email
                    request.user.save(update_fields=["email"])

                messages.success(request, "Profile updated successfully!")
                return redirect("accounts.profile")
    else:
        form = ProfileEditForm(instance=profile, user=request.user)

    return render(
        request,
        "accounts/edit_profile.html",
        {"template_data": {"title": "Edit Profile", "form": form, "skill_options": COMMON_SKILLS}},
    )


@superuser_required
def manage_users(request):
    query = request.GET.get("search", "").strip()
    profiles = Profile.objects.select_related("user").all()
    if query:
        profiles = profiles.filter(Q(user__username__icontains=query) | Q(user__email__icontains=query))
    return render(
        request,
        "accounts/manage_users.html",
        {"template_data": {"title": "Manage Users", "users": profiles, "search_query": query}},
    )


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
                    prof.headline = prof.skills = prof.education = prof.work_experience = ""

                prof.save()

                submitted_email = (form.cleaned_data.get("email") or "").strip()
                if submitted_email and submitted_email != profile.user.email:
                    profile.user.email = submitted_email
                    profile.user.save(update_fields=["email"])

                messages.success(request, f"User {profile.user.username} updated.")
                return redirect("accounts.manage_users")
    else:
        form = ProfileEditForm(instance=profile, user=profile.user)

    return render(
        request,
        "accounts/edit_user.html",
        {"template_data": {"title": "Edit User", "form": form, "user": profile}},
    )


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

    return render(
        request,
        "accounts/public_profile.html",
        {
            "template_data": {
                "title": f"{user.username} Profile",
                "profile": profile,
                "public_view": True,
                "is_owner": is_owner,
                "has_links": profile.links.exists(),
                "skill_badges": build_skill_badges_for_applicant(user),
            }
        },
    )


@login_required
def candidate_search(request):
    if not _is_employer(request.user):
        return HttpResponseForbidden("Only employers can access candidate search.")

    qs = Profile.objects.filter(
        account_type=Profile.AccountType.APPLICANT,
        visible_to_recruiters=True,
    ).select_related("user").order_by("user__username")

    skills = request.GET.get("skills", "").strip()
    location = request.GET.get("location", "").strip()
    projects = request.GET.get("projects", "").strip()

    if skills:
        for t in [t.strip() for t in skills.split(",") if t.strip()]:
            qs = qs.filter(skills__icontains=t)
    if location:
        qs = qs.filter(
            Q(location__icontains=location)
            | Q(city__icontains=location)
            | Q(state__icontains=location)
            | Q(address_line_1__icontains=location)
        )
    if projects:
        qs = qs.filter(Q(projects__icontains=projects) | Q(headline__icontains=projects))

    candidates = list(qs)

    def _skill_set(raw_value):
        if not raw_value:
            return set()
        return {token.strip().lower() for token in raw_value.split(",") if token.strip()}

    employer_jobs = list(
        JobPost.objects.filter(owner=request.user)
        .only("title", "skills", "created_at")
        .order_by("-created_at")
    )
    job_skill_sets = [(job, _skill_set(job.skills)) for job in employer_jobs]

    for candidate in candidates:
        best_job = None
        best_score = 0
        candidate_skills = _skill_set(candidate.skills)
        for job, job_skills in job_skill_sets:
            score = len(candidate_skills.intersection(job_skills))
            if score > best_score:
                best_job = job
                best_score = score
        candidate.has_skill_match = best_job is not None
        candidate.matched_job_title = best_job.title if best_job else ""
        candidate.skill_badges = build_skill_badges_for_applicant(candidate.user)
    candidates.sort(key=lambda c: (not c.has_skill_match, c.user.username.lower()))

    return render(
        request,
        "accounts/candidate_search.html",
        {"template_data": {"title": "Candidate Search", "candidates": candidates, "filters": {"skills": skills, "location": location, "projects": projects}}},
    )


@login_required
def company_profile_edit(request):
    if not _is_employer(request.user):
        return HttpResponseForbidden("Only employers can edit company profiles.")

    profile, _ = Profile.objects.get_or_create(user=request.user)
    if request.method == "POST":
        form = CompanyProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Company profile updated successfully!")
            return redirect("accounts.company_profile_edit")
    else:
        form = CompanyProfileForm(instance=profile)

    return render(
        request,
        "accounts/company_profile_edit.html",
        {"template_data": {"title": "Edit Company Profile", "form": form}},
    )


@login_required
def company_profile(request, username):
    User = get_user_model()
    company_user = get_object_or_404(User, username=username)
    profile, _ = Profile.objects.get_or_create(user=company_user)

    is_owner = request.user == company_user
    if profile.account_type != Profile.AccountType.EMPLOYER:
        raise Http404("Company profile not available.")
    if not is_owner and not _is_applicant(request.user):
        return HttpResponseForbidden("Only applicants can view company profiles.")

    office_jobs = (
        JobPost.objects.filter(owner=company_user, office_location__isnull=False)
        .select_related("office_location")
        .order_by("-created_at")
    )
    perks = [perk.strip() for perk in (profile.company_perks or "").splitlines() if perk.strip()]
    response_sla = _build_response_sla_by_employer_ids([company_user.id]).get(company_user.id)

    return render(
        request,
        "accounts/company_profile.html",
        {
            "template_data": {
                "title": f"{profile.company_name or company_user.username} Company Profile",
                "company_user": company_user,
                "profile": profile,
                "is_owner": is_owner,
                "perks": perks,
                "office_jobs": office_jobs,
                "response_sla": response_sla,
            }
        },
    )


@login_required
def company_search(request):
    if not _is_applicant(request.user):
        return HttpResponseForbidden("Only applicants can access company search.")

    qs = Profile.objects.filter(account_type=Profile.AccountType.EMPLOYER).select_related("user").order_by("company_name", "user__username")

    company = request.GET.get("company", "").strip()
    culture = request.GET.get("culture", "").strip()
    location = request.GET.get("location", "").strip()

    if company:
        qs = qs.filter(
            Q(company_name__icontains=company)
            | Q(user__username__icontains=company)
            | Q(company_description__icontains=company)
        )
    if culture:
        qs = qs.filter(
            Q(company_culture__icontains=culture)
            | Q(company_perks__icontains=culture)
            | Q(company_description__icontains=culture)
        )
    if location:
        qs = qs.filter(
            Q(location__icontains=location)
            | Q(city__icontains=location)
            | Q(state__icontains=location)
            | Q(user__job_posts__location__icontains=location)
            | Q(user__job_posts__office_location__city__icontains=location)
            | Q(user__job_posts__office_location__state__icontains=location)
        )

    companies = list(qs.distinct())
    company_user_ids = [company_profile.user_id for company_profile in companies]
    response_sla_by_owner = _build_response_sla_by_employer_ids(company_user_ids)
    for company_profile in companies:
        company_profile.open_roles_count = JobPost.objects.filter(owner=company_profile.user).count()
        company_profile.response_sla = response_sla_by_owner.get(company_profile.user_id)

    return render(
        request,
        "accounts/company_search.html",
        {
            "template_data": {
                "title": "Company Search",
                "companies": companies,
                "filters": {
                    "company": company,
                    "culture": culture,
                    "location": location,
                },
            }
        },
    )


@login_required
def save_candidate_search(request):
    if request.method == "POST":
        SavedCandidateSearch.objects.create(
            employer=request.user,
            search_name=request.POST.get("search_name"),
            filters={
                "skills": request.POST.get("skills", ""),
                "location": request.POST.get("location", ""),
                "projects": request.POST.get("projects", ""),
            },
        )
        messages.success(request, "Alert created successfully!")
    return redirect("jobposts.dashboard")


@login_required
def delete_candidate_search(request, search_id):
    search = get_object_or_404(SavedCandidateSearch, id=search_id, employer=request.user)
    if request.method == "POST":
        name = search.search_name
        search.delete()
        messages.warning(request, f'Alert "{name}" deleted.')
    return redirect("jobposts.dashboard")


@login_required
def applicant_clusters_map(request):
    if not (request.user.is_superuser or _is_employer(request.user)):
        return HttpResponseForbidden("Only employers can access applicant clusters map.")

    applicants = Profile.objects.filter(account_type=Profile.AccountType.APPLICANT).select_related("user")
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
        clusters.append({
            "location": location_name,
            "count": applicant_count,
            "latitude": float(latitude),
            "longitude": float(longitude),
        })

    template_data = {
        "title": "Applicant Clusters Map",
        "total_applicants": applicants.count(),
        "cluster_count": len(clusters),
    }
    return render(
        request,
        "accounts/applicant_clusters_map.html",
        {
            "template_data": template_data,
            "clusters": clusters,
            "google_maps_api_key": getattr(settings, "GOOGLE_MAPS_API_KEY", ""),
        },
    )



@login_required
def email_candidate(request, candidate_id):
    if not _is_employer(request.user):
        return HttpResponseForbidden("Only employers can email candidates.")
    
    candidate = get_object_or_404(Profile, id=candidate_id)
    employer = request.user

    # Candidate must have email visible
    if candidate.hide_email_from_employers:
        return HttpResponseForbidden("This candidate has chosen not to receive emails from employers.")
    
    # Candidate must have an email address
    if not candidate.user.email: 
        return HttpResponseForbidden("This candidate does not have an email address on file.") 

    if request.method == "POST":
        subject = request.POST.get("subject")
        message = request.POST.get("message")

        if not subject or not message:
            messages.error(request, "Subject and message are required.")
            return redirect("accounts.email_candidate", candidate_id=candidate_id)
        
        employer_name = request.user.username
        company_name = request.user.profile.company_name

        email_subject = company_name + ": " + subject
        email_message = "Hello! " + employer_name + " from " + company_name + " sent you this message.\nPlease reply to " + employer.email + ".\n\n\n" + message

        try:
            email = EmailMessage(
                subject=email_subject,
                body=email_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[candidate.user.email],
                reply_to=[request.user.email],
            )

            email.send(fail_silently=False)

            messages.success(request, "Your email has been sent.")
            return redirect("accounts.candidate_search")
        except Exception as exc:
            if settings.DEBUG:
                messages.warning(request, f"Your email could not be sent: {exc}")
            else:
                messages.warning(request, "Your email could not be sent.")


    return render(request, "accounts/email_candidate.html", {
        "candidate": candidate
    })

