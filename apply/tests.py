from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

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
