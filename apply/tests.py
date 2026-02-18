from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from jobposts.models import JobPost
from .models import Application


class SubmitApplicationTests(TestCase):
    def setUp(self):
        self.applicant = User.objects.create_user(username="applicant", password="pass12345")
        self.employer = User.objects.create_user(username="employer", password="pass12345")
        self.job = JobPost.objects.create(
            owner=self.employer,
            title="Backend Engineer",
            company="Acme",
            location="Atlanta",
            pay_range="$100k-$130k",
            skills="Python, Django",
            description="Build APIs",
        )

    def test_submit_application_succeeds_without_profile_address(self):
        self.client.login(username="applicant", password="pass12345")

        response = self.client.post(
            reverse("apply:submit_application", kwargs={"job_id": self.job.id}),
            data={"resume_type": "profile", "note": "Interested"},
        )

        self.assertRedirects(
            response,
            reverse("apply:application_submitted", kwargs={"job_id": self.job.id}),
        )
        self.assertTrue(
            Application.objects.filter(user=self.applicant, job=self.job).exists()
        )

    def test_submit_application_succeeds_with_profile_address(self):
        self.client.login(username="applicant", password="pass12345")

        response = self.client.post(
            reverse("apply:submit_application", kwargs={"job_id": self.job.id}),
            data={"resume_type": "profile", "note": "Interested"},
        )

        self.assertRedirects(
            response,
            reverse("apply:application_submitted", kwargs={"job_id": self.job.id}),
        )
        self.assertTrue(
            Application.objects.filter(user=self.applicant, job=self.job).exists()
        )


class EmployerViewedStatusTests(TestCase):
    def setUp(self):
        self.applicant = User.objects.create_user(username="applicant2", password="pass12345")
        self.employer = User.objects.create_user(username="employer2", password="pass12345")
        self.job = JobPost.objects.create(
            owner=self.employer,
            title="Frontend Engineer",
            company="Acme",
            location="Atlanta",
            pay_range="$90k-$120k",
            skills="React, CSS",
            description="Build UI",
        )
        self.application = Application.objects.create(
            user=self.applicant,
            job=self.job,
            note="Excited to apply",
            resume_type="profile",
        )

    def test_employer_pipeline_marks_applications_as_viewed(self):
        self.client.login(username="employer2", password="pass12345")
        self.client.get(reverse("apply:employer_pipeline", kwargs={"job_id": self.job.id}))
        self.application.refresh_from_db()
        self.assertTrue(self.application.employer_viewed)
        self.assertIsNotNone(self.application.employer_viewed_at)

    def test_application_status_page_shows_not_viewed_message(self):
        self.client.login(username="applicant2", password="pass12345")
        response = self.client.get(reverse("apply:application_status"))
        self.assertContains(response, "Not viewed by employer yet")

    def test_application_status_page_shows_viewed_message(self):
        self.application.employer_viewed = True
        self.application.employer_viewed_at = self.application.applied_at
        self.application.save(update_fields=["employer_viewed", "employer_viewed_at"])

        self.client.login(username="applicant2", password="pass12345")
        response = self.client.get(reverse("apply:application_status"))
        self.assertContains(response, "Viewed by employer")


class ApplicationArchiveTests(TestCase):
    def setUp(self):
        self.applicant = User.objects.create_user(username="applicant3", password="pass12345")
        self.employer = User.objects.create_user(username="employer3", password="pass12345")
        self.job = JobPost.objects.create(
            owner=self.employer,
            title="QA Engineer",
            company="Acme",
            location="Atlanta",
            pay_range="$80k-$100k",
            skills="Testing",
            description="Test apps",
        )
        self.application = Application.objects.create(
            user=self.applicant,
            job=self.job,
            note="Please consider me",
            resume_type="profile",
            status="rejected",
            rejected_at=timezone.now(),
        )

    def test_applicant_can_archive_rejected_application(self):
        self.client.login(username="applicant3", password="pass12345")
        response = self.client.post(
            reverse("apply:archive_application", kwargs={"application_id": self.application.id}),
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.application.refresh_from_db()
        self.assertTrue(self.application.archived_by_applicant)

    def test_employer_can_archive_rejected_applicant(self):
        self.client.login(username="employer3", password="pass12345")
        response = self.client.post(
            reverse("apply:archive_rejected_applicant", kwargs={"application_id": self.application.id}),
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.application.refresh_from_db()
        self.assertTrue(self.application.archived_by_employer)

    def test_auto_archive_after_30_days(self):
        self.application.rejected_at = timezone.now() - timedelta(days=31)
        self.application.save(update_fields=["rejected_at"])

        self.client.login(username="applicant3", password="pass12345")
        self.client.get(reverse("apply:application_status"))
        self.application.refresh_from_db()
        self.assertTrue(self.application.archived_by_applicant)
        self.assertTrue(self.application.archived_by_employer)


class EmployerResponseDeadlineTests(TestCase):
    def setUp(self):
        self.applicant = User.objects.create_user(username="applicant4", password="pass12345")
        self.employer = User.objects.create_user(username="employer4", password="pass12345")
        self.job = JobPost.objects.create(
            owner=self.employer,
            title="DevOps Engineer",
            company="Acme",
            location="Atlanta",
            pay_range="$100k-$140k",
            skills="AWS, Terraform",
            description="Maintain cloud infra",
        )
        self.application = Application.objects.create(
            user=self.applicant,
            job=self.job,
            note="Ready to start",
            resume_type="profile",
            status="applied",
        )

    def test_overdue_unresponded_application_auto_rejects(self):
        Application.objects.filter(id=self.application.id).update(
            applied_at=timezone.now() - timedelta(days=31),
            responded_at=None,
        )

        self.client.login(username="applicant4", password="pass12345")
        self.client.get(reverse("apply:application_status"))
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, "rejected")
        self.assertTrue(self.application.auto_rejected_for_timeout)
        self.assertIsNotNone(self.application.rejected_at)

    def test_responded_application_does_not_auto_reject(self):
        self.client.login(username="employer4", password="pass12345")
        response = self.client.post(
            reverse("apply:update_status", kwargs={"application_id": self.application.id}),
            data='{"status":"review"}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

        Application.objects.filter(id=self.application.id).update(
            applied_at=timezone.now() - timedelta(days=31),
        )
        self.client.get(reverse("apply:employer_pipeline", kwargs={"job_id": self.job.id}))
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, "review")
        self.assertFalse(self.application.auto_rejected_for_timeout)

    def test_each_status_update_resets_30_day_deadline(self):
        old_time = timezone.now() - timedelta(days=31)
        Application.objects.filter(id=self.application.id).update(
            status="review",
            responded_at=old_time,
            applied_at=old_time,
        )

        self.client.login(username="employer4", password="pass12345")
        response = self.client.post(
            reverse("apply:update_status", kwargs={"application_id": self.application.id}),
            data='{"status":"interview"}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

        self.client.get(reverse("apply:employer_pipeline", kwargs={"job_id": self.job.id}))
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, "interview")
        self.assertFalse(self.application.auto_rejected_for_timeout)
