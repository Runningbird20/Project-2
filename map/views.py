import math

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.conf import settings

from accounts.models import Profile
from jobposts.models import JobPost
from map.services import OfficeLocationGeocodingError, geocode_office_address


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


def _haversine_miles(lat1, lon1, lat2, lon2):
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
def jobs_map(request):
    profile = Profile.objects.filter(user=request.user).first()
    has_applicant_address = bool(
        profile
        and profile.account_type == Profile.AccountType.APPLICANT
        and profile.full_address
    )

    raw_radius = request.GET.get("radius_miles", "25").strip()
    try:
        radius_miles = float(raw_radius)
        if radius_miles <= 0:
            raise ValueError
    except ValueError:
        radius_miles = 25.0
    radius_miles_display = int(radius_miles) if float(radius_miles).is_integer() else round(radius_miles, 1)

    template_data = {
        "title": "Jobs Map",
        "jobs_count": 0,
        "radius_miles": radius_miles_display,
        "has_applicant_address": has_applicant_address,
        "address_prompt": "",
        "map_notice": "",
    }

    if not has_applicant_address:
        template_data["address_prompt"] = "Add your full address in Profile to view nearby jobs on the map."
        return render(
            request,
            "map/jobs_map.html",
            {
                "template_data": template_data,
                "jobs_data": [],
                "google_maps_api_key": getattr(settings, "GOOGLE_MAPS_API_KEY", ""),
            },
        )

    try:
        center_lat, center_lon = geocode_office_address(profile.full_address)
        center_lat = float(center_lat)
        center_lon = float(center_lon)
    except OfficeLocationGeocodingError:
        template_data["address_prompt"] = (
            "We could not map your profile address. Update it in Profile and try again."
        )
        return render(
            request,
            "map/jobs_map.html",
            {
                "template_data": template_data,
                "jobs_data": [],
                "google_maps_api_key": getattr(settings, "GOOGLE_MAPS_API_KEY", ""),
            },
        )

    posts = (
        JobPost.objects.select_related('office_location')
        .filter(office_location__isnull=False)
        .order_by('-created_at')
    )

    jobs_data = []
    for post in posts:
        office = post.office_location
        distance_miles = _haversine_miles(
            center_lat,
            center_lon,
            float(office.latitude),
            float(office.longitude),
        )
        if distance_miles > radius_miles:
            continue

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
                'distance_miles': round(distance_miles, 1),
                'detail_url': reverse('jobposts.detail', args=[post.id]),
            }
        )

    jobs_data.sort(key=lambda item: item["distance_miles"])
    template_data["jobs_count"] = len(jobs_data)
    template_data["map_notice"] = f"Showing pinned jobs within {radius_miles_display} miles of your profile address."
    return render(
        request,
        'map/jobs_map.html',
        {
            'template_data': template_data,
            'jobs_data': jobs_data,
            'map_center': {'lat': center_lat, 'lng': center_lon},
            'google_maps_api_key': getattr(settings, 'GOOGLE_MAPS_API_KEY', ''),
        },
    )
