from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Profile


class ProfileNavigationTests(TestCase):
    def test_applicant_profile_returns_to_applicant_dashboard(self):
        user_model = get_user_model()
        user = user_model.objects.create_user(
            username="applicant_profile_nav_user",
            password="test-password-123",
        )
        Profile.objects.update_or_create(
            user=user,
            defaults={"account_type": Profile.AccountType.APPLICANT},
        )

        self.client.login(username="applicant_profile_nav_user", password="test-password-123")
        response = self.client.get(reverse("accounts.profile"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Back to Dashboard")
        self.assertContains(response, reverse("apply:application_status"))
        self.assertNotContains(response, reverse("jobposts.dashboard"))

    def test_employer_profile_returns_to_employer_dashboard(self):
        user_model = get_user_model()
        user = user_model.objects.create_user(
            username="employer_profile_nav_user",
            password="test-password-123",
        )
        Profile.objects.update_or_create(
            user=user,
            defaults={"account_type": Profile.AccountType.EMPLOYER},
        )

        self.client.login(username="employer_profile_nav_user", password="test-password-123")
        response = self.client.get(reverse("accounts.profile"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Back to Dashboard")
        self.assertContains(response, reverse("jobposts.dashboard"))
