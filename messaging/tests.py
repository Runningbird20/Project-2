from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import Profile

from .models import Message


class MessagingNavigationTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.employer = user_model.objects.create_user(
            username="employer_nav",
            password="test-password-123",
        )
        self.applicant = user_model.objects.create_user(
            username="applicant_nav",
            password="test-password-123",
        )

        Profile.objects.update_or_create(
            user=self.employer,
            defaults={"account_type": Profile.AccountType.EMPLOYER},
        )
        Profile.objects.update_or_create(
            user=self.applicant,
            defaults={
                "account_type": Profile.AccountType.APPLICANT,
                "visible_to_recruiters": True,
            },
        )

        Message.objects.create(
            sender=self.employer,
            recipient=self.applicant,
            body="Hello there",
        )

    def test_employer_chat_detail_links_back_to_candidate_profile(self):
        self.client.login(username="employer_nav", password="test-password-123")

        response = self.client.get(
            reverse("messaging:chat_detail", args=[self.applicant.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            reverse("accounts.public_profile", args=[self.applicant.username]),
        )
        self.assertContains(response, "Return to Profile")

    def test_employer_inbox_uses_employer_dashboard_navigation(self):
        self.client.login(username="employer_nav", password="test-password-123")

        response = self.client.get(reverse("messaging:inbox"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("jobposts.dashboard"))

    def test_applicant_chat_detail_uses_applicant_dashboard_navigation(self):
        self.client.login(username="applicant_nav", password="test-password-123")

        response = self.client.get(
            reverse("messaging:chat_detail", args=[self.employer.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("apply:application_status"))
        self.assertNotContains(response, "Return to Profile")
