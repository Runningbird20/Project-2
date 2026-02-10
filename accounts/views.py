from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction
from django.contrib.auth import login as auth_login, authenticate, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.http import Http404

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

    # POST
    form = SignupWithProfileForm(request.POST, error_class=CustomErrorList)
    template_data["form"] = form

    if not form.is_valid():
        return render(request, "accounts/signup.html", {"template_data": template_data})

    # Either everything within this block succeeds or nothing is written into the database. 
    with transaction.atomic():
        user = form.save()

        profile, _ = Profile.objects.get_or_create(user=user)
        profile.headline = form.cleaned_data.get("headline", "")
        profile.skills = form.cleaned_data.get("skills", "")
        profile.education = form.cleaned_data.get("education", "")
        profile.work_experience = form.cleaned_data.get("work_experience", "")
        profile.save()

        # Save up to 2 links from the signup template
        for i in range(2):
            label = request.POST.get(f"link_label_{i}", "").strip()
            url = request.POST.get(f"link_url_{i}", "").strip()
            if url:
                profile.links.create(label=label, url=url)

    return redirect("accounts.login")

@login_required
def profile(request):
    template_data = {"title": "My Profile"}
    # Ensure profile exists
    prof, _ = Profile.objects.get_or_create(user=request.user)
    template_data["profile"] = prof
    return render(request, "accounts/profile.html", {"template_data": template_data})

@login_required
def edit_profile(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)

    template_data = {"title": "Edit Profile"}

    if request.method == "GET":
        template_data["form"] = ProfileEditForm(instance=profile)
        return render(request, "accounts/edit_profile.html", {"template_data": template_data})

    # POST
    form = ProfileEditForm(request.POST, instance=profile)
    if not form.is_valid():
        template_data["form"] = form
        return render(request, "accounts/edit_profile.html", {"template_data": template_data})

    form.save()
    return redirect("accounts.profile")

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
