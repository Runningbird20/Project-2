from django.db import models
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import Profile
from map.forms import OfficeLocationForm
from map.models import OfficeLocation
from map.services import OfficeLocationGeocodingError, geocode_office_address
from .forms import JobPostForm
from .models import JobPost
from django.views.decorators.http import require_POST
from apply.models import Application

from django.db.models import Count, Q

@login_required
def dashboard(request):
    profile = request.user.profile
    context = {}
    
    # --- APPLICANT LOGIC ---
    if profile.account_type == Profile.AccountType.APPLICANT:
        recommendations = get_job_recommendations(profile)
        
        apps = request.user.application_set.all() 
        apps_sent_count = apps.count()
        success_count = apps.filter(status__in=['offer', 'closed']).count()
        
        context.update({
            'recommendations': recommendations,
            'skills': profile.skills,
            'apps_sent_count': apps_sent_count,
            'success_count': success_count,
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
        
        saved_searches = request.user.saved_searches.all()
    
        context.update({
            'jobs': my_jobs,
            'overall_total': overall_total,
            'saved_searches': saved_searches,
        })

    return render(request, 'jobposts/dashboard.html', context)

def get_job_recommendations(user_profile):
    """
    Ranks jobs based on location match AND overlap between user skills and job requirements.
    """
    user_skills = []
    if user_profile.skills:
        user_skills = [s.strip().lower() for s in user_profile.skills.split(',') if s.strip()]
    
    user_location = user_profile.location.strip().lower() if user_profile.location else ""

    if not user_skills and not user_location:
        return JobPost.objects.none()

    query = Q()
    
    for skill in user_skills:
        query |= Q(title__icontains=skill) | Q(description__icontains=skill) | Q(skills__icontains=skill)

    if user_location:
        query |= Q(location__icontains=user_location)

    applied_job_ids = user_profile.user.application_set.values_list('job_id', flat=True)    
    suggested_jobs = JobPost.objects.filter(query).exclude(id__in=applied_job_ids).distinct()

    recommended_list = []
    for job in suggested_jobs:
        score = 0
        job_title = job.title.lower()
        job_desc = job.description.lower()
        job_loc = job.location.lower()
        job_skills = job.skills.lower() if job.skills else ""

        for skill in user_skills:
            if skill in job_title: score += 3  
            if skill in job_skills: score += 2 
            if skill in job_desc: score += 1   

        if user_location and user_location in job_loc:
            score += 5 

        recommended_list.append({
            'job': job,
            'score': score
        })

    recommended_list.sort(key=lambda x: x['score'], reverse=True)
    
    return [item['job'] for item in recommended_list[:5]]


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
                return redirect('jobposts.search')
            except OfficeLocationGeocodingError as exc:
                map_form.add_error(None, str(exc))
    else:
        form = JobPostForm()
        map_form = OfficeLocationForm(prefix='map')

    template_data['form'] = form
    template_data['map_form'] = map_form
    template_data['submit_label'] = 'Create Job Post'
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
    return render(request, 'jobposts/create.html', {'template_data': template_data})


def search(request):
    if request.user.is_authenticated:
        prof = Profile.objects.filter(user=request.user).first()
        if prof and prof.account_type == Profile.AccountType.EMPLOYER:
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
    visa_sponsorship = request.GET.get('visa_sponsorship', '').strip()

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
    if visa_sponsorship == 'true':
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

    template_data['posts'] = posts
    template_data['can_post_job'] = can_post_job
    template_data['filters'] = {
        'title': title,
        'skills': skills,
        'location': location,
        'salary_min': salary_min,
        'salary_max': salary_max,
        'work_setting': work_setting,
        'visa_sponsorship': visa_sponsorship == 'true',
    }
    return render(request, 'jobposts/search.html', {'template_data': template_data})

@login_required
<<<<<<< HEAD
def employer_dashboard(request):
    my_jobs = JobPost.objects.filter(owner=request.user).annotate(
        total_apps=models.Count('applications'),
        new_apps=models.Count('applications', filter=models.Q(applications__status='applied')),
    ).order_by('-created_at')

    overall_total = sum(job.total_apps for job in my_jobs)

    return render(request, 'jobposts/dashboard.html', {
        'jobs': my_jobs,
        'overall_total': overall_total,
    })


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
=======
@require_POST
def delete_job(request, job_id):
    job = get_object_or_404(JobPost, id=job_id, owner=request.user)
    job.delete()
    messages.success(request, "Job listing deleted successfully.")
    return redirect('jobposts.dashboard')

def job_detail(request, post_id):
    job = get_object_or_404(JobPost, pk=post_id)
    has_applied = False
    
    if request.user.is_authenticated:
        has_applied = Application.objects.filter(user=request.user, job=job).exists()
    
    return render(request, 'jobposts/job_detail.html', {
        'job': job,
        'has_applied': has_applied
    })
>>>>>>> e2d3c8e3be22649f88d65caa4a6ede12be78e1c2
