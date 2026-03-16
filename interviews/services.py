import calendar
from collections import defaultdict
from datetime import datetime, timedelta, timezone as dt_timezone
from urllib.parse import quote

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from accounts.models import Profile
from project2.skills import split_skills_csv

from .forms import InterviewFeedbackForm, InterviewSlotProposalForm
from .models import InterviewSkillEndorsement, InterviewSlot


def _month_anchor(raw_value):
    if raw_value:
        try:
            parsed = datetime.strptime(raw_value, "%Y-%m")
            return parsed.year, parsed.month
        except ValueError:
            pass
    now = timezone.localtime()
    return now.year, now.month


def normalize_skill_token(raw_value):
    return " ".join(str(raw_value or "").split()).strip().lower()


def parse_skill_tokens(raw_value):
    return split_skills_csv(raw_value)


def build_skill_badges_for_applicant(applicant):
    try:
        profile = applicant.profile
    except Profile.DoesNotExist:
        profile = None

    skills = parse_skill_tokens(getattr(profile, "skills", ""))
    company_map = defaultdict(set)
    for endorsement in (
        InterviewSkillEndorsement.objects.filter(applicant=applicant)
        .select_related("interview_slot__application__job")
        .only("skill_key", "interview_slot__application__job__company")
    ):
        company = endorsement.interview_slot.application.job.company
        if company:
            company_map[endorsement.skill_key].add(company)

    badges = []
    for skill in skills:
        key = normalize_skill_token(skill)
        companies = sorted(company_map.get(key, set()))
        badges.append(
            {
                "name": skill,
                "endorsed": bool(companies),
                "endorsed_by": ", ".join(companies),
            }
        )
    return badges


def build_calendar_data(interviews, month_key=None):
    year, month = _month_anchor(month_key)
    cal = calendar.Calendar(firstweekday=6)
    date_to_interviews = {}
    for slot in interviews:
        local_start = timezone.localtime(slot.start_at)
        date_to_interviews.setdefault(local_start.date(), []).append(slot)

    weeks = []
    for week in cal.monthdatescalendar(year, month):
        week_days = []
        for day in week:
            day_items = date_to_interviews.get(day, [])
            week_days.append(
                {
                    "date": day,
                    "in_month": day.month == month,
                    "items": sorted(day_items, key=lambda i: i.start_at),
                }
            )
        weeks.append(week_days)

    current_month = datetime(year, month, 1)
    prev_month = (current_month - timedelta(days=1)).strftime("%Y-%m")
    next_month = (current_month + timedelta(days=32)).replace(day=1).strftime("%Y-%m")
    return {
        "weeks": weeks,
        "month_label": current_month.strftime("%B %Y"),
        "prev_month": prev_month,
        "next_month": next_month,
        "month_key": current_month.strftime("%Y-%m"),
    }


def _base_interview_queryset():
    return InterviewSlot.objects.select_related(
        "application",
        "application__job",
        "application__user",
        "employer",
        "applicant",
        "applicant__profile",
        "feedback",
    )


def get_applicant_interview_context(user, month_key=None):
    now = timezone.now()
    scheduled = list(
        _base_interview_queryset().filter(applicant=user, status=InterviewSlot.Status.BOOKED).order_by("start_at")
    )
    open_slots = _base_interview_queryset().filter(applicant=user, status=InterviewSlot.Status.OPEN).order_by("start_at")
    upcoming = []
    past = []
    for slot in scheduled:
        slot.feedback_visible_to_applicant = slot.end_at <= now and bool(getattr(slot, "feedback", None))
        if slot.end_at <= now:
            past.append(slot)
        else:
            upcoming.append(slot)
    return {
        "scheduled_interviews": upcoming,
        "upcoming_interviews": upcoming,
        "past_interviews": past,
        "open_interview_slots": open_slots,
        "interview_calendar": build_calendar_data(upcoming, month_key=month_key),
        "applicant_skill_badges": build_skill_badges_for_applicant(user),
    }


def get_employer_interview_context(user, month_key=None, post_data=None, initial_application_id=None):
    scheduled = list(
        _base_interview_queryset().filter(employer=user, status=InterviewSlot.Status.BOOKED).order_by("start_at")
    )
    open_slots = _base_interview_queryset().filter(employer=user, status=InterviewSlot.Status.OPEN).order_by("start_at")
    form = InterviewSlotProposalForm(post_data or None, employer=user)
    endorsement_keys_by_slot = defaultdict(set)
    if scheduled:
        for slot_id, skill_key in InterviewSkillEndorsement.objects.filter(
            interview_slot_id__in=[slot.id for slot in scheduled]
        ).values_list("interview_slot_id", "skill_key"):
            endorsement_keys_by_slot[slot_id].add(skill_key)
    now = timezone.now()
    upcoming = []
    past = []
    for slot in scheduled:
        slot.feedback_allowed = slot.end_at <= now
        slot.feedback_form = InterviewFeedbackForm(instance=getattr(slot, "feedback", None), prefix=f"feedback-{slot.id}")
        try:
            applicant_profile = slot.applicant.profile
        except Profile.DoesNotExist:
            applicant_profile = None
        applicant_skills = parse_skill_tokens(getattr(applicant_profile, "skills", ""))
        endorsed_keys = endorsement_keys_by_slot.get(slot.id, set())
        slot.skill_endorsement_options = [
            {
                "label": skill,
                "value": skill,
                "endorsed": normalize_skill_token(skill) in endorsed_keys,
            }
            for skill in applicant_skills
        ]
        if slot.end_at <= now:
            past.append(slot)
        else:
            upcoming.append(slot)
    if initial_application_id and not post_data:
        try:
            parsed_application_id = int(initial_application_id)
        except (TypeError, ValueError):
            parsed_application_id = None
        if parsed_application_id and form.fields["application"].queryset.filter(id=parsed_application_id).exists():
            form.fields["application"].initial = parsed_application_id
    return {
        "scheduled_interviews": upcoming,
        "upcoming_interviews": upcoming,
        "past_interviews": past,
        "open_interview_slots": open_slots,
        "interview_proposal_form": form,
        "interview_calendar": build_calendar_data(upcoming, month_key=month_key),
    }


def is_employer(user):
    return Profile.objects.filter(user=user, account_type=Profile.AccountType.EMPLOYER).exists()


def is_applicant(user):
    return Profile.objects.filter(user=user, account_type=Profile.AccountType.APPLICANT).exists()


def google_calendar_link(slot):
    start_utc = slot.start_at.astimezone(dt_timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    end_utc = slot.end_at.astimezone(dt_timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    title = quote(f"Interview: {slot.application.job.title} at {slot.application.job.company}")
    details_parts = [
        f"Applicant: {slot.applicant.get_full_name() or slot.applicant.username}",
        f"Employer: {slot.employer.get_full_name() or slot.employer.username}",
    ]
    if slot.notes:
        details_parts.append(f"Notes: {slot.notes}")
    if slot.meeting_link:
        details_parts.append(f"Meeting link: {slot.meeting_link}")
    details = quote("\n".join(details_parts))
    location = quote(slot.meeting_link or "PandaPulse Interview")
    return (
        "https://calendar.google.com/calendar/render?action=TEMPLATE"
        f"&text={title}&dates={start_utc}/{end_utc}&details={details}&location={location}"
    )


def build_ics_content(slot):
    dtstamp = timezone.now().astimezone(dt_timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dtstart = slot.start_at.astimezone(dt_timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dtend = slot.end_at.astimezone(dt_timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    summary = f"Interview: {slot.application.job.title} at {slot.application.job.company}"
    description = (
        f"Applicant: {slot.applicant.get_full_name() or slot.applicant.username}\\n"
        f"Employer: {slot.employer.get_full_name() or slot.employer.username}"
    )
    if slot.notes:
        description += f"\\nNotes: {slot.notes}"
    if slot.meeting_link:
        description += f"\\nMeeting link: {slot.meeting_link}"
    location = slot.meeting_link or "PandaPulse"
    return "\r\n".join(
        [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//PandaPulse//Interview Scheduler//EN",
            "BEGIN:VEVENT",
            f"UID:{slot.calendar_uid}",
            f"DTSTAMP:{dtstamp}",
            f"DTSTART:{dtstart}",
            f"DTEND:{dtend}",
            f"SUMMARY:{summary}",
            f"DESCRIPTION:{description}",
            f"LOCATION:{location}",
            "END:VEVENT",
            "END:VCALENDAR",
            "",
        ]
    )


def notify_booking(slot):
    gcal_url = google_calendar_link(slot)
    if slot.applicant.email:
        send_mail(
            subject = f"Interview Scheduled: {slot.application.job.title}",
            message = (
                f"Hi {slot.applicant.username},\n\n"
                "Your interview has been successfully scheduled. Please find the details below:\n\n"
                f"Position: {slot.application.job.title}\n"
                f"Company: {slot.application.job.company}\n"
                f"Date and Time: "
                f"{timezone.localtime(slot.start_at).strftime('%b %d, %Y %I:%M %p')} - "
                f"{timezone.localtime(slot.end_at).strftime('%I:%M %p')}\n\n"
                f"Add to Google Calendar: {gcal_url}\n\n"
                "You can also download the calendar invitation file from your PandaPulse dashboard.\n\n"
                "If you need to reschedule or have any questions, please log in to your account for next steps.\n\n"
                "Best regards,\n"
                "The PandaPulse Team"
            ),
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@pandapulse.local"),
            recipient_list=[slot.applicant.email],
            fail_silently=True,
        )
    if slot.employer.email:
        send_mail(
            subject = f"Interview Confirmed: {slot.applicant.username}",
            message = (
                f"Hi {slot.employer.username},\n\n"
                f"{slot.applicant.username} has confirmed their interview by selecting an available time slot.\n\n"
                f"Position: {slot.application.job.title}\n"
                f"Date and Time: "
                f"{timezone.localtime(slot.start_at).strftime('%b %d, %Y %I:%M %p')} - "
                f"{timezone.localtime(slot.end_at).strftime('%I:%M %p')}\n\n"
                f"Add to Google Calendar: {gcal_url}\n\n"
                "You can review the candidate’s application and manage interview details "
                "from your PandaPulse dashboard.\n\n"
                "Best regards,\n"
                "The PandaPulse Team"
            ),
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@pandapulse.local"),
            recipient_list=[slot.employer.email],
            fail_silently=True,
        )


def create_slot_from_form(form):
    application = form.cleaned_data["application"]
    return InterviewSlot.create_from_duration(
        application=application,
        start_at=form.cleaned_data["start_at"],
        duration_minutes=form.cleaned_data["duration_minutes"],
        meeting_link=form.cleaned_data["meeting_link"],
        notes=form.cleaned_data["notes"],
    )


def mark_application_interview(application):
    if application.status not in {"interview", "offer", "closed"}:
        application.status = "interview"
        application.responded_at = timezone.now()
        application.save(update_fields=["status", "responded_at"])
