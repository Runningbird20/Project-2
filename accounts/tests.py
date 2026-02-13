from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Profile


class ProfilePrivacyAuthorizationTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()
        self.owner = self.user_model.objects.create_user(
            username="owner",
            password="test-password-123",
        )
        self.other_user = self.user_model.objects.create_user(
            username="other",
            password="test-password-123",
        )

        self.owner_profile, _ = Profile.objects.get_or_create(user=self.owner)
        self.owner_profile.visible_to_recruiters = True
        self.owner_profile.show_headline = True
        self.owner_profile.show_skills = True
        self.owner_profile.show_education = True
        self.owner_profile.show_work_experience = True
        self.owner_profile.show_links = True
        self.owner_profile.save()

        self.other_profile, _ = Profile.objects.get_or_create(user=self.other_user)
        self.other_profile.visible_to_recruiters = True
        self.other_profile.show_headline = True
        self.other_profile.show_skills = True
        self.other_profile.show_education = True
        self.other_profile.show_work_experience = True
        self.other_profile.show_links = True
        self.other_profile.save()

    def test_user_can_update_own_privacy_settings(self):
        self.client.login(username="owner", password="test-password-123")

        response = self.client.post(
            reverse("accounts.profile_edit"),
            {
                "headline": self.owner_profile.headline,
                "skills": self.owner_profile.skills,
                "education": self.owner_profile.education,
                "work_experience": self.owner_profile.work_experience,
                # Unchecked checkboxes are omitted by browsers; include only selected fields.
                "show_headline": "on",
                "show_skills": "on",
                "show_education": "on",
                "show_work_experience": "on",
                "show_links": "on",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.owner_profile.refresh_from_db()
        self.assertFalse(self.owner_profile.visible_to_recruiters)

    def test_user_cannot_update_another_users_privacy_settings(self):
        self.client.login(username="owner", password="test-password-123")

        response = self.client.post(
            reverse("accounts.profile_edit_user", kwargs={"username": "other"}),
            {
                "headline": self.other_profile.headline,
                "skills": self.other_profile.skills,
                "education": self.other_profile.education,
                "work_experience": self.other_profile.work_experience,
            },
        )

        self.assertEqual(response.status_code, 403)
        self.other_profile.refresh_from_db()
        self.assertTrue(self.other_profile.visible_to_recruiters)
