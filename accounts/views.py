from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction
from django.contrib.auth import login as auth_login, authenticate, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model
from django.http import Http404, HttpResponseForbidden

from .forms import SignupWithProfileForm, CustomErrorList, ProfileEditForm
from .models import Profile


@login_required
def logout(request):
    auth_logout(request)
    return redirect('home.index')


def login(request):
    template_data = {"title": "Login"}
    if request.method == 'GET':
        return render(request, 'accounts/login.html', {'template_data': template_data})

    user = authenticate(request, username=request.POST['username'], password=request.POST['password'])
    if user is None:
        template_data['error'] = 'The username or password is incorrect.'
        return render(request, 'accounts/login.html', {'template_data': template_data})

    auth_login(request, user)
    return redirect('home.index')


def signup(request):
    template_data = {"title": "Sign Up"}

    if request.method == "GET":
        template_data["form"] = SignupWithProfileForm()
        return render(request, "accounts/signup.html", {"template_data": template_data})

    form = SignupWithProfileForm(request.POST, error_class=CustomErrorList)
    template_data["form"] = form

    if not form.is_valid():
        return render(request, "accounts/signup.html", {"template_data": template_data})

    with transaction.atomic():
        user = form.save()
        profile, _ = Profile.objects.get_or_create(user=user)

        acct = form.cleaned_data.get("account_type", Profile.AccountType.APPLICANT)
        profile.account_type = acct

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
def profile(request):
    template_data = {"title": "My Profile"}
    prof, _ = Profile.objects.get_or_create(user=request.user)
    template_data["profile"] = prof
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

    form = ProfileEditForm(request.POST, instance=profile)
    template_data["form"] = form

    if not form.is_valid():
        return render(request, "accounts/edit_profile.html", {"template_data": template_data})

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

    return redirect("accounts.profile")


@staff_member_required
def manage_users(request):
    template_data = {
        "title": "Manage Users",
        "users": Profile.objects.all(),
    }
    return render(request, 'accounts/manage_users.html', {'template_data': template_data})


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

    form = ProfileEditForm(request.POST, instance=profile)
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
        user = Profile.objects.get(id=user_id)
        user.user.delete()
        return redirect('accounts.manage_users')
    return redirect('accounts.manage_users')


def public_profile(request, username):
    User = get_user_model()
    user = get_object_or_404(User, username=username)
    profile, _ = Profile.objects.get_or_create(user=user)
    if not profile.visible_to_recruiters:
        raise Http404("Profile not available.")

    template_data = {
        "title": f"{user.username} Profile",
        "profile": profile,
        "public_view": True,
    }
    return render(request, "accounts/public_profile.html", {"template_data": template_data})