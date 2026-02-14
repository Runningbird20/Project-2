from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.db import models
from accounts.models import Profile
from map.forms import OfficeLocationForm
from map.models import OfficeLocation
from map.services import OfficeLocationGeocodingError, geocode_office_address
from .forms import JobPostForm
from .models import JobPost


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

<<<<<<< HEAD

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
@login_required
def employer_dashboard(request):
    my_jobs = JobPost.objects.filter(owner=request.user).annotate(
        total_apps=models.Count('applications'),
        new_apps=models.Count(
            'applications', 
            filter=models.Q(applications__status='applied')
        )
    ).order_by('-created_at')

    overall_total = sum(job.total_apps for job in my_jobs)

    return render(request, 'jobposts/dashboard.html', {
        'jobs': my_jobs,
        'overall_total': overall_total
    })
>>>>>>> e7dc03fe6bff4b71bede7a2df0e2984315fb23bb
