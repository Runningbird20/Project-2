from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Profile


class CandidateSearchMapButtonTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.employer_user = user_model.objects.create_user(
            username="employer_find_candidates",
            password="test-password-123",
        )
        Profile.objects.update_or_create(
            user=self.employer_user,
            defaults={"account_type": Profile.AccountType.EMPLOYER},
        )

    def test_find_candidates_page_shows_clusters_map_button(self):
        self.client.login(username="employer_find_candidates", password="test-password-123")
        response = self.client.get(reverse("accounts.candidate_search"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("accounts.applicant_clusters_map"))
        self.assertContains(response, "View Map")
