from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounts.models import Profile, SkillOption


class SkillCatalogTests(TestCase):
    def setUp(self):
        self.applicant_user = User.objects.create_user(username="applicant", password="pass12345")
        Profile.objects.create(
            user=self.applicant_user,
            account_type=Profile.AccountType.APPLICANT,
        )
        self.employer_user = User.objects.create_user(username="employer", password="pass12345")
        Profile.objects.create(
            user=self.employer_user,
            account_type=Profile.AccountType.EMPLOYER,
        )

    def test_custom_skill_saved_on_profile_edit_shows_in_other_dropdowns(self):
        self.client.login(username="applicant", password="pass12345")
        response = self.client.post(
            reverse("accounts.profile_edit"),
            {
                "account_type": Profile.AccountType.APPLICANT,
                "headline": "",
                "skills": "Graph Databases",
                "projects": "",
                "education": "",
                "work_experience": "",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(SkillOption.objects.filter(normalized_name="graph databases").exists())

        signup_response = self.client.get(reverse("accounts.signup"))
        self.assertContains(signup_response, '<option value="Graph Databases">Graph Databases</option>', html=True)

        self.client.logout()
        self.client.login(username="employer", password="pass12345")
        create_response = self.client.get(reverse("jobposts.create"))
        self.assertContains(create_response, '<option value="Graph Databases">Graph Databases</option>', html=True)
