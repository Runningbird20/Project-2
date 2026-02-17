from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounts.models import Profile
from jobposts.models import JobPost
from .models import Application


class SubmitApplicationAddressRequirementTests(TestCase):
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

    def test_submit_application_requires_profile_address(self):
        Profile.objects.update_or_create(
            user=self.applicant,
            defaults={"location": ""},
        )
        self.client.login(username="applicant", password="pass12345")

        response = self.client.post(
            reverse("apply:submit_application", kwargs={"job_id": self.job.id}),
            data={"resume_type": "profile", "note": "Interested"},
        )

        self.assertRedirects(response, reverse("accounts.profile_edit"))
        self.assertFalse(
            Application.objects.filter(user=self.applicant, job=self.job).exists()
        )

    def test_submit_application_succeeds_when_profile_address_exists(self):
        Profile.objects.update_or_create(
            user=self.applicant,
            defaults={"location": "123 Peachtree St NE, Atlanta, GA 30303"},
        )
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
