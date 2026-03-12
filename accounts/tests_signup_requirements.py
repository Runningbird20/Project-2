from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class SignupRequirementsTests(TestCase):
    def test_signup_page_shows_required_markers_and_password_rules(self):
        response = self.client.get(reverse("accounts.signup"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Fields marked with")
        self.assertContains(response, "required-indicator")
        self.assertContains(response, "At least 8 characters")
        self.assertContains(response, "At least 1 uppercase letter")
        self.assertContains(response, "At least 1 lowercase letter")
        self.assertContains(response, "At least 1 number")
        self.assertContains(response, "At least 1 special character")
        self.assertContains(response, "Passwords match")
        self.assertContains(response, "not too common")

    def test_signup_rejects_password_without_required_character_mix(self):
        response = self.client.post(
            reverse("accounts.signup"),
            {
                "username": "weak_password_user",
                "email": "weak@example.com",
                "password1": "alllowercase123!",
                "password2": "alllowercase123!",
                "account_type": "APPLICANT",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Password must contain at least one uppercase letter.")
        self.assertFalse(
            get_user_model().objects.filter(username="weak_password_user").exists()
        )
