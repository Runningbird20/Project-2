import math

from django.conf import settings
from django.core.mail import send_mail
from django.db import models
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import Profile
from map.forms import OfficeLocationForm
from map.models import OfficeLocation
from map.services import OfficeLocationGeocodingError, geocode_office_address
from .forms import JobPostForm
from .models import ApplicantJobMatch, JobPost
from .matching import sync_applicant_job_matches
from django.views.decorators.http import require_POST
from apply.models import Application
from apply.services import auto_archive_old_rejections, enforce_employer_response_deadline
from project2.skills import COMMON_SKILLS
from django.contrib.admin.views.decorators import staff_member_required

from django.db.models import Count
from interviews.services import build_skill_badges_for_applicant, get_employer_interview_context

MIN_MATCH_PERCENT = 50


def _skill_set(raw_value):
    if not raw_value:
        return set()
    return {token.strip().lower() for token in raw_value.split(",") if token.strip()}


def _skill_list(raw_value):
    if not raw_value:
        return []
    seen = set()
    ordered = []
    for token in str(raw_value).replace(";", ",").split(","):
        skill = token.strip()
        if not skill:
            continue
        key = skill.lower()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(skill)
    return ordered


def _ordered_overlap_skills(job_skills_raw, candidate_skills_raw):
    job_skills = _skill_list(job_skills_raw)
    candidate_skill_set = _skill_set(candidate_skills_raw)
    return [skill for skill in job_skills if skill.lower() in candidate_skill_set]


def _skill_overlap_percent(applicant_skills, job_skills):
    if not applicant_skills or not job_skills:
        return 0
    overlap_count = len(applicant_skills.intersection(job_skills))
    return round((overlap_count / len(job_skills)) * 100)


def _haversine_miles(lat1, lon1, lat2, lon2):
    """Calculate great-circle distance in miles between two lat/lon points."""
    earth_radius_miles = 3958.8
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return earth_radius_miles * c


@login_required
def dashboard(request):
    enforce_employer_response_deadline()
    auto_archive_old_rejections()
    profile = request.user.profile
    context = {}
    
    # --- APPLICANT LOGIC ---
    if profile.account_type == Profile.AccountType.APPLICANT:
        recommendations = get_job_recommendations(profile)
        match_map = {
            match.job_id: match.matched_skills
            for match in ApplicantJobMatch.objects.filter(
                applicant=request.user,
                job_id__in=[job.id for job in recommendations],
            )
        }
        for job in recommendations:
            raw = match_map.get(job.id, "")
            job.why_matched_skills = [token.strip() for token in raw.split(",") if token.strip()]
        
        apps = request.user.application_set.all() 
        apps_sent_count = apps.count()
        success_count = apps.filter(status__in=['offer', 'closed']).count()
        
        context.update({
            'recommendations': recommendations,
            'skills': profile.skills,
            'apps_sent_count': apps_sent_count,
            'success_count': success_count,
            'recent_applications': apps.select_related('job').order_by('-applied_at')[:5],
            'archived_rejected_applications': apps.filter(
                status='rejected',
                archived_by_applicant=True,
            ).select_related('job').order_by('-rejected_at', '-applied_at')[:5],
        })

    # --- EMPLOYER LOGIC ---
    elif profile.account_type == Profile.AccountType.EMPLOYER:
        my_jobs = JobPost.objects.filter(owner=request.user).annotate(
            total_apps=Count('applications'), 
            new_apps=Count(
                'applications', 
                filter=Q(applications__status='applied')
            )
        ).order_by('-created_at')

        overall_total = sum(job.total_apps for job in my_jobs)
        employer_jobs = list(my_jobs)

        def _skill_set(raw_value):
            if not raw_value:
                return set()
            return {token.strip().lower() for token in raw_value.split(",") if token.strip()}

        applied_pairs = set(
            Application.objects.filter(job__owner=request.user).values_list("user_id", "job_id")
        )
        job_skill_sets = [(job, _skill_set(job.skills)) for job in employer_jobs]
        candidate_matches = []
        applicant_profiles = Profile.objects.filter(
            account_type=Profile.AccountType.APPLICANT,
            visible_to_recruiters=True,
        ).select_related("user").order_by("user__username")

        for candidate in applicant_profiles:
            candidate_skills = _skill_set(candidate.skills)
            candidate_skill_list = _skill_list(candidate.skills)
            candidate_skill_map = {skill.lower(): skill for skill in candidate_skill_list}
            if not candidate_skills:
                continue

            best_job = None
            best_score = 0
            best_matched_skills = []
            for job, job_skills in job_skill_sets:
                if (candidate.user_id, job.id) in applied_pairs:
                    continue
                score = _skill_overlap_percent(candidate_skills, job_skills)
                if score <= MIN_MATCH_PERCENT:
                    continue
                if score > best_score:
                    job_skill_list = _skill_list(job.skills)
                    matched_skills = [
                        candidate_skill_map.get(skill.lower(), skill)
                        for skill in job_skill_list
                        if skill.lower() in candidate_skills
                    ]
                    best_score = score
                    best_job = job
                    best_matched_skills = matched_skills

            if best_job:
                overlap_skills = _ordered_overlap_skills(best_job.skills, candidate.skills)
                candidate_skill_badges = {
                    item["name"].lower(): item for item in build_skill_badges_for_applicant(candidate.user)
                }
                candidate_matches.append({
                    "candidate": candidate,
                    "job": best_job,
                    "score": best_score,
                    "overlap_skills": overlap_skills,
                    "overlap_skill_badges": [
                        {
                            "name": skill,
                            "endorsed": candidate_skill_badges.get(skill.lower(), {}).get("endorsed", False),
                            "endorsed_by": candidate_skill_badges.get(skill.lower(), {}).get("endorsed_by", ""),
                        }
                        for skill in overlap_skills
                    ],
                })
    
        saved_searches = request.user.saved_searches.all()
    
        context.update({
            'jobs': my_jobs,
            'overall_total': overall_total,
            'saved_searches': saved_searches,
            'matched_candidates': candidate_matches,
            'archived_rejected_applicants': Application.objects.filter(
                job__owner=request.user,
                status='rejected',
                archived_by_employer=True,
            ).select_related('job', 'user').order_by('-rejected_at', '-applied_at')[:5],
        })
        context.update(
            get_employer_interview_context(
                request.user,
                month_key=request.GET.get("interview_month"),
                initial_application_id=request.GET.get("interview_application"),
            )
        )

    return render(request, 'jobposts/dashboard.html', context)

def get_job_recommendations(user_profile):
    return sync_applicant_job_matches(user_profile.user)


def _is_employer(user):
    return Profile.objects.filter(
        user=user,
        account_type=Profile.AccountType.EMPLOYER,
    ).exists()


@login_required
def create(request):
    if not _is_employer(request.user):
        return HttpResponseForbidden('Only employer accounts can create job posts.')

    template_data = {'title': 'Create Job Post'}

    if request.method == 'POST':
        form = JobPostForm(request.POST)
        map_form = OfficeLocationForm(request.POST, prefix='map')
        if form.is_valid() and map_form.is_valid():
            post = form.save(commit=False)
            post.owner = request.user
            post.save()
            try:
                _save_office_location(post, map_form)
                if request.user.email:
                    try:
                        send_mail(
                            subject=f"Job posted: {post.title}",
                            message=(
                                f"Hi {request.user.username},\n\n"
                                f"Great news. Your job posting, {post.title} at {post.company}, "
                                "is now live on PandaPulse and visible to candidates.\n\n"
                                "You can log in at any time to manage the listing, review "
                                "applications, and make updates as needed. We recommend checking "
                                "your dashboard regularly to stay on top of new applicants.\n\n"
                                "Thank you for choosing PandaPulse to connect with top talent.\n\n"
                                "Best regards,\n"
                                "The PandaPulse Team\n"
                            ),
                            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@pandapulse.local"),
                            recipient_list=[request.user.email],
                            fail_silently=False,
                        )
                    except Exception as exc:
                        if settings.DEBUG:
                            messages.warning(request, f"Job posting confirmation email could not be sent: {exc}")
                        else:
                            messages.warning(request, "Job posting confirmation email could not be sent.")
                return redirect('jobposts.search')
            except OfficeLocationGeocodingError as exc:
                map_form.add_error(None, str(exc))
    else:
        form = JobPostForm()
        map_form = OfficeLocationForm(prefix='map')

    template_data['form'] = form
    template_data['map_form'] = map_form
    template_data['submit_label'] = 'Create Job Post'
    template_data['skill_options'] = COMMON_SKILLS
    return render(request, 'jobposts/create.html', {'template_data': template_data})


@login_required
def edit(request, post_id):
    if not _is_employer(request.user):
        return HttpResponseForbidden('Only employer accounts can edit job posts.')

    post = get_object_or_404(JobPost, pk=post_id, owner=request.user)

    template_data = {'title': 'Edit Job Post'}
    office_location = getattr(post, 'office_location', None)

    if request.method == 'POST':
        form = JobPostForm(request.POST, instance=post)
        map_form = OfficeLocationForm(request.POST, instance=office_location, prefix='map')
        if form.is_valid() and map_form.is_valid():
            updated_post = form.save(commit=False)
            updated_post.owner = request.user
            updated_post.save()
            try:
                _save_office_location(updated_post, map_form)
                return redirect('jobposts.search')
            except OfficeLocationGeocodingError as exc:
                map_form.add_error(None, str(exc))
    else:
        form = JobPostForm(instance=post)
        map_form = OfficeLocationForm(instance=office_location, prefix='map')

    template_data['form'] = form
    template_data['map_form'] = map_form
    template_data['submit_label'] = 'Save Changes'
    template_data['skill_options'] = COMMON_SKILLS
    return render(request, 'jobposts/create.html', {'template_data': template_data})


def search(request):
    if request.user.is_authenticated:
        prof = Profile.objects.filter(user=request.user).first()
        if prof and (prof.account_type == Profile.AccountType.EMPLOYER and not prof.user.is_staff):
            return redirect("accounts.candidate_search")

    template_data = {'title': 'Job Search'}
    posts = JobPost.objects.select_related('office_location').all().order_by('-created_at')
    can_post_job = False
    if request.user.is_authenticated:
        can_post_job = _is_employer(request.user)

    title = request.GET.get('title', '').strip()
    skills = request.GET.get('skills', '').strip()
    location = request.GET.get('location', '').strip()
    salary_min = request.GET.get('salary_min', '').strip()
    salary_max = request.GET.get('salary_max', '').strip()
    work_setting = request.GET.get('work_setting', '').strip()
    company_size = request.GET.get('company_size', '').strip()
    visa_sponsorship = request.GET.get('visa_sponsorship', '').strip()
    use_home_radius = False
    radius_miles = ''
    radius_warning = ''
    radius_active = False
    is_applicant = False
    applicant_profile = None
    has_home_address = False
    home_address = ''

    if title:
        posts = posts.filter(title__icontains=title)
    if skills:
        skill_terms = [term.strip() for term in skills.split(',') if term.strip()]
        for term in skill_terms:
            posts = posts.filter(skills__icontains=term)
    if location:
        posts = posts.filter(location__icontains=location)
    if work_setting:
        posts = posts.filter(work_setting=work_setting)
    if company_size:
        posts = posts.filter(company_size=company_size)
    if visa_sponsorship.lower() in {'true', '1', 'on', 'yes'}:
        posts = posts.filter(visa_sponsorship=True)
    if salary_min:
        try:
            min_value = int(salary_min)
            posts = posts.filter(Q(salary_max__gte=min_value) | Q(salary_min__gte=min_value))
        except ValueError:
            pass
    if salary_max:
        try:
            max_value = int(salary_max)
            posts = posts.filter(Q(salary_min__lte=max_value) | Q(salary_max__lte=max_value))
        except ValueError:
            pass

    if request.user.is_authenticated:
        profile = Profile.objects.filter(user=request.user).first()
        if profile and profile.account_type == Profile.AccountType.APPLICANT:
            applicant_profile = profile
            is_applicant = True
            home_address = profile.full_address
            has_home_address = bool(home_address)

            session_use_home_radius = request.session.get('job_search_use_home_radius', False)
            session_radius_miles = request.session.get('job_search_radius_miles', '25')

            raw_use_home_radius = request.GET.get('use_home_radius')
            if raw_use_home_radius is None:
                use_home_radius = bool(session_use_home_radius)
            else:
                use_home_radius = str(raw_use_home_radius).strip().lower() in {'true', '1', 'on', 'yes'}
            raw_radius = request.GET.get('radius_miles', str(session_radius_miles)).strip()
            try:
                radius_value = float(raw_radius)
                if radius_value <= 0:
                    raise ValueError
                radius_miles = str(int(radius_value)) if radius_value.is_integer() else f'{radius_value:.1f}'
            except (ValueError, TypeError):
                radius_miles = '25'

            request.session['job_search_use_home_radius'] = use_home_radius
            request.session['job_search_radius_miles'] = radius_miles

            if use_home_radius:
                if not has_home_address:
                    radius_warning = 'Add your home address in your profile to use radius filtering.'
                else:
                    try:
                        home_lat, home_lon = geocode_office_address(home_address)
                        home_lat = float(home_lat)
                        home_lon = float(home_lon)
                        filtered_posts = []
                        for post in posts:
                            if post.work_setting == 'remote':
                                filtered_posts.append(post)
                                continue

                            office_location = getattr(post, 'office_location', None)
                            if not office_location:
                                continue

                            distance_miles = _haversine_miles(
                                home_lat,
                                home_lon,
                                float(office_location.latitude),
                                float(office_location.longitude),
                            )
                            if distance_miles <= float(radius_miles):
                                post.distance_from_home_miles = round(distance_miles, 1)
                                filtered_posts.append(post)
                        posts = filtered_posts
                        radius_active = True
                    except OfficeLocationGeocodingError:
                        radius_warning = 'Could not map your home address right now. Showing all search results.'

    posts_sequence = list(posts)
    matched_posts = []
    other_posts = posts_sequence
    if is_applicant and request.user.is_authenticated and applicant_profile:
        sync_applicant_job_matches(request.user)

        applicant_skills = _skill_set(applicant_profile.skills)
        matched_posts = []
        other_posts = []
        for post in posts_sequence:
            post_skills = _skill_set(post.skills)
            post.skill_overlap_percent = _skill_overlap_percent(applicant_skills, post_skills)
            if post.skill_overlap_percent > MIN_MATCH_PERCENT:
                matched_posts.append(post)
            else:
                other_posts.append(post)

    template_data['posts'] = posts_sequence
    template_data['matched_posts'] = matched_posts
    template_data['other_posts'] = other_posts
    template_data['posts_count'] = len(posts_sequence)
    template_data['can_post_job'] = can_post_job
    template_data['filters'] = {
        'title': title,
        'skills': skills,
        'location': location,
        'salary_min': salary_min,
        'salary_max': salary_max,
        'work_setting': work_setting,
        'company_size': company_size,
        'visa_sponsorship': visa_sponsorship.lower() in {'true', '1', 'on', 'yes'},
        'use_home_radius': use_home_radius,
        'radius_miles': radius_miles,
    }
    template_data['is_applicant'] = is_applicant
    template_data['has_home_address'] = has_home_address
    template_data['home_address'] = home_address
    template_data['radius_warning'] = radius_warning
    template_data['radius_active'] = radius_active
    return render(request, 'jobposts/search.html', {'template_data': template_data})

def _save_office_location(post, map_form):
    if not getattr(map_form, 'has_location_data', False):
        OfficeLocation.objects.filter(job_post=post).delete()
        return

    address_line_1 = map_form.cleaned_data.get('address_line_1', '')
    address_line_2 = map_form.cleaned_data.get('address_line_2', '')
    city = map_form.cleaned_data.get('city', '')
    state = map_form.cleaned_data.get('state', '')
    postal_code = map_form.cleaned_data.get('postal_code', '')
    country = map_form.cleaned_data.get('country', '')

    query_parts = [address_line_1, address_line_2, city, state, postal_code, country]
    address_query = ', '.join([part for part in query_parts if part])
    latitude, longitude = geocode_office_address(address_query)

    OfficeLocation.objects.update_or_create(
        job_post=post,
        defaults={
            'address_line_1': address_line_1,
            'address_line_2': address_line_2,
            'city': city,
            'state': state,
            'postal_code': postal_code,
            'country': country,
            'latitude': latitude,
            'longitude': longitude,
        },
    )

@require_POST
def delete_job(request, job_id):
    job = get_object_or_404(JobPost, id=job_id, owner=request.user)
    job.delete()
    messages.success(request, "Job listing deleted successfully.")
    return redirect('jobposts.dashboard')

def job_detail(request, post_id):
    job = get_object_or_404(JobPost.objects.select_related('office_location'), pk=post_id)
    has_applied = False
    skill_overlap_percent = None
    
    if request.user.is_authenticated:
        has_applied = Application.objects.filter(user=request.user, job=job).exists()
        profile = Profile.objects.filter(user=request.user).first()
        if profile and profile.account_type == Profile.AccountType.APPLICANT:
            applicant_skills = _skill_set(profile.skills)
            job_skills = _skill_set(job.skills)
            skill_overlap_percent = _skill_overlap_percent(applicant_skills, job_skills)
    
    return render(request, 'jobposts/job_detail.html', {
        'job': job,
        'has_applied': has_applied,
        'skill_overlap_percent': skill_overlap_percent,
        'job_skill_list': _skill_list(job.skills),
    })



@staff_member_required
def edit_post(request, post_id):
    post = get_object_or_404(JobPost, pk=post_id)
    template_data = {'title': 'Edit Job Post'}

    if request.method == 'POST':
        form = JobPostForm(request.POST, instance=post)
        if form.is_valid():
            updated_post = form.save(commit=False)
            updated_post.save()
            return redirect('jobposts.search')
    else:
        form = JobPostForm(instance=post)

    template_data['form'] = form
    template_data['submit_label'] = 'Save Changes'
    template_data['post_id'] = post_id
    template_data['skill_options'] = COMMON_SKILLS
    return render(request, 'jobposts/edit_post.html', {'template_data': template_data})

@staff_member_required
def remove_post(request, post_id):
    if request.method == "POST":
        post = JobPost.objects.get(id=post_id)
        post.delete()
        return redirect('jobposts.search')
    else:
        return redirect('jobposts.search')
