from datetime import timedelta

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from jobposts.models import JobPost
from messaging.models import Message
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


class EmployerRejectionFeedbackTests(TestCase):
    def setUp(self):
        self.applicant = User.objects.create_user(
            username="feedback_applicant",
            email="feedback_applicant@example.com",
            password="pass12345",
        )
        self.employer = User.objects.create_user(
            username="feedback_employer",
            password="pass12345",
        )
        self.job = JobPost.objects.create(
            owner=self.employer,
            title="ML Engineer",
            company="Acme",
            location="Atlanta",
            pay_range="$120k-$170k",
            skills="Python, ML",
            description="Build ML services",
        )
        self.application = Application.objects.create(
            user=self.applicant,
            job=self.job,
            note="Looking forward to this role",
            resume_type="profile",
            status="review",
            responded_at=timezone.now(),
        )

    def test_recruiter_can_send_rejection_feedback_template_and_note(self):
        self.client.login(username="feedback_employer", password="pass12345")
        response = self.client.post(
            reverse("apply:update_status", kwargs={"application_id": self.application.id}),
            data='{"status":"rejected","send_feedback":true,"feedback_template":"skills_alignment","feedback_note":"Your portfolio was strong; keep shipping production-ready projects."}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

        self.application.refresh_from_db()
        self.assertEqual(self.application.status, "rejected")
        self.assertEqual(self.application.rejection_feedback_template, "skills_alignment")
        self.assertEqual(
            self.application.rejection_feedback_note,
            "Your portfolio was strong; keep shipping production-ready projects.",
        )
        self.assertIsNotNone(self.application.rejection_feedback_sent_at)

        feedback_message = Message.objects.get(sender=self.employer, recipient=self.applicant)
        self.assertIn("Feedback for your ML Engineer application at Acme:", feedback_message.body)
        self.assertIn("Your portfolio was strong; keep shipping production-ready projects.", feedback_message.body)

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Recruiter feedback:", mail.outbox[0].body)

    def test_recruiter_can_reject_without_sending_feedback(self):
        self.client.login(username="feedback_employer", password="pass12345")
        response = self.client.post(
            reverse("apply:update_status", kwargs={"application_id": self.application.id}),
            data='{"status":"rejected","send_feedback":false}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

        self.application.refresh_from_db()
        self.assertEqual(self.application.status, "rejected")
        self.assertEqual(self.application.rejection_feedback_template, "")
        self.assertEqual(self.application.rejection_feedback_note, "")
        self.assertIsNone(self.application.rejection_feedback_sent_at)
        self.assertFalse(Message.objects.filter(sender=self.employer, recipient=self.applicant).exists())

    def test_invalid_feedback_template_is_rejected(self):
        self.client.login(username="feedback_employer", password="pass12345")
        response = self.client.post(
            reverse("apply:update_status", kwargs={"application_id": self.application.id}),
            data='{"status":"rejected","send_feedback":true,"feedback_template":"unknown_template"}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Invalid rejection feedback template", status_code=400)

