from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import Profile


class SignupAutoLoginTests(TestCase):
    @patch("accounts.views.geocode_office_address", return_value=("33.748997", "-84.387985"))
    def test_applicant_signup_logs_user_in_and_redirects_to_applicant_dashboard(self, _mock_geocode):
        response = self.client.post(
            reverse("accounts.signup"),
            {
                "username": "new_applicant",
                "email": "applicant@example.com",
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
                "account_type": Profile.AccountType.APPLICANT,
                "address_line_1": "123 Peachtree St NE",
                "city": "Atlanta",
                "state": "GA",
                "postal_code": "30303",
                "country": "United States",
            },
        )

        self.assertRedirects(response, reverse("apply:application_status"))
        user = get_user_model().objects.get(username="new_applicant")
        self.assertEqual(self.client.session.get("_auth_user_id"), str(user.pk))

    def test_employer_signup_logs_user_in_and_redirects_to_employer_dashboard(self):
        response = self.client.post(
            reverse("accounts.signup"),
            {
                "username": "new_employer",
                "email": "employer@example.com",
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
                "account_type": Profile.AccountType.EMPLOYER,
                "company_name": "PandaPulse Recruiting",
            },
        )

        self.assertRedirects(response, reverse("jobposts.dashboard"))
        user = get_user_model().objects.get(username="new_employer")
        self.assertEqual(self.client.session.get("_auth_user_id"), str(user.pk))
