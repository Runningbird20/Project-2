from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.conf import settings

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


def jobs_map(request):
    posts = (
        JobPost.objects.select_related('office_location')
        .filter(office_location__isnull=False)
        .order_by('-created_at')
    )

    jobs_data = []
    for post in posts:
        office = post.office_location
        jobs_data.append(
            {
                'id': post.id,
                'title': post.title,
                'company': post.company,
                'location': post.location,
                'work_setting': post.get_work_setting_display(),
                'visa_sponsorship': post.visa_sponsorship,
                'latitude': float(office.latitude),
                'longitude': float(office.longitude),
                'full_address': office.full_address,
                'detail_url': reverse('jobposts.detail', args=[post.id]),
            }
        )

    template_data = {
        'title': 'Jobs Map',
        'jobs_count': len(jobs_data),
    }
    return render(
        request,
        'map/jobs_map.html',
        {
            'template_data': template_data,
            'jobs_data': jobs_data,
            'google_maps_api_key': getattr(settings, 'GOOGLE_MAPS_API_KEY', ''),
        },
    )
