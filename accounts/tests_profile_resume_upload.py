import shutil
import tempfile
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import Profile, SkillOption


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class ProfileResumeUploadTests(TestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(self.media_root, ignore_errors=True))
        self.user = User.objects.create_user(username="resume_owner", password="pass12345")
        Profile.objects.create(
            user=self.user,
            account_type=Profile.AccountType.APPLICANT,
        )

    @patch("accounts.views.parse_resume", return_value={"skills": ["python", "django"], "raw_text": "resume"})
    def test_applicant_can_upload_pdf_resume_from_profile_edit(self, _mock_parse_resume):
        with self.settings(MEDIA_ROOT=self.media_root):
            self.client.login(username="resume_owner", password="pass12345")
            resume_file = SimpleUploadedFile(
                "candidate_resume.pdf",
                b"%PDF-1.4 fake profile resume",
                content_type="application/pdf",
            )

            response = self.client.post(
                reverse("accounts.profile_edit"),
                {
                    "account_type": Profile.AccountType.APPLICANT,
                    "headline": "",
                    "skills": "",
                    "projects": "",
                    "education": "",
                    "work_experience": "",
                    "resume_file": resume_file,
                },
            )

        self.assertEqual(response.status_code, 302)
        profile = Profile.objects.get(user=self.user)
        self.assertTrue(bool(profile.resume_file))
        self.assertEqual(profile.resume_file_name, "candidate_resume.pdf")
        self.assertEqual(profile.parsed_resume_skills, "python, django")
        self.assertEqual(profile.skills, "python, django")

    @patch("accounts.views.parse_resume", return_value={"skills": ["python"], "raw_text": "resume"})
    def test_profile_page_shows_open_resume_action_after_upload(self, _mock_parse_resume):
        with self.settings(MEDIA_ROOT=self.media_root):
            self.client.login(username="resume_owner", password="pass12345")
            resume_file = SimpleUploadedFile(
                "candidate_resume.pdf",
                b"%PDF-1.4 fake profile resume",
                content_type="application/pdf",
            )
            self.client.post(
                reverse("accounts.profile_edit"),
                {
                    "account_type": Profile.AccountType.APPLICANT,
                    "headline": "",
                    "skills": "",
                    "projects": "",
                    "education": "",
                    "work_experience": "",
                    "resume_file": resume_file,
                },
            )
            response = self.client.get(reverse("accounts.profile"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Open Resume")
        self.assertContains(response, "candidate_resume.pdf")

    @patch("accounts.views.parse_resume", return_value={"skills": ["LangChain", "Python"], "raw_text": "resume"})
    def test_profile_resume_upload_registers_new_skills_for_shared_dropdowns(self, _mock_parse_resume):
        with self.settings(MEDIA_ROOT=self.media_root):
            self.client.login(username="resume_owner", password="pass12345")
            resume_file = SimpleUploadedFile(
                "candidate_resume.pdf",
                b"%PDF-1.4 fake profile resume",
                content_type="application/pdf",
            )

            response = self.client.post(
                reverse("accounts.profile_edit"),
                {
                    "account_type": Profile.AccountType.APPLICANT,
                    "headline": "",
                    "skills": "",
                    "projects": "",
                    "education": "",
                    "work_experience": "",
                    "resume_file": resume_file,
                },
            )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(SkillOption.objects.filter(normalized_name="langchain").exists())

    def test_profile_resume_upload_rejects_non_pdf_files(self):
        with self.settings(MEDIA_ROOT=self.media_root):
            self.client.login(username="resume_owner", password="pass12345")
            resume_file = SimpleUploadedFile(
                "candidate_resume.txt",
                b"Python Django AWS",
                content_type="text/plain",
            )

            response = self.client.post(
                reverse("accounts.profile_edit"),
                {
                    "account_type": Profile.AccountType.APPLICANT,
                    "headline": "",
                    "skills": "",
                    "projects": "",
                    "education": "",
                    "work_experience": "",
                    "resume_file": resume_file,
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Upload a PDF resume.")
        profile = Profile.objects.get(user=self.user)
        self.assertFalse(bool(profile.resume_file))
