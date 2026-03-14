from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from jobposts.models import JobPost

from .models import Profile


class CandidateSearchMatchIndicatorTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.employer_user = user_model.objects.create_user(
            username="employer_match_indicator",
            password="test-password-123",
        )
        Profile.objects.update_or_create(
            user=self.employer_user,
            defaults={"account_type": Profile.AccountType.EMPLOYER},
        )

        self.candidate_user = user_model.objects.create_user(
            username="candidate_match_indicator",
            password="test-password-123",
        )
        Profile.objects.update_or_create(
            user=self.candidate_user,
            defaults={
                "account_type": Profile.AccountType.APPLICANT,
                "skills": "Python",
                "visible_to_recruiters": True,
            },
        )

    def test_find_candidates_hides_matched_job_indicator_below_50_percent(self):
        JobPost.objects.create(
            owner=self.employer_user,
            title="Platform Engineer",
            company="Acme",
            location="Atlanta, GA",
            pay_range="$100k-$130k",
            skills="Python, Django, SQL",
            description="Build APIs",
        )

        self.client.login(username="employer_match_indicator", password="test-password-123")
        response = self.client.get(reverse("accounts.candidate_search"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Matched Platform Engineer")
        candidates = list(response.context["template_data"]["candidates"])
        self.assertEqual(len(candidates), 1)
        self.assertFalse(candidates[0].has_skill_match)

    def test_find_candidates_shows_matched_job_indicator_at_50_percent(self):
        JobPost.objects.create(
            owner=self.employer_user,
            title="Platform Engineer",
            company="Acme",
            location="Atlanta, GA",
            pay_range="$100k-$130k",
            skills="Python, Django",
            description="Build APIs",
        )

        self.client.login(username="employer_match_indicator", password="test-password-123")
        response = self.client.get(reverse("accounts.candidate_search"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Matched Platform Engineer")
        candidates = list(response.context["template_data"]["candidates"])
        self.assertEqual(len(candidates), 1)
        self.assertTrue(candidates[0].has_skill_match)
        self.assertEqual(candidates[0].matched_job_percent, 50)
