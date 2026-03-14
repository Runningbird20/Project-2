import shutil
import tempfile

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from accounts.models import Profile
from apply.models import Application
from jobposts.models import JobPost


class ProfileResumeUsageTests(TestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(self.media_root, ignore_errors=True))
        self.applicant = User.objects.create_user(username="resume_applicant", password="pass12345")
        self.employer = User.objects.create_user(username="resume_employer", password="pass12345")
        Profile.objects.create(user=self.employer, account_type=Profile.AccountType.EMPLOYER)
        self.job = JobPost.objects.create(
            owner=self.employer,
            title="Backend Engineer",
            company="Acme",
            location="Atlanta",
            pay_range="$100k-$130k",
            skills="Python, Django",
            description="Build APIs",
        )

    def test_application_requires_profile_resume_when_profile_option_selected(self):
        with self.settings(MEDIA_ROOT=self.media_root):
            self.client.login(username="resume_applicant", password="pass12345")
            response = self.client.post(
                reverse("apply:submit_application", kwargs={"job_id": self.job.id}),
                data={"resume_type": "profile", "note": "Interested"},
            )

        self.assertRedirects(response, reverse("jobposts.detail", args=[self.job.id]))
        self.assertFalse(Application.objects.filter(user=self.applicant, job=self.job).exists())

    def test_application_can_use_stored_profile_resume(self):
        with self.settings(MEDIA_ROOT=self.media_root):
            profile = Profile.objects.create(
                user=self.applicant,
                account_type=Profile.AccountType.APPLICANT,
                resume_file=SimpleUploadedFile(
                    "profile_resume.pdf",
                    b"%PDF-1.4 profile resume",
                    content_type="application/pdf",
                ),
            )

            self.client.login(username="resume_applicant", password="pass12345")
            response = self.client.post(
                reverse("apply:submit_application", kwargs={"job_id": self.job.id}),
                data={"resume_type": "profile", "note": "Interested"},
            )

        self.assertRedirects(
            response,
            reverse("apply:application_submitted", kwargs={"job_id": self.job.id}),
        )
        application = Application.objects.get(user=self.applicant, job=self.job)
        self.assertEqual(application.resume_type, "profile")
        self.assertFalse(bool(application.resume_file))
        self.assertTrue(bool(profile.resume_file))
