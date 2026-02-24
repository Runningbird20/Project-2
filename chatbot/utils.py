import json

from django.db.models import Q
from django.utils import timezone

from apply.models import Application
from interviews.models import InterviewSlot
from jobposts.models import ApplicantJobMatch, JobPost
from map.models import OfficeLocation
from messaging.models import Message
from pulses.models import Pulse


def get_comprehensive_site_context(user):
    if not user.is_authenticated:
        return json.dumps({"error": "User not authenticated"})

    profile = user.profile
    is_employer = profile.account_type == "EMPLOYER"

    unread_msgs = Message.objects.filter(recipient=user, is_read=False).select_related("sender")[:5]
    latest_pulses = Pulse.objects.all().select_related("user")[:3]
    interviews = InterviewSlot.objects.filter(
        Q(employer=user) | Q(applicant=user),
        start_at__gte=timezone.now(),
        status="booked",
    ).select_related("application__job")[:3]

    if is_employer:
        my_jobs = JobPost.objects.filter(owner=user).select_related("office_location").order_by("-created_at")[:5]
        job_data = [
            {
                "title": j.title,
                "apps": j.applications.count(),
                "has_office_map": isinstance(getattr(j, "office_location", None), OfficeLocation),
                "city": j.office_location.city if isinstance(getattr(j, "office_location", None), OfficeLocation) else j.location,
            }
            for j in my_jobs
        ]
        activity = {"listings": job_data}
        is_complete = bool(profile.company_name and profile.company_description)
    else:
        matches = ApplicantJobMatch.objects.filter(applicant=user).select_related("job", "job__office_location").order_by("-score")[:5]
        match_data = [
            {
                "job": m.job.title,
                "company": m.job.company,
                "match_score": m.score,
                "skills_match": m.matched_skills,
                "work_setting": m.job.work_setting,
                "location": m.job.office_location.full_address if isinstance(getattr(m.job, "office_location", None), OfficeLocation) else m.job.location,
            }
            for m in matches
        ]
        apps = Application.objects.filter(user=user).select_related("job").order_by("-applied_at")[:3]
        activity = {
            "top_matches": match_data,
            "recent_apps": [{"job": a.job.title, "status": a.status} for a in apps],
        }
        is_complete = bool(profile.headline and profile.skills)

    context_data = {
        "user_meta": {
            "name": user.get_full_name() or user.username,
            "role": profile.account_type,
            "profile_ready": is_complete,
            "location": profile.location_city_state,
        },
        "social": {
            "unread_messages": [{"from": m.sender.username, "snippet": m.body[:40]} for m in unread_msgs],
            "recent_pulse_creators": [p.user.username for p in latest_pulses],
        },
        "interviews": [{"job": i.application.job.title, "at": i.start_at.strftime("%m/%d %H:%M")} for i in interviews],
        "dashboard": activity,
        "system": {"now": timezone.now().isoformat()},
    }

    return json.dumps(context_data, indent=2)
