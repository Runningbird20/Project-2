from django.db.models import Q
from django.shortcuts import redirect, render

from .forms import JobPostForm
from .models import JobPost


def create(request):
    template_data = {'title': 'Create Job Post'}

    if request.method == 'POST':
        form = JobPostForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('jobposts.create')
    else:
        form = JobPostForm()

    template_data['form'] = form
    return render(request, 'jobposts/create.html', {'template_data': template_data})


def search(request):
    template_data = {'title': 'Job Search'}
    posts = JobPost.objects.all().order_by('-created_at')

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
