from collections import defaultdict

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import Profile, SavedCandidateSearch
from apply.models import Application
from jobposts.models import JobPost

MIN_MATCH_PERCENT = 50


def _skill_set(raw_value):
    if not raw_value:
        return set()
    return {token.strip().lower() for token in raw_value.split(",") if token.strip()}


def _skill_overlap_percent(applicant_skills, job_skills):
    if not applicant_skills or not job_skills:
        return 0
    overlap_count = len(applicant_skills.intersection(job_skills))
    return round((overlap_count / len(job_skills)) * 100)


class Command(BaseCommand):
    help = (
        "Send match digest emails to applicants, employers, and recruiter saved-search alerts "
        "on Tuesdays/Thursdays at 12 PM (local server time)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Send regardless of weekday/time window.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Compute digests but do not send emails.",
        )

    def handle(self, *args, **options):
        force = options["force"]
        dry_run = options["dry_run"]

        now = timezone.localtime()
        is_allowed_day = now.weekday() in {1, 3}  # Tuesday, Thursday
        is_allowed_hour = now.hour == 12

        if not force and not (is_allowed_day and is_allowed_hour):
            self.stdout.write(
                self.style.WARNING(
                    "Skipped: only runs Tuesdays/Thursdays at 12 PM local time. "
                    "Use --force to run now."
                )
            )
            return

        applicants = list(
            Profile.objects.filter(
                account_type=Profile.AccountType.APPLICANT,
                visible_to_recruiters=True,
            ).select_related("user")
        )
        jobs = list(JobPost.objects.select_related("owner").all())
        saved_searches = list(
            SavedCandidateSearch.objects.select_related("employer").order_by("-created_at")
        )

        if not applicants and not jobs and not saved_searches:
            self.stdout.write(self.style.SUCCESS("Nothing to send: no applicants, jobs, or saved alerts."))
            return

        applied_pairs = set(Application.objects.values_list("user_id", "job_id"))
        applicant_skill_map = {p.user_id: _skill_set(p.skills) for p in applicants}
        job_skill_map = {job.id: _skill_set(job.skills) for job in jobs}

        applicant_sent = 0
        employer_sent = 0
        saved_alert_sent = 0

        # Applicant digests: matching jobs not yet applied.
        for profile in applicants:
            user = profile.user
            if not user.email:
                continue

            user_skills = applicant_skill_map.get(user.id, set())
            if not user_skills:
                continue

            matched_jobs = []
            for job in jobs:
                if (user.id, job.id) in applied_pairs:
                    continue
                if _skill_overlap_percent(user_skills, job_skill_map.get(job.id, set())) > MIN_MATCH_PERCENT:
                    matched_jobs.append(job)

            if not matched_jobs:
                continue

            lines = [f"- {job.title} at {job.company} ({job.location})" for job in matched_jobs[:20]]
            message = (
                f"Hi {user.username},\n\n"
                "Here are some job postings that match your skills and that you have not applied to yet:\n\n"
                f"{chr(10).join(lines)}\n\n"
                "Log in to PandaPulse to view full details and apply.\n\n"
                "Best regards,\n"
                "The PandaPulse Team"
            )

            if dry_run:
                self.stdout.write(f"[DRY RUN] Applicant digest -> {user.email} ({len(matched_jobs)} matches)")
            else:
                send_mail(
                    subject="PandaPulse Match Digest: New jobs for you",
                    message=message,
                    from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@pandapulse.local"),
                    recipient_list=[user.email],
                    fail_silently=False,
                )
                applicant_sent += 1

        # Employer digests: matching candidates per job where they have not applied yet.
        employer_matches = defaultdict(lambda: defaultdict(list))
        for job in jobs:
            if not job.owner or not job.owner.email:
                continue
            job_skills = job_skill_map.get(job.id, set())
            if not job_skills:
                continue

            for profile in applicants:
                user = profile.user
                if (user.id, job.id) in applied_pairs:
                    continue
                if _skill_overlap_percent(applicant_skill_map.get(user.id, set()), job_skills) > MIN_MATCH_PERCENT:
                    employer_matches[job.owner][job].append(user.username)

        for employer, job_to_candidates in employer_matches.items():
            if not employer.email:
                continue

            sections = []
            for job, usernames in job_to_candidates.items():
                limited_names = ", ".join(usernames[:25])
                sections.append(f"- {job.title}: {limited_names}")

            message = (
                f"Hi {employer.username},\n\n"
                "Here are candidates who match your job postings and have not applied yet:\n\n"
                f"{chr(10).join(sections)}\n\n"
                "Log in to PandaPulse to review matches."
            )

            if dry_run:
                self.stdout.write(
                    f"[DRY RUN] Employer digest -> {employer.email} ({len(job_to_candidates)} jobs with matches)"
                )
            else:
                send_mail(
                    subject="PandaPulse Match Digest: New candidates for your jobs",
                    message=message,
                    from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@pandapulse.local"),
                    recipient_list=[employer.email],
                    fail_silently=False,
                )
                employer_sent += 1

        for saved_search in saved_searches:
            employer = saved_search.employer
            if not employer or not employer.email:
                continue

            matched_profiles = list(saved_search.matches_to_notify_queryset()[:25])
            if not matched_profiles:
                continue

            lines = []
            for profile in matched_profiles:
                headline = f" - {profile.headline}" if profile.headline else ""
                location = f" ({profile.location_city_state})" if profile.location_city_state else ""
                lines.append(f"- {profile.user.username}{headline}{location}")

            filter_summary = saved_search.filters_summary

            message = (
                f"Hi {employer.username},\n\n"
                f'Your PandaPulse saved alert "{saved_search.search_name}" has new matching candidates.\n\n'
                f"Alert filters: {filter_summary}\n\n"
                "New candidate matches:\n\n"
                f"{chr(10).join(lines)}\n\n"
                "Log in to PandaPulse to review the candidates and continue outreach.\n\n"
                "Best regards,\n"
                "The PandaPulse Team"
            )

            if dry_run:
                self.stdout.write(
                    f'[DRY RUN] Saved alert email -> {employer.email} ("{saved_search.search_name}", {len(matched_profiles)} matches)'
                )
            else:
                send_mail(
                    subject=f'PandaPulse Alert: {saved_search.search_name}',
                    message=message,
                    from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@pandapulse.local"),
                    recipient_list=[employer.email],
                    fail_silently=False,
                )
                saved_search.mark_notified()
                saved_alert_sent += 1

        if dry_run:
            self.stdout.write(self.style.SUCCESS("Dry run complete."))
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Digests sent. Applicant emails: {applicant_sent}. Employer emails: {employer_sent}. "
                    f"Saved alert emails: {saved_alert_sent}."
                )
            )
