from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Profile


class ApplicantClustersMapPermissionTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.superuser = user_model.objects.create_user(
            username="super_only_map",
            password="test-password-123",
            is_superuser=True,
            is_staff=True,
        )
        self.staff_user = user_model.objects.create_user(
            username="staff_no_map",
            password="test-password-123",
            is_staff=True,
        )
        self.employer_user = user_model.objects.create_user(
            username="employer_map_access",
            password="test-password-123",
        )
        Profile.objects.update_or_create(
            user=self.employer_user,
            defaults={"account_type": Profile.AccountType.EMPLOYER},
        )

    def test_staff_user_cannot_access_applicant_clusters_map(self):
        self.client.login(username="staff_no_map", password="test-password-123")
        response = self.client.get(reverse("accounts.applicant_clusters_map"))
        self.assertEqual(response.status_code, 403)

    def test_employer_user_can_access_applicant_clusters_map(self):
        self.client.login(username="employer_map_access", password="test-password-123")
        response = self.client.get(reverse("accounts.applicant_clusters_map"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("accounts.candidate_search"))
        self.assertContains(response, "Back to Find Candidates")
        self.assertNotContains(response, "Back to Manage Users")

    def test_superuser_can_access_applicant_clusters_map(self):
        self.client.login(username="super_only_map", password="test-password-123")
        response = self.client.get(reverse("accounts.applicant_clusters_map"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("accounts.manage_users"))
        self.assertContains(response, "Back to Manage Users")
