from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from map.services import OfficeLocationGeocodingError

from accounts.models import Profile


class ApplicantSignupAddressTests(TestCase):
    def test_applicant_signup_requires_full_address(self):
        response = self.client.post(
            reverse("accounts.signup"),
            {
                "username": "applicant_no_address",
                "email": "noaddress@example.com",
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
                "account_type": Profile.AccountType.APPLICANT,
                "address_line_1": "",
                "city": "",
                "state": "",
                "postal_code": "",
                "country": "United States",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Address is required for applicants.")
        self.assertFalse(get_user_model().objects.filter(username="applicant_no_address").exists())

    @patch("accounts.views.geocode_office_address", side_effect=OfficeLocationGeocodingError("Bad address"))
    def test_applicant_signup_rejects_unpinnable_address(self, _mock_geocode):
        response = self.client.post(
            reverse("accounts.signup"),
            {
                "username": "applicant_bad_address",
                "email": "badaddress@example.com",
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
                "account_type": Profile.AccountType.APPLICANT,
                "address_line_1": "Not a real address",
                "city": "Nowhere",
                "state": "GA",
                "postal_code": "30303",
                "country": "United States",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Bad address")
        self.assertFalse(get_user_model().objects.filter(username="applicant_bad_address").exists())

    @patch("accounts.views.geocode_office_address", return_value=("33.748997", "-84.387985"))
    def test_applicant_signup_accepts_full_address_when_pinnable(self, _mock_geocode):
        response = self.client.post(
            reverse("accounts.signup"),
            {
                "username": "applicant_good_address",
                "email": "goodaddress@example.com",
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

        self.assertEqual(response.status_code, 302)
        user = get_user_model().objects.get(username="applicant_good_address")
        self.assertEqual(user.profile.location, "123 Peachtree St NE, Atlanta, GA 30303, United States")
        self.assertEqual(user.profile.city, "Atlanta")
        self.assertEqual(user.profile.state, "GA")
