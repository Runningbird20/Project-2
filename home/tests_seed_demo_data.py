import shutil
import tempfile
from pathlib import Path
import random

from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model

from accounts.models import Profile, SavedCandidateSearch
from apply.models import Application
from interviews.models import InterviewFeedback, InterviewSlot
from jobposts.models import ApplicantJobMatch
from messaging.models import Message
from seed_demo_data import (
    APPLICANT_RESUME_TEMPLATE_PATH,
    align_jobs_with_applicants,
    build_employer_response_profiles,
    create_applicant_job_matches,
    create_applicants,
    create_applications,
    create_employers,
    create_interviews_feedback_and_endorsements,
    create_jobs,
    create_messages_for_applications,
    create_saved_candidate_alerts,
    clear_seed_data,
    enrich_application_feature_data,
    ensure_seed_superuser,
    SEED_SUPERUSER_EMAIL,
    SEED_SUPERUSER_USERNAME,
)


class SeedDemoDataApplicantResumeTests(TestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(self.media_root, ignore_errors=True))

    def test_create_applicants_assigns_2025_template_resume_to_profiles(self):
        with self.settings(MEDIA_ROOT=self.media_root):
            applicants = create_applicants("resume_seed", 1, "Pass12345!")
            self.assertEqual(len(applicants), 1)

            profile = Profile.objects.get(user=applicants[0])
            self.assertEqual(profile.account_type, Profile.AccountType.APPLICANT)
            self.assertTrue(bool(profile.resume_file))
            self.assertTrue(Path(profile.resume_file.path).exists())
            self.assertNotEqual(Path(profile.resume_file.path), APPLICANT_RESUME_TEMPLATE_PATH)
            self.assertEqual(
                Path(profile.resume_file.path).read_bytes(),
                APPLICANT_RESUME_TEMPLATE_PATH.read_bytes(),
            )

    def test_seed_helpers_populate_dashboard_feature_data(self):
        random.seed(7)
        with self.settings(MEDIA_ROOT=self.media_root):
            employers = create_employers("feature_seed", 2, "Pass12345!")
            applicants = create_applicants("feature_seed", 4, "Pass12345!")
            jobs = create_jobs("feature_seed", employers, 6)
            aligned_jobs = align_jobs_with_applicants(jobs, applicants)
            response_profiles = build_employer_response_profiles(employers)
            applications = create_applications(
                applicants,
                jobs,
                min_per_applicant=2,
                max_per_applicant=2,
                employer_response_profiles=response_profiles,
            )
            application_feature_stats = enrich_application_feature_data(applications)
            alert_stats = create_saved_candidate_alerts(employers, applicants)
            match_stats = create_applicant_job_matches(applicants, jobs, applications)
            message_stats = create_messages_for_applications(applications)
            interview_stats = create_interviews_feedback_and_endorsements(
                applications,
                interview_probability=1.0,
                feedback_probability=1.0,
                endorsement_probability=1.0,
            )

        self.assertGreater(aligned_jobs, 0)
        self.assertEqual(alert_stats["saved_searches"], SavedCandidateSearch.objects.count())
        self.assertGreater(match_stats["job_matches"], 0)
        self.assertEqual(match_stats["job_matches"], ApplicantJobMatch.objects.count())
        self.assertGreater(message_stats["messages"], 0)
        self.assertEqual(message_stats["messages"], Message.objects.count())
        self.assertGreaterEqual(application_feature_stats["offer_letters"], 1)
        self.assertTrue(
            Application.objects.filter(status__in=["offer", "closed"]).exclude(offer_letter_title="").exists()
        )
        self.assertTrue(
            Application.objects.filter(status="rejected", rejection_feedback_sent_at__isnull=False).exists()
        )
        self.assertTrue(
            Application.objects.filter(status="rejected", archived_by_employer=True).exists()
        )
        self.assertGreater(interview_stats["upcoming_booked_slots"], 0)
        self.assertTrue(
            InterviewSlot.objects.filter(
                status=InterviewSlot.Status.BOOKED,
                start_at__gt=timezone.now(),
            ).exists()
        )
        self.assertTrue(InterviewSlot.objects.filter(status=InterviewSlot.Status.OPEN).exists())
        self.assertTrue(InterviewFeedback.objects.exists())

    def test_ensure_seed_superuser_creates_and_preserves_seed_sup_1(self):
        user_model = get_user_model()
        existing_user = user_model.objects.create_user(
            username=SEED_SUPERUSER_USERNAME,
            email="wrong@example.com",
            password="old-password",
        )

        user, created = ensure_seed_superuser("Pass12345!")

        self.assertFalse(created)
        self.assertEqual(user.id, existing_user.id)
        self.assertEqual(user.email, SEED_SUPERUSER_EMAIL)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.check_password("Pass12345!"))
        self.assertTrue(Profile.objects.filter(user=user, account_type=Profile.AccountType.EMPLOYER).exists())

        deleted_users, _ = clear_seed_data("seed")

        self.assertEqual(deleted_users, 0)
        self.assertTrue(user_model.objects.filter(username=SEED_SUPERUSER_USERNAME).exists())
