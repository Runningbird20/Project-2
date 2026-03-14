from datetime import timedelta

from django.contrib.auth.models import User
from django.core import mail
from django.core.management import call_command
from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import Profile, SavedCandidateSearch


class SavedCandidateAlertTests(TestCase):
    def setUp(self):
        self.employer = User.objects.create_user(
            username="alert_employer",
            password="pass12345",
        )
        Profile.objects.create(
            user=self.employer,
            account_type=Profile.AccountType.EMPLOYER,
        )

    def _login_employer(self):
        self.client.login(username="alert_employer", password="pass12345")

    def _create_applicant(
        self,
        username,
        *,
        skills="",
        location="",
        projects="",
        created_at=None,
    ):
        applicant = User.objects.create_user(username=username, password="pass12345")
        profile = Profile.objects.create(
            user=applicant,
            account_type=Profile.AccountType.APPLICANT,
            visible_to_recruiters=True,
            skills=skills,
            location=location,
            projects=projects,
        )
        if created_at is not None:
            Profile.objects.filter(pk=profile.pk).update(created_at=created_at)
            profile.refresh_from_db()
        return profile

    def _create_saved_search(self, *, created_at=None):
        saved_search = SavedCandidateSearch.objects.create(
            employer=self.employer,
            search_name="Python Engineers in Atlanta",
            filters={
                "skills": "Python",
                "location": "Atlanta",
                "projects": "robotics",
            },
        )
        if created_at is not None:
            SavedCandidateSearch.objects.filter(pk=saved_search.pk).update(created_at=created_at)
            saved_search.refresh_from_db()
        return saved_search

    def test_save_candidate_search_redirects_back_to_origin_page(self):
        self._login_employer()
        return_to = f"{reverse('jobposts.dashboard')}?tab=emp-matches"

        response = self.client.post(
            reverse("accounts.save_search"),
            {
                "search_name": "Backend Candidates",
                "skills": "Python, Django",
                "location": "Atlanta",
                "projects": "API",
                "return_to": return_to,
            },
        )

        self.assertRedirects(
            response,
            return_to,
            fetch_redirect_response=False,
        )
        saved_search = SavedCandidateSearch.objects.get(employer=self.employer)
        self.assertEqual(saved_search.search_name, "Backend Candidates")
        self.assertEqual(saved_search.filters["skills"], "Python, Django")

    def test_dashboard_shows_saved_alerts_with_view_delete_and_new_match_counts(self):
        now = timezone.now()
        self._create_applicant(
            "older_match",
            skills="Python, Django",
            location="Atlanta, GA",
            projects="robotics platform",
            created_at=now - timedelta(days=4),
        )
        saved_search = self._create_saved_search(created_at=now - timedelta(days=2))
        self._create_applicant(
            "fresh_match",
            skills="Python, Flask",
            location="Atlanta, GA",
            projects="robotics lab",
            created_at=now - timedelta(hours=2),
        )

        self._login_employer()
        response = self.client.get(reverse("jobposts.dashboard"), {"tab": "emp-tools"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["saved_searches_count"], 1)
        self.assertEqual(response.context["saved_search_new_alert_count"], 1)
        self.assertEqual(response.context["saved_search_new_match_total"], 1)
        self.assertContains(response, saved_search.search_name)
        self.assertContains(response, "2 current matching candidates")
        self.assertContains(response, "1 new candidate")
        self.assertContains(response, reverse("accounts.delete_search", args=[saved_search.id]))
        self.assertContains(
            response,
            f"{reverse('accounts.candidate_search')}?saved_search={saved_search.id}",
        )
        self.assertNotContains(response, 'id="emp-alerts-btn"')
        self.assertNotContains(response, 'data-bs-target="#emp-alerts"')

    def test_opening_saved_alert_prefills_filters_and_marks_it_viewed(self):
        now = timezone.now()
        saved_search = self._create_saved_search(created_at=now - timedelta(days=2))
        self._create_applicant(
            "new_robotics_match",
            skills="Python, SQL",
            location="Atlanta, GA",
            projects="robotics analytics",
            created_at=now - timedelta(hours=3),
        )

        self._login_employer()
        response = self.client.get(
            reverse("accounts.candidate_search"),
            {"saved_search": saved_search.id},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["template_data"]["filters"]["skills"], "Python")
        self.assertEqual(response.context["template_data"]["filters"]["location"], "Atlanta")
        self.assertEqual(response.context["template_data"]["filters"]["projects"], "robotics")
        self.assertEqual(
            response.context["template_data"]["active_saved_search"].id,
            saved_search.id,
        )
        self.assertContains(response, "new_robotics_match")

        saved_search.refresh_from_db()
        self.assertIsNotNone(saved_search.last_viewed_at)
        self.assertEqual(saved_search.new_matches_queryset().count(), 0)

    def test_candidate_search_preserves_back_target_for_back_button_and_forms(self):
        self._login_employer()
        return_to = f"{reverse('jobposts.dashboard')}?tab=emp-tools"

        response = self.client.get(
            reverse("accounts.candidate_search"),
            {"return_to": return_to},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'href="{return_to}"')
        self.assertContains(response, f'name="return_to" value="{return_to}"', count=2)
        self.assertContains(response, 'data-bs-target="#saveSearchModal"')
        self.assertContains(response, 'id="saveSearchModal"')
        self.assertContains(response, 'id="candidateCreateAlertForm"')
        self.assertContains(response, 'id="candidateAlertSkills"')
        self.assertContains(response, 'id="candidateAlertLocation"')
        self.assertContains(response, 'id="candidateAlertProjects"')
        self.assertContains(response, 'id="candidateAlertModalError"')
        self.assertContains(
            response,
            f'{reverse("accounts.candidate_search")}?return_to=%2Fjobposts%2Fdashboard%2F%3Ftab%3Demp-tools',
        )

    def test_delete_candidate_search_removes_saved_alert(self):
        saved_search = self._create_saved_search()
        self._login_employer()

        response = self.client.post(reverse("accounts.delete_search", args=[saved_search.id]))

        self.assertRedirects(
            response,
            f"{reverse('jobposts.dashboard')}?tab=emp-tools",
            fetch_redirect_response=False,
        )
        self.assertFalse(
            SavedCandidateSearch.objects.filter(pk=saved_search.pk).exists()
        )

    def test_more_tools_section_links_to_alert_management(self):
        saved_search = self._create_saved_search()
        self._login_employer()

        response = self.client.get(reverse("jobposts.dashboard"), {"tab": "emp-tools"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Alerts")
        self.assertContains(response, 'data-bs-target="#dashboardCreateAlertModal"', count=1)
        self.assertContains(response, 'id="dashboardCreateAlertModal"')
        self.assertContains(response, 'id="dashboardCreateAlertForm"')
        self.assertContains(
            response,
            'id="saved-alert-management"',
        )
        self.assertContains(
            response,
            f"{reverse('accounts.candidate_search')}?saved_search={saved_search.id}&return_to=%2Fjobposts%2Fdashboard%2F%3Ftab%3Demp-tools%23saved-alert-management",
        )
        self.assertNotContains(response, 'id="emp-alerts-btn"')

    def test_dashboard_create_alert_modal_saves_alert_back_to_alerts_section(self):
        self._login_employer()
        return_to = f"{reverse('jobposts.dashboard')}?tab=emp-tools#saved-alert-management"

        response = self.client.post(
            reverse("accounts.save_search"),
            {
                "search_name": "Atlanta Robotics Alert",
                "skills": "Python",
                "location": "Atlanta",
                "projects": "robotics",
                "return_to": return_to,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], return_to)
        self.assertTrue(
            SavedCandidateSearch.objects.filter(
                employer=self.employer,
                search_name="Atlanta Robotics Alert",
            ).exists()
        )


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="pandapulse.donotreply@gmail.com",
)
class SavedCandidateAlertEmailTests(TestCase):
    def setUp(self):
        self.employer = User.objects.create_user(
            username="email_alert_employer",
            email="recruiter@example.com",
            password="pass12345",
        )
        Profile.objects.create(
            user=self.employer,
            account_type=Profile.AccountType.EMPLOYER,
        )

    def test_saved_alert_digest_emails_employer_with_alert_name_and_candidate_list(self):
        now = timezone.now()
        saved_search = SavedCandidateSearch.objects.create(
            employer=self.employer,
            search_name="Atlanta Python Robotics",
            filters={
                "skills": "Python",
                "location": "Atlanta",
                "projects": "robotics",
            },
        )
        SavedCandidateSearch.objects.filter(pk=saved_search.pk).update(
            created_at=now - timedelta(days=2)
        )

        matching_user = User.objects.create_user(
            username="candidate_alpha",
            password="pass12345",
        )
        matching_profile = Profile.objects.create(
            user=matching_user,
            account_type=Profile.AccountType.APPLICANT,
            visible_to_recruiters=True,
            skills="Python, SQL",
            location="Atlanta, GA",
            projects="robotics dashboards",
            headline="Data Engineer",
        )
        Profile.objects.filter(pk=matching_profile.pk).update(
            created_at=now - timedelta(hours=4)
        )

        call_command("send_match_digests", force=True)

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, ["recruiter@example.com"])
        self.assertEqual(email.from_email, "pandapulse.donotreply@gmail.com")
        self.assertIn("Atlanta Python Robotics", email.subject)
        self.assertIn('saved alert "Atlanta Python Robotics"', email.body)
        self.assertIn("candidate_alpha", email.body)
        self.assertIn("Data Engineer", email.body)

        saved_search.refresh_from_db()
        self.assertIsNotNone(saved_search.last_notified_at)

    def test_saved_alert_digest_does_not_resend_same_matches(self):
        now = timezone.now()
        saved_search = SavedCandidateSearch.objects.create(
            employer=self.employer,
            search_name="Backend Alert",
            filters={
                "skills": "Python",
                "location": "Atlanta",
                "projects": "API",
            },
        )
        SavedCandidateSearch.objects.filter(pk=saved_search.pk).update(
            created_at=now - timedelta(days=2)
        )

        matching_user = User.objects.create_user(
            username="candidate_beta",
            password="pass12345",
        )
        matching_profile = Profile.objects.create(
            user=matching_user,
            account_type=Profile.AccountType.APPLICANT,
            visible_to_recruiters=True,
            skills="Python, Django",
            location="Atlanta, GA",
            projects="API platform",
        )
        Profile.objects.filter(pk=matching_profile.pk).update(
            created_at=now - timedelta(hours=5)
        )

        call_command("send_match_digests", force=True)
        call_command("send_match_digests", force=True)

        self.assertEqual(len(mail.outbox), 1)
