from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from accounts.models import Profile
from apply.models import Application
from jobposts.models import JobPost


class ResumeProfileMergeTests(TestCase):
    def setUp(self):
        self.employer = User.objects.create_user(username="employer", password="pass12345")
        Profile.objects.create(user=self.employer, account_type=Profile.AccountType.EMPLOYER)
        self.applicant = User.objects.create_user(username="applicant", password="pass12345")
        Profile.objects.create(user=self.applicant, account_type=Profile.AccountType.APPLICANT)
        self.job = JobPost.objects.create(
            owner=self.employer,
            title="Backend Engineer",
            company="Acme Inc",
            location="Atlanta, GA",
            pay_range="$80k-$100k",
            skills="Python, Django",
            work_setting="hybrid",
            description="Build APIs",
        )

    def test_uploaded_application_resume_merges_parsed_skills_into_profile(self):
        self.client.login(username="applicant", password="pass12345")
        resume_file = SimpleUploadedFile(
            "resume.txt",
            b"Experienced Python and Django engineer with AWS deployments.",
            content_type="text/plain",
        )

        response = self.client.post(
            reverse("apply:submit_application", args=[self.job.id]),
            {
                "resume_type": "uploaded",
                "resume_file": resume_file,
                "note": "Interested",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Application.objects.filter(user=self.applicant, job=self.job).exists())
        profile = Profile.objects.get(user=self.applicant)
        self.assertEqual(profile.parsed_resume_skills, "python, django, aws")
        self.assertEqual(profile.skills, "python, django, aws")
