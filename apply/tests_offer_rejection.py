from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from jobposts.models import JobPost
from .models import Application


class OfferRejectionFlowTests(TestCase):
    def setUp(self):
        self.applicant = User.objects.create_user(username="offer_applicant", password="pass12345")
        self.other_user = User.objects.create_user(username="other_user", password="pass12345")
        self.employer = User.objects.create_user(username="offer_employer", password="pass12345")
        self.job = JobPost.objects.create(
            owner=self.employer,
            title="Platform Engineer",
            company="Acme",
            location="Atlanta",
            pay_range="$120k-$160k",
            skills="Python, AWS",
            description="Build platform services",
        )
        self.application = Application.objects.create(
            user=self.applicant,
            job=self.job,
            note="I am interested",
            resume_type="profile",
            status="offer",
            responded_at=timezone.now(),
        )

    def test_applicant_can_reject_offer(self):
        self.client.login(username="offer_applicant", password="pass12345")
        response = self.client.post(
            reverse("apply:reject_offer", kwargs={"application_id": self.application.id}),
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, "rejected")
        self.assertTrue(self.application.rejected_offer_by_applicant)
        self.assertIsNotNone(self.application.rejected_at)

    def test_offer_rejection_is_reflected_in_employer_pipeline(self):
        self.client.login(username="offer_applicant", password="pass12345")
        self.client.post(reverse("apply:reject_offer", kwargs={"application_id": self.application.id}))

        self.client.login(username="offer_employer", password="pass12345")
        response = self.client.get(reverse("apply:employer_pipeline", kwargs={"job_id": self.job.id}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Offer rejected by applicant")

    def test_non_owner_cannot_reject_other_applicant_offer(self):
        self.client.login(username="other_user", password="pass12345")
        response = self.client.post(reverse("apply:reject_offer", kwargs={"application_id": self.application.id}))
        self.assertEqual(response.status_code, 404)

    def test_rejected_offer_auto_archives_after_30_days(self):
        Application.objects.filter(id=self.application.id).update(
            status="rejected",
            rejected_offer_by_applicant=True,
            rejected_at=timezone.now() - timedelta(days=31),
        )
        self.client.login(username="offer_applicant", password="pass12345")
        self.client.get(reverse("apply:application_status"))
        self.application.refresh_from_db()
        self.assertTrue(self.application.archived_by_applicant)
        self.assertTrue(self.application.archived_by_employer)

