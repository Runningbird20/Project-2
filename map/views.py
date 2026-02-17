from django.shortcuts import get_object_or_404, render

from jobposts.models import JobPost


def job_location(request, post_id):
    post = get_object_or_404(
        JobPost.objects.select_related('office_location'),
        pk=post_id,
    )
    template_data = {
        'title': f'{post.title} Location',
        'post': post,
    }
    return render(request, 'map/job_location.html', {'template_data': template_data})
