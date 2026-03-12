from decimal import Decimal
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apply.models import Application
from jobposts.models import JobPost
from map.models import OfficeLocation

from .models import Profile


class CompanyProfileAndSearchTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.employer = user_model.objects.create_user(username="recruiter1", password="pass12345")
        self.applicant = user_model.objects.create_user(username="applicant1", password="pass12345")

        self.employer_profile, _ = Profile.objects.get_or_create(user=self.employer)
        self.employer_profile.account_type = Profile.AccountType.EMPLOYER
        self.employer_profile.company_name = "Acme Labs"
        self.employer_profile.company_description = "Builds AI tools."
        self.employer_profile.company_culture = "Remote-first and learning-focused."
        self.employer_profile.company_perks = "401k match\nHome office stipend"
        self.employer_profile.save()

        self.applicant_profile, _ = Profile.objects.get_or_create(user=self.applicant)
        self.applicant_profile.account_type = Profile.AccountType.APPLICANT
        self.applicant_profile.save()

        self.post = JobPost.objects.create(
            owner=self.employer,
            title="Backend Engineer",
            company="Acme Labs",
            location="Atlanta, GA",
            pay_range="$100k-$130k",
            work_setting="hybrid",
            description="Build APIs",
        )
        OfficeLocation.objects.create(
            job_post=self.post,
            address_line_1="75 5th St NW",
            city="Atlanta",
            state="GA",
            postal_code="30308",
            country="United States",
            latitude=Decimal("33.776500"),
            longitude=Decimal("-84.398300"),
        )

    def test_company_search_available_to_applicants(self):
        self.client.login(username="applicant1", password="pass12345")
        response = self.client.get(reverse("accounts.company_search"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Acme Labs")

    def test_company_search_forbidden_for_employers(self):
        self.client.login(username="recruiter1", password="pass12345")
        response = self.client.get(reverse("accounts.company_search"))
        self.assertEqual(response.status_code, 403)

    def test_company_search_filters_by_culture_and_location(self):
        self.client.login(username="applicant1", password="pass12345")

        response = self.client.get(
            reverse("accounts.company_search"),
            {"culture": "learning-focused", "location": "Atlanta"},
        )
        self.assertEqual(response.status_code, 200)
        companies = list(response.context["template_data"]["companies"])
        self.assertEqual(len(companies), 1)
        self.assertEqual(companies[0].company_name, "Acme Labs")

    def test_applicant_can_view_company_profile_with_map_gallery(self):
        self.client.login(username="applicant1", password="pass12345")
        response = self.client.get(
            reverse("accounts.company_profile", kwargs={"username": self.employer.username})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Office Map Gallery")
        self.assertContains(response, "Remote-first and learning-focused.")
        self.assertContains(response, "Home office stipend")

    def test_only_employer_can_edit_company_profile(self):
        self.client.login(username="applicant1", password="pass12345")
        forbidden = self.client.get(reverse("accounts.company_profile_edit"))
        self.assertEqual(forbidden.status_code, 403)

        self.client.login(username="recruiter1", password="pass12345")
        response = self.client.post(
            reverse("accounts.company_profile_edit"),
            {
                "company_name": "Acme Labs Updated",
                "company_website": "",
                "company_description": "Updated description",
                "company_culture": "Collaborative",
                "company_perks": "Medical",
                "address_line_1": "",
                "address_line_2": "",
                "city": "",
                "state": "",
                "postal_code": "",
                "country": "United States",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.employer_profile.refresh_from_db()
        self.assertEqual(self.employer_profile.company_name, "Acme Labs Updated")

    def test_company_profile_edit_shows_required_marker_and_rejects_blank_company_name(self):
        self.client.login(username="recruiter1", password="pass12345")

        get_response = self.client.get(reverse("accounts.company_profile_edit"))
        self.assertEqual(get_response.status_code, 200)
        self.assertContains(get_response, "Fields marked with")
        self.assertContains(get_response, "Company Name")
        self.assertContains(get_response, "required-indicator")

        post_response = self.client.post(
            reverse("accounts.company_profile_edit"),
            {
                "company_name": "",
                "company_website": "",
                "company_description": "Builds AI tools.",
                "company_culture": "Remote-first and learning-focused.",
                "company_perks": "401k match\nHome office stipend",
                "address_line_1": "",
                "address_line_2": "",
                "city": "",
                "state": "",
                "postal_code": "",
                "country": "United States",
            },
        )
        self.assertEqual(post_response.status_code, 200)
        self.assertContains(post_response, "Company name is required for employers.")

    def test_employer_can_set_company_hq_in_company_profile(self):
        self.client.login(username="recruiter1", password="pass12345")
        response = self.client.post(
            reverse("accounts.company_profile_edit"),
            {
                "company_name": "Acme Labs",
                "company_website": "",
                "company_description": "Builds AI tools.",
                "company_culture": "Remote-first and learning-focused.",
                "company_perks": "401k match\nHome office stipend",
                "address_line_1": "75 5th St NW",
                "address_line_2": "",
                "city": "Atlanta",
                "state": "GA",
                "postal_code": "30308",
                "country": "United States",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.employer_profile.refresh_from_db()
        self.assertEqual(self.employer_profile.city, "Atlanta")
        self.assertEqual(self.employer_profile.state, "GA")

    def _create_responded_application(self, hours_to_respond, username_suffix):
        user_model = get_user_model()
        applicant = user_model.objects.create_user(
            username=f"sla_applicant_{username_suffix}",
            password="pass12345",
        )
        applicant_profile, _ = Profile.objects.get_or_create(user=applicant)
        applicant_profile.account_type = Profile.AccountType.APPLICANT
        applicant_profile.save()

        application = Application.objects.create(
            user=applicant,
            job=self.post,
            resume_type="profile",
            status="review",
        )
        responded_at = timezone.now() - timedelta(hours=1)
        applied_at = responded_at - timedelta(hours=hours_to_respond)
        Application.objects.filter(id=application.id).update(
            applied_at=applied_at,
            responded_at=responded_at,
        )

    def test_company_profile_shows_green_response_sla_badge_under_49_hours(self):
        self._create_responded_application(hours_to_respond=48, username_suffix="green")
        self.client.login(username="applicant1", password="pass12345")
        response = self.client.get(
            reverse("accounts.company_profile", kwargs={"username": self.employer.username})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Responds in ~2 days")
        self.assertContains(response, "sla-badge is-green")

    def test_company_search_shows_yellow_response_sla_badge_between_49_hours_and_week(self):
        self._create_responded_application(hours_to_respond=72, username_suffix="yellow")
        self.client.login(username="applicant1", password="pass12345")
        response = self.client.get(reverse("accounts.company_search"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Responds in ~3 days")
        self.assertContains(response, "sla-badge is-yellow")

    def test_company_search_shows_red_response_sla_badge_over_one_week(self):
        self._create_responded_application(hours_to_respond=240, username_suffix="red")
        self.client.login(username="applicant1", password="pass12345")
        response = self.client.get(reverse("accounts.company_search"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Responds in ~10 days")
        self.assertContains(response, "sla-badge is-red")
