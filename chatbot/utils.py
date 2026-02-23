import json
from django.utils import timezone
from django.db.models import Q
from messaging.models import Message
from jobposts.models import JobPost, ApplicantJobMatch
from apply.models import Application
from interviews.models import InterviewSlot
from pulses.models import Pulse
from map.models import OfficeLocation

def get_comprehensive_site_context(user):
    """
    The ultimate context builder for PandaPulse. 
    Syncs Maps, Pulses, Messages, Jobs, and Applications.
    """
    if not user.is_authenticated:
        return json.dumps({"error": "User not authenticated"})

    profile = user.profile
    is_employer = (profile.account_type == "EMPLOYER")
    
    # 1. Social & Messaging Context
    unread_msgs = Message.objects.filter(recipient=user, is_read=False).select_related('sender')[:5]
    latest_pulses = Pulse.objects.all().select_related('user')[:3]

    # 2. Upcoming Interviews (Booked status only)
    interviews = InterviewSlot.objects.filter(
        Q(employer=user) | Q(applicant=user),
        start_at__gte=timezone.now(),
        status="booked"
    ).select_related('application__job')[:3]

    # 3. Role-Specific Activity
    if is_employer:
        # Employer: Job Listings + Map presence
        my_jobs = JobPost.objects.filter(owner=user).select_related('office_location').order_by('-created_at')[:5]
        job_data = [{
            "title": j.title, 
            "apps": j.applications.count(),
            "has_office_map": hasattr(j, 'office_location'),
            "city": j.office_location.city if hasattr(j, 'office_location') else j.location
        } for j in my_jobs]

        activity = {"listings": job_data}
        is_complete = bool(profile.company_name and profile.company_description)
    else:
        # Applicant: Matching Score + Matched Skills + Application History
        matches = ApplicantJobMatch.objects.filter(applicant=user).select_related('job', 'job__office_location').order_by('-score')[:5]
        match_data = [{
            "job": m.job.title, 
            "company": m.job.company, 
            "match_score": m.score,
            "skills_match": m.matched_skills,
            "work_setting": m.job.work_setting,
            "location": m.job.office_location.full_address if hasattr(m.job, 'office_location') else m.job.location
        } for m in matches]

        apps = Application.objects.filter(user=user).select_related('job').order_by('-applied_at')[:3]
        activity = {
            "top_matches": match_data,
            "recent_apps": [{"job": a.job.title, "status": a.status} for a in apps]
        }
        is_complete = bool(profile.headline and profile.skills)

    # 4. Consolidate into JSON
    context_data = {
        "user_meta": {
            "name": user.get_full_name() or user.username,
            "role": profile.account_type,
            "profile_ready": is_complete,
            "location": profile.location_city_state
        },
        "social": {
            "unread_messages": [{"from": m.sender.username, "snippet": m.body[:40]} for m in unread_msgs],
            "recent_pulse_creators": [p.user.username for p in latest_pulses]
        },
        "interviews": [{"job": i.application.job.title, "at": i.start_at.strftime('%m/%d %H:%M')} for i in interviews],
        "dashboard": activity,
        "system": {"now": timezone.now().isoformat()}
    }

    return json.dumps(context_data, indent=2)