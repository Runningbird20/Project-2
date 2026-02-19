from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from apply.models import Application
from accounts.models import Profile

from .models import ApplicantJobMatch, JobPost

MIN_MATCH_PERCENT = 50


def _skill_set(raw_value):
    if not raw_value:
        return set()
    return {
        token.strip().lower()
        for token in raw_value.split(",")
        if token.strip()
    }


def _skill_overlap_percent(applicant_skills, job_skills):
    if not applicant_skills or not job_skills:
        return 0
    overlap_count = len(applicant_skills.intersection(job_skills))
    return round((overlap_count / len(job_skills)) * 100)


def sync_applicant_job_matches(applicant_user):
    profile = Profile.objects.filter(user=applicant_user).first()
    if not profile or profile.account_type != Profile.AccountType.APPLICANT:
        return []

    applicant_skills = _skill_set(profile.skills)
    if not applicant_skills:
        return []

    applied_job_ids = set(
        Application.objects.filter(user=applicant_user).values_list("job_id", flat=True)
    )

    matched_job_ids = set()
    candidate_jobs = JobPost.objects.select_related("owner").exclude(id__in=applied_job_ids)
    for job in candidate_jobs:
        job_skills = _skill_set(job.skills)
        if not job_skills:
            continue

        overlap = sorted(applicant_skills.intersection(job_skills))
        match_percent = _skill_overlap_percent(applicant_skills, job_skills)
        if not overlap or match_percent <= MIN_MATCH_PERCENT:
            continue

        matched_job_ids.add(job.id)
        matched_skills = ", ".join(overlap)
        score = len(overlap)

        match, created = ApplicantJobMatch.objects.get_or_create(
            applicant=applicant_user,
            job=job,
            defaults={"score": score, "matched_skills": matched_skills},
        )

        fields_to_update = []
        if match.score != score:
            match.score = score
            fields_to_update.append("score")
        if match.matched_skills != matched_skills:
            match.matched_skills = matched_skills
            fields_to_update.append("matched_skills")
        if fields_to_update:
            fields_to_update.append("updated_at")
            match.save(update_fields=fields_to_update)

        if match.employer_notified_at is None and job.owner and job.owner.email:
            send_mail(
                subject=f"New applicant-job skill match: {job.title}",
                message=(
                    f"Hi {job.owner.username},\n\n"
                    f"A new candidate has been identified as a strong match for your role, "
                    f"{job.title}.\n\n"
                    f"Applicant: {applicant_user.username}\n"
                    f"Matched skills: {matched_skills}\n\n"
                    "Based on the skills listed in their profile, this applicant aligns "
                    "well with the requirements of your position. We recommend reviewing "
                    "their profile to determine next steps.\n\n"
                    "Log in to PandaPulse to view the full application details and connect "
                    "with the candidate.\n\n"
                    "Best regards,\n"
                    "The PandaPulse Team\n"
                ),
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@pandapulse.local"),
                recipient_list=[job.owner.email],
                fail_silently=True,
            )
            match.employer_notified_at = timezone.now()
            match.save(update_fields=["employer_notified_at", "updated_at"])

        if created and applicant_user.email:
            send_mail(
                subject=f"New job match: {job.title}",
                message=(
                    f"Hi {applicant_user.username},\n\n"
                    "Great news. A new opportunity has been identified as a strong match "
                    "for your profile.\n\n"
                    f"Position: {job.title}\n"
                    f"Company: {job.company}\n"
                    f"Matched skills: {matched_skills}\n\n"
                    "Based on the skills listed in your profile, this role closely aligns "
                    "with your experience and qualifications. We encourage you to review the "
                    "job details and consider applying.\n\n"
                    "Log in to PandaPulse to explore this opportunity and take the next step "
                    "in your career journey.\n\n"
                    "Best of luck,\n"
                    "The PandaPulse Team\n"
                ),
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@pandapulse.local"),
                recipient_list=[applicant_user.email],
                fail_silently=True,
            )

    ApplicantJobMatch.objects.filter(applicant=applicant_user).exclude(job_id__in=matched_job_ids).delete()

    ordered_matches = ApplicantJobMatch.objects.filter(applicant=applicant_user).select_related("job").order_by(
        "-score", "-updated_at"
    )
    return [match.job for match in ordered_matches[:5]]
