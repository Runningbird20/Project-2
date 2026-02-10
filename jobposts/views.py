from django.shortcuts import redirect, render

from .forms import JobPostForm


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
