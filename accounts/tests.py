from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
<<<<<<< HEAD
from django.core import mail
from django.test.utils import override_settings
=======
from unittest.mock import patch
>>>>>>> d01baced0c73dcc3eed56bd8efb0232142b26b68

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

    def test_public_profile_hides_street_address_for_non_owner(self):
        self.owner_profile.location = "123 Peachtree St NE, Atlanta, GA 30303"
        self.owner_profile.save(update_fields=["location"])
        self.owner.email = "owner@example.com"
        self.owner.save(update_fields=["email"])

        response = self.client.get(
            reverse("accounts.public_profile", kwargs={"username": self.owner.username})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Atlanta, GA")
        self.assertContains(response, "owner@example.com")
        self.assertNotContains(response, "123 Peachtree St NE")

<<<<<<< HEAD
    def test_public_profile_hides_email_when_toggle_is_enabled(self):
        self.owner.email = "owner@example.com"
        self.owner.save(update_fields=["email"])
        self.owner_profile.hide_email_from_employers = True
        self.owner_profile.save(update_fields=["hide_email_from_employers"])

        response = self.client.get(
            reverse("accounts.public_profile", kwargs={"username": self.owner.username})
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "owner@example.com")


class AccountRecoveryTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()
        self.user_model.objects.create_user(
            username="recover_me",
            email="recover@example.com",
            password="test-password-123",
        )

    def test_forgot_username_page_loads(self):
        response = self.client.get(reverse("accounts.forgot_username"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Forgot Username")

    def test_forgot_username_sends_email_when_match_exists(self):
        response = self.client.post(
            reverse("accounts.forgot_username"),
            {"email": "recover@example.com"},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(mail.outbox), 1)
        self.assertIn("recover_me", mail.outbox[0].body)

    def test_password_reset_form_page_loads(self):
        response = self.client.get(reverse("accounts.password_reset"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Forgot Password")


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class AdminEmailDiagnosticsTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()
        self.staff = self.user_model.objects.create_user(
            username="staff_user",
            email="staff@example.com",
            password="test-password-123",
            is_staff=True,
        )

    def test_staff_can_send_test_email(self):
        self.client.login(username="staff_user", password="test-password-123")
        response = self.client.post(
            reverse("accounts.send_test_email"),
            {"test_email_to": "recipient@example.com"},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("PandaPulse test email", mail.outbox[0].subject)

    def test_send_test_email_requires_recipient_or_account_email(self):
        self.staff.email = "staff@example.com"
        self.staff.save(update_fields=["email"])
        self.client.login(username="staff_user", password="test-password-123")
        response = self.client.post(
            reverse("accounts.send_test_email"),
            {"test_email_to": ""},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)
=======

class ApplicantClustersMapAccessTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()
        self.staff = self.user_model.objects.create_user(
            username="staff",
            password="test-password-123",
            is_staff=True,
        )
        self.non_staff = self.user_model.objects.create_user(
            username="notstaff",
            password="test-password-123",
        )
        self.applicant = self.user_model.objects.create_user(
            username="applicant",
            password="test-password-123",
        )
        Profile.objects.update_or_create(
            user=self.applicant,
            defaults={
                "account_type": Profile.AccountType.APPLICANT,
                "location": "123 Peachtree St NE, Atlanta, GA 30303",
            },
        )

    def test_non_staff_cannot_access_applicant_clusters_map(self):
        self.client.login(username="notstaff", password="test-password-123")
        response = self.client.get(reverse("accounts.applicant_clusters_map"))
        self.assertEqual(response.status_code, 302)

    @patch("accounts.views.geocode_office_address", return_value=("33.748997", "-84.387985"))
    def test_staff_can_view_applicant_clusters_map(self, _mock_geocode):
        self.client.login(username="staff", password="test-password-123")
        response = self.client.get(reverse("accounts.applicant_clusters_map"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Applicant Location Clusters")
        self.assertContains(response, "Atlanta, GA")
>>>>>>> d01baced0c73dcc3eed56bd8efb0232142b26b68
