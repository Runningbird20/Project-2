from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.db import models
from accounts.models import Profile
from .forms import JobPostForm
from .models import JobPost


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
        
        context.update({
            'jobs': my_jobs,
            'overall_total': overall_total
        })

    return render(request, 'jobposts/dashboard.html', context)

def get_job_recommendations(user_profile):
    """
    Ranks jobs based on the overlap between user skills and job requirements.
    """
    if not user_profile.skills:
        return JobPost.objects.none()

    user_skills = [s.strip().lower() for s in user_profile.skills.split(',') if s.strip()]
    
    query = Q()
    for skill in user_skills:
        query |= Q(title__icontains=skill) | Q(description__icontains=skill)

    applied_job_ids = user_profile.user.application_set.values_list('job_id', flat=True)    
    suggested_jobs = JobPost.objects.filter(query).exclude(id__in=applied_job_ids).distinct()

    recommended_list = []
    for job in suggested_jobs:
        match_count = sum(1 for skill in user_skills if skill in job.description.lower() or skill in job.title.lower())
        recommended_list.append({
            'job': job,
            'match_count': match_count
        })

    recommended_list.sort(key=lambda x: x['match_count'], reverse=True)
    
    return [item['job'] for item in recommended_list[:5]] # Return top 5
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
        if form.is_valid():
            post = form.save(commit=False)
            post.owner = request.user
            post.save()
            return redirect('jobposts.search')
    else:
        form = JobPostForm()

    template_data['form'] = form
    template_data['submit_label'] = 'Create Job Post'
    return render(request, 'jobposts/create.html', {'template_data': template_data})


@login_required
def edit(request, post_id):
    if not _is_employer(request.user):
        return HttpResponseForbidden('Only employer accounts can edit job posts.')

    post = get_object_or_404(JobPost, pk=post_id, owner=request.user)

    template_data = {'title': 'Edit Job Post'}

    if request.method == 'POST':
        form = JobPostForm(request.POST, instance=post)
        if form.is_valid():
            updated_post = form.save(commit=False)
            updated_post.owner = request.user
            updated_post.save()
            return redirect('jobposts.search')
    else:
        form = JobPostForm(instance=post)

    template_data['form'] = form
    template_data['submit_label'] = 'Save Changes'
    return render(request, 'jobposts/create.html', {'template_data': template_data})


def search(request):
    if request.user.is_authenticated:
        prof = Profile.objects.filter(user=request.user).first()
        if prof and prof.account_type == Profile.AccountType.EMPLOYER:
            return redirect("accounts.candidate_search")

    template_data = {'title': 'Job Search'}
    if request.user.is_authenticated:
        prof = Profile.objects.filter(user=request.user).first()
        if prof and prof.account_type == Profile.AccountType.EMPLOYER:
            template_data["title"] = "Candidate Search"
    posts = JobPost.objects.all().order_by('-created_at')
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

