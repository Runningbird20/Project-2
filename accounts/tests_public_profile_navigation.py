from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import Profile


class PublicProfileNavigationTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.applicant = user_model.objects.create_user(
            username="applicant_preview",
            password="StrongPass123!",
            email="applicant_preview@example.com",
        )
        Profile.objects.create(
            user=self.applicant,
            account_type=Profile.AccountType.APPLICANT,
            visible_to_recruiters=True,
        )

        self.employer = user_model.objects.create_user(
            username="employer_viewer",
            password="StrongPass123!",
            email="employer_viewer@example.com",
        )
        Profile.objects.create(
            user=self.employer,
            account_type=Profile.AccountType.EMPLOYER,
            company_name="PandaPulse Recruiting",
        )

    def test_owner_public_profile_returns_to_applicant_dashboard(self):
        self.client.login(username="applicant_preview", password="StrongPass123!")

        response = self.client.get(
            reverse("accounts.public_profile", kwargs={"username": self.applicant.username})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Back to Dashboard")
        self.assertContains(response, reverse("apply:application_status"))
        self.assertNotContains(response, reverse("accounts.candidate_search"))
        self.assertContains(response, "applicant_preview@example.com", count=1)

    def test_recruiter_public_profile_keeps_back_to_search_button(self):
        self.client.login(username="employer_viewer", password="StrongPass123!")

        response = self.client.get(
            reverse("accounts.public_profile", kwargs={"username": self.applicant.username})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Back to Find Candidates")
        self.assertContains(response, reverse("accounts.candidate_search"))
        self.assertNotContains(response, reverse("apply:application_status"))
