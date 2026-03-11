from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from jobposts.models import JobPost

from .models import Application


class ApplicationPrivateNotesTests(TestCase):
    def setUp(self):
        self.applicant = User.objects.create_user(username="private_notes_applicant", password="pass12345")
        self.other_applicant = User.objects.create_user(
            username="private_notes_other_applicant",
            password="pass12345",
        )
        self.employer = User.objects.create_user(username="private_notes_employer", password="pass12345")
        self.other_employer = User.objects.create_user(
            username="private_notes_other_employer",
            password="pass12345",
        )

        self.job = JobPost.objects.create(
            owner=self.employer,
            title="Backend Engineer",
            company="Acme",
            location="Atlanta",
            pay_range="$100k-$130k",
            skills="Python, Django",
            description="Build APIs",
        )
        self.application = Application.objects.create(
            user=self.applicant,
            job=self.job,
            note="Initial note",
            resume_type="profile",
        )

    def test_applicant_can_save_their_private_note(self):
        self.client.login(username="private_notes_applicant", password="pass12345")
        response = self.client.post(
            reverse("apply:save_applicant_private_note", kwargs={"application_id": self.application.id}),
            data={"applicant_private_note": "Remember to follow up in one week."},
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("apply:application_status"), response.url)
        self.assertIn("tab=tab-applications", response.url)

        self.application.refresh_from_db()
        self.assertEqual(self.application.applicant_private_note, "Remember to follow up in one week.")
        self.assertEqual(self.application.employer_private_note, "")

    def test_applicant_cannot_save_note_for_other_users_application(self):
        self.client.login(username="private_notes_other_applicant", password="pass12345")
        response = self.client.post(
            reverse("apply:save_applicant_private_note", kwargs={"application_id": self.application.id}),
            data={"applicant_private_note": "Unauthorized update"},
        )
        self.assertEqual(response.status_code, 404)

    def test_employer_can_save_private_note_on_pipeline(self):
        self.client.login(username="private_notes_employer", password="pass12345")
        response = self.client.post(
            reverse("apply:save_employer_private_note", kwargs={"application_id": self.application.id}),
            data={"employer_private_note": "Strong communication skills."},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url,
            reverse("apply:employer_pipeline", kwargs={"job_id": self.job.id}),
        )

        self.application.refresh_from_db()
        self.assertEqual(self.application.employer_private_note, "Strong communication skills.")
        self.assertEqual(self.application.applicant_private_note, "")

    def test_other_employer_cannot_save_private_note(self):
        self.client.login(username="private_notes_other_employer", password="pass12345")
        response = self.client.post(
            reverse("apply:save_employer_private_note", kwargs={"application_id": self.application.id}),
            data={"employer_private_note": "Unauthorized update"},
        )
        self.assertEqual(response.status_code, 403)

    def test_private_notes_are_only_visible_to_their_side(self):
        self.application.applicant_private_note = "APPLICANT_PRIVATE_NOTE_TOKEN"
        self.application.employer_private_note = "EMPLOYER_PRIVATE_NOTE_TOKEN"
        self.application.save(update_fields=["applicant_private_note", "employer_private_note"])

        self.client.login(username="private_notes_applicant", password="pass12345")
        applicant_response = self.client.get(reverse("apply:application_status"))
        self.assertContains(applicant_response, "APPLICANT_PRIVATE_NOTE_TOKEN")
        self.assertNotContains(applicant_response, "EMPLOYER_PRIVATE_NOTE_TOKEN")

        self.client.login(username="private_notes_employer", password="pass12345")
        employer_response = self.client.get(
            reverse("apply:employer_pipeline", kwargs={"job_id": self.job.id})
        )
        self.assertContains(employer_response, "EMPLOYER_PRIVATE_NOTE_TOKEN")
        self.assertNotContains(employer_response, "APPLICANT_PRIVATE_NOTE_TOKEN")
