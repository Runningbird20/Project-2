from django.test import TestCase
from django.core import mail
from django.test.utils import override_settings
from django.contrib.auth.models import User
from django.urls import reverse
from unittest.mock import patch
from decimal import Decimal

from accounts.models import Profile
from map.models import OfficeLocation
from apply.models import Application
from .models import ApplicantJobMatch, JobPost


class JobPostViewTests(TestCase):
    def setUp(self):
        self.employer_user = User.objects.create_user(username='employer', password='pass12345')
        Profile.objects.create(
            user=self.employer_user,
            account_type=Profile.AccountType.EMPLOYER,
        )
        self.other_employer_user = User.objects.create_user(username='employer2', password='pass12345')
        Profile.objects.create(
            user=self.other_employer_user,
            account_type=Profile.AccountType.EMPLOYER,
        )

        self.applicant_user = User.objects.create_user(username='applicant', password='pass12345')
        Profile.objects.create(
            user=self.applicant_user,
            account_type=Profile.AccountType.APPLICANT,
        )

    def test_create_page_requires_login(self):
        response = self.client.get(reverse('jobposts.create'))
        self.assertEqual(response.status_code, 302)

    def test_applicant_cannot_access_create_page(self):
        self.client.login(username='applicant', password='pass12345')
        response = self.client.get(reverse('jobposts.create'))
        self.assertEqual(response.status_code, 403)

    def test_employer_can_access_create_page(self):
        self.client.login(username='employer', password='pass12345')
        response = self.client.get(reverse('jobposts.create'))
        self.assertEqual(response.status_code, 200)

    def test_employer_post_creates_jobpost(self):
        self.client.login(username='employer', password='pass12345')
        payload = {
            'title': 'Backend Engineer',
            'company': 'Acme Inc',
            'company_size': 'mid_size',
            'location': 'Remote',
            'salary_min': 70000,
            'salary_max': 90000,
            'work_setting': 'remote',
            'description': 'Build APIs and services.',
        }

        response = self.client.post(reverse('jobposts.create'), payload)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(JobPost.objects.count(), 1)

    def test_employer_post_does_not_require_address_when_country_prefilled(self):
        self.client.login(username='employer', password='pass12345')
        payload = {
            'title': 'Backend Engineer',
            'company': 'Acme Inc',
            'company_size': 'mid_size',
            'location': 'Remote',
            'salary_min': 70000,
            'salary_max': 90000,
            'work_setting': 'remote',
            'description': 'Build APIs and services.',
            'map-address_line_1': '',
            'map-address_line_2': '',
            'map-city': '',
            'map-state': '',
            'map-postal_code': '',
            'map-country': 'United States',
        }

        response = self.client.post(reverse('jobposts.create'), payload)

        self.assertEqual(response.status_code, 302)
        post = JobPost.objects.get()
        self.assertFalse(OfficeLocation.objects.filter(job_post=post).exists())

    def test_employer_can_pin_office_location_on_create(self):
        self.client.login(username='employer', password='pass12345')
        payload = {
            'title': 'Backend Engineer',
            'company': 'Acme Inc',
            'company_size': 'mid_size',
            'location': 'Atlanta, GA',
            'salary_min': 70000,
            'salary_max': 90000,
            'work_setting': 'onsite',
            'description': 'Build APIs and services.',
            'map-address_line_1': '75 5th St NW',
            'map-city': 'Atlanta',
            'map-state': 'GA',
            'map-postal_code': '30308',
            'map-country': 'United States',
        }

        with patch('jobposts.views.geocode_office_address', return_value=('33.776500', '-84.398300')):
            response = self.client.post(reverse('jobposts.create'), payload)

        self.assertEqual(response.status_code, 302)
        post = JobPost.objects.get()
        self.assertTrue(OfficeLocation.objects.filter(job_post=post).exists())

    def test_applicant_post_does_not_create_jobpost(self):
        self.client.login(username='applicant', password='pass12345')
        payload = {
            'title': 'Backend Engineer',
            'company': 'Acme Inc',
            'company_size': 'mid_size',
            'location': 'Remote',
            'salary_min': 70000,
            'salary_max': 90000,
            'work_setting': 'remote',
            'description': 'Build APIs and services.',
        }

        response = self.client.post(reverse('jobposts.create'), payload)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(JobPost.objects.count(), 0)

    def test_owner_employer_can_access_edit_page(self):
        post = JobPost.objects.create(
            owner=self.employer_user,
            title='Backend Engineer',
            company='Acme Inc',
            location='Remote',
            pay_range='$70k-$90k',
            work_setting='remote',
            description='Build APIs and services.',
        )
        self.client.login(username='employer', password='pass12345')
        response = self.client.get(reverse('jobposts.edit', args=[post.id]))
        self.assertEqual(response.status_code, 200)

    def test_applicant_cannot_access_edit_page(self):
        post = JobPost.objects.create(
            owner=self.employer_user,
            title='Backend Engineer',
            company='Acme Inc',
            location='Remote',
            pay_range='$70k-$90k',
            work_setting='remote',
            description='Build APIs and services.',
        )
        self.client.login(username='applicant', password='pass12345')
        response = self.client.get(reverse('jobposts.edit', args=[post.id]))
        self.assertEqual(response.status_code, 403)

    def test_non_owner_employer_cannot_access_edit_page(self):
        post = JobPost.objects.create(
            owner=self.employer_user,
            title='Backend Engineer',
            company='Acme Inc',
            location='Remote',
            pay_range='$70k-$90k',
            work_setting='remote',
            description='Build APIs and services.',
        )
        self.client.login(username='employer2', password='pass12345')
        response = self.client.get(reverse('jobposts.edit', args=[post.id]))
        self.assertEqual(response.status_code, 404)

    def test_non_owner_employer_cannot_edit_post(self):
        post = JobPost.objects.create(
            owner=self.employer_user,
            title='Backend Engineer',
            company='Acme Inc',
            location='Remote',
            pay_range='$70k-$90k',
            work_setting='remote',
            description='Build APIs and services.',
        )
        payload = {
            'title': 'Updated Title',
            'company': 'Acme Inc',
            'company_size': 'mid_size',
            'location': 'Remote',
            'salary_min': 70000,
            'salary_max': 90000,
            'work_setting': 'remote',
            'description': 'Build APIs and services.',
        }
        self.client.login(username='employer2', password='pass12345')
        response = self.client.post(reverse('jobposts.edit', args=[post.id]), payload)
        post.refresh_from_db()

        self.assertEqual(response.status_code, 404)
        self.assertEqual(post.title, 'Backend Engineer')

    def test_owner_can_clear_office_location_on_edit(self):
        post = JobPost.objects.create(
            owner=self.employer_user,
            title='Backend Engineer',
            company='Acme Inc',
            location='Atlanta, GA',
            pay_range='$70k-$90k',
            work_setting='onsite',
            description='Build APIs and services.',
        )
        OfficeLocation.objects.create(
            job_post=post,
            address_line_1='75 5th St NW',
            city='Atlanta',
            state='GA',
            postal_code='30308',
            country='United States',
            latitude='33.776500',
            longitude='-84.398300',
        )
        payload = {
            'title': 'Backend Engineer',
            'company': 'Acme Inc',
            'company_size': 'mid_size',
            'location': 'Atlanta, GA',
            'salary_min': 70000,
            'salary_max': 90000,
            'work_setting': 'onsite',
            'description': 'Build APIs and services.',
            'map-address_line_1': '',
            'map-address_line_2': '',
            'map-city': '',
            'map-state': '',
            'map-postal_code': '',
            'map-country': '',
        }
        self.client.login(username='employer', password='pass12345')
        response = self.client.post(reverse('jobposts.edit', args=[post.id]), payload)

        self.assertEqual(response.status_code, 302)
        self.assertFalse(OfficeLocation.objects.filter(job_post=post).exists())

    def test_applicant_can_filter_jobs_by_home_radius(self):
        nearby_post = JobPost.objects.create(
            owner=self.employer_user,
            title='Nearby Onsite Role',
            company='Acme Inc',
            location='Atlanta, GA',
            pay_range='$80k-$100k',
            work_setting='onsite',
            description='Near office',
        )
        far_post = JobPost.objects.create(
            owner=self.employer_user,
            title='Far Onsite Role',
            company='Acme Inc',
            location='Savannah, GA',
            pay_range='$80k-$100k',
            work_setting='onsite',
            description='Far office',
        )
        remote_post = JobPost.objects.create(
            owner=self.employer_user,
            title='Remote Role',
            company='Acme Inc',
            location='USA',
            pay_range='$80k-$100k',
            work_setting='remote',
            description='Work from anywhere',
        )

        OfficeLocation.objects.create(
            job_post=nearby_post,
            address_line_1='75 5th St NW',
            city='Atlanta',
            state='GA',
            postal_code='30308',
            country='United States',
            latitude=Decimal('33.776500'),
            longitude=Decimal('-84.398300'),
        )
        OfficeLocation.objects.create(
            job_post=far_post,
            address_line_1='1 W Bay St',
            city='Savannah',
            state='GA',
            postal_code='31401',
            country='United States',
            latitude=Decimal('32.080900'),
            longitude=Decimal('-81.091200'),
        )

        profile = Profile.objects.get(user=self.applicant_user)
        profile.location = '123 Peachtree St NE, Atlanta, GA 30303'
        profile.save(update_fields=['location'])

        self.client.login(username='applicant', password='pass12345')
        with patch('jobposts.views.geocode_office_address', return_value=('33.776500', '-84.398300')):
            response = self.client.get(
                reverse('jobposts.search'),
                {'use_home_radius': 'true', 'radius_miles': '15'},
            )

        self.assertEqual(response.status_code, 200)
        posts = list(response.context['template_data']['posts'])
        self.assertIn(nearby_post, posts)
        self.assertIn(remote_post, posts)
        self.assertNotIn(far_post, posts)

    def test_radius_filter_shows_warning_without_home_address(self):
        self.client.login(username='applicant', password='pass12345')
        response = self.client.get(
            reverse('jobposts.search'),
            {'use_home_radius': 'true', 'radius_miles': '25'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            'Add your home address in your profile to use radius filtering.',
        )

    def test_home_radius_can_be_unchecked_after_being_enabled(self):
        nearby_post = JobPost.objects.create(
            owner=self.employer_user,
            title='Nearby Onsite Role',
            company='Acme Inc',
            location='Atlanta, GA',
            pay_range='$80k-$100k',
            work_setting='onsite',
            description='Near office',
        )
        far_post = JobPost.objects.create(
            owner=self.employer_user,
            title='Far Onsite Role',
            company='Acme Inc',
            location='Savannah, GA',
            pay_range='$80k-$100k',
            work_setting='onsite',
            description='Far office',
        )
        OfficeLocation.objects.create(
            job_post=nearby_post,
            address_line_1='75 5th St NW',
            city='Atlanta',
            state='GA',
            postal_code='30308',
            country='United States',
            latitude=Decimal('33.776500'),
            longitude=Decimal('-84.398300'),
        )
        OfficeLocation.objects.create(
            job_post=far_post,
            address_line_1='1 W Bay St',
            city='Savannah',
            state='GA',
            postal_code='31401',
            country='United States',
            latitude=Decimal('32.080900'),
            longitude=Decimal('-81.091200'),
        )

        profile = Profile.objects.get(user=self.applicant_user)
        profile.location = '123 Peachtree St NE, Atlanta, GA 30303'
        profile.save(update_fields=['location'])

        self.client.login(username='applicant', password='pass12345')
        with patch('jobposts.views.geocode_office_address', return_value=('33.776500', '-84.398300')):
            first_response = self.client.get(
                reverse('jobposts.search'),
                {'use_home_radius': 'true', 'radius_miles': '15'},
            )
            second_response = self.client.get(
                reverse('jobposts.search'),
                {'use_home_radius': 'false', 'radius_miles': '15'},
            )

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 200)
        filtered_posts = list(first_response.context['template_data']['posts'])
        all_posts = list(second_response.context['template_data']['posts'])
        self.assertIn(nearby_post, filtered_posts)
        self.assertNotIn(far_post, filtered_posts)
        self.assertIn(nearby_post, all_posts)
        self.assertIn(far_post, all_posts)

    def test_search_filters_by_company_size(self):
        self.client.login(username='applicant', password='pass12345')
        matching = JobPost.objects.create(
            owner=self.employer_user,
            title='Mid-size Role',
            company='Acme Inc',
            location='Atlanta, GA',
            pay_range='$80k-$100k',
            company_size='mid_size',
            work_setting='onsite',
            description='Match me',
        )
        non_matching = JobPost.objects.create(
            owner=self.employer_user,
            title='Startup Role',
            company='Acme Inc',
            location='Atlanta, GA',
            pay_range='$80k-$100k',
            company_size='startup',
            work_setting='onsite',
            description='Do not match',
        )

        response = self.client.get(reverse('jobposts.search'), {'company_size': 'mid_size'})
        self.assertEqual(response.status_code, 200)
        posts = list(response.context['template_data']['posts'])
        self.assertIn(matching, posts)
        self.assertNotIn(non_matching, posts)

    def test_search_matches_full_state_name_to_abbreviated_location(self):
        florida_job = JobPost.objects.create(
            owner=self.employer_user,
            title='Miami Engineer',
            company='Sunshine Tech',
            location='Miami, FL',
            pay_range='$80k-$100k',
            work_setting='hybrid',
            description='Florida role',
        )
        other_job = JobPost.objects.create(
            owner=self.employer_user,
            title='Atlanta Engineer',
            company='Peachtree Tech',
            location='Atlanta, GA',
            pay_range='$80k-$100k',
            work_setting='hybrid',
            description='Georgia role',
        )

        response = self.client.get(reverse('jobposts.search'), {'location': 'Florida'})

        self.assertEqual(response.status_code, 200)
        posts = list(response.context['template_data']['posts'])
        self.assertIn(florida_job, posts)
        self.assertNotIn(other_job, posts)

    def test_search_matches_full_state_name_against_structured_office_location(self):
        florida_job = JobPost.objects.create(
            owner=self.employer_user,
            title='Miami Engineer',
            company='Sunshine Tech',
            location='Miami Office',
            pay_range='$80k-$100k',
            work_setting='onsite',
            description='Florida office role',
        )
        OfficeLocation.objects.create(
            job_post=florida_job,
            address_line_1='200 Biscayne Blvd',
            city='Miami',
            state='FL',
            postal_code='33131',
            country='United States',
            latitude=Decimal('25.761700'),
            longitude=Decimal('-80.191800'),
        )
        other_job = JobPost.objects.create(
            owner=self.employer_user,
            title='Austin Engineer',
            company='Lone Star Tech',
            location='Austin Office',
            pay_range='$80k-$100k',
            work_setting='onsite',
            description='Texas office role',
        )
        OfficeLocation.objects.create(
            job_post=other_job,
            address_line_1='500 Congress Ave',
            city='Austin',
            state='TX',
            postal_code='78701',
            country='United States',
            latitude=Decimal('30.267200'),
            longitude=Decimal('-97.743100'),
        )

        response = self.client.get(reverse('jobposts.search'), {'location': 'Florida'})

        self.assertEqual(response.status_code, 200)
        posts = list(response.context['template_data']['posts'])
        self.assertIn(florida_job, posts)
        self.assertNotIn(other_job, posts)

    def test_search_filters_only_visa_sponsored_jobs(self):
        self.client.login(username='applicant', password='pass12345')
        visa_job = JobPost.objects.create(
            owner=self.employer_user,
            title='Visa Role',
            company='Acme Inc',
            location='Atlanta, GA',
            pay_range='$80k-$100k',
            visa_sponsorship=True,
            work_setting='onsite',
            description='Visa sponsored',
        )
        non_visa_job = JobPost.objects.create(
            owner=self.employer_user,
            title='No Visa Role',
            company='Acme Inc',
            location='Atlanta, GA',
            pay_range='$80k-$100k',
            visa_sponsorship=False,
            work_setting='onsite',
            description='No sponsorship',
        )

        response = self.client.get(reverse('jobposts.search'), {'visa_sponsorship': 'true'})
        self.assertEqual(response.status_code, 200)
        posts = list(response.context['template_data']['posts'])
        self.assertIn(visa_job, posts)
        self.assertNotIn(non_visa_job, posts)

    def test_search_shows_resume_match_percentage_for_applicant(self):
        profile = Profile.objects.get(user=self.applicant_user)
        profile.skills = "Python, Django"
        profile.save(update_fields=["skills"])

        JobPost.objects.create(
            owner=self.employer_user,
            title='Backend Engineer',
            company='Acme Inc',
            location='Atlanta, GA',
            pay_range='$80k-$100k',
            skills='Python, Django, SQL',
            work_setting='hybrid',
            description='Build APIs',
        )

        self.client.login(username='applicant', password='pass12345')
        response = self.client.get(reverse('jobposts.search'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Resume Match 67%')

    def test_search_page_uses_profile_resume_for_application_flow_only(self):
        JobPost.objects.create(
            owner=self.employer_user,
            title='Backend Engineer',
            company='Acme Inc',
            location='Atlanta, GA',
            pay_range='$80k-$100k',
            skills='Python, Django',
            work_setting='hybrid',
            description='Build APIs',
        )
        self.client.login(username='applicant', password='pass12345')
        response = self.client.get(reverse('jobposts.search'))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Upload Resume Skills')
        self.assertContains(response, 'Use my Profile Resume')

    def test_search_uses_parsed_resume_skills_for_matching_when_profile_skills_are_blank(self):
        profile = Profile.objects.get(user=self.applicant_user)
        profile.skills = ''
        profile.parsed_resume_skills = 'python, django'
        profile.save(update_fields=['skills', 'parsed_resume_skills'])

        job = JobPost.objects.create(
            owner=self.employer_user,
            title='Backend Engineer',
            company='Acme Inc',
            location='Atlanta, GA',
            pay_range='$80k-$100k',
            skills='Python, Django, SQL',
            work_setting='hybrid',
            description='Build APIs',
        )

        self.client.login(username='applicant', password='pass12345')
        response = self.client.get(reverse('jobposts.search'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Resume Match 67%')
        self.assertTrue(
            ApplicantJobMatch.objects.filter(applicant=self.applicant_user, job=job).exists()
        )

    def test_dashboard_prefills_interview_form_from_query_param(self):
        job = JobPost.objects.create(
            owner=self.employer_user,
            title='Backend Engineer',
            company='Acme Inc',
            location='Atlanta, GA',
            pay_range='$80k-$100k',
            work_setting='hybrid',
            description='Build APIs',
        )
        application = Application.objects.create(
            user=self.applicant_user,
            job=job,
            resume_type='profile',
        )

        self.client.login(username='employer', password='pass12345')
        response = self.client.get(
            reverse('jobposts.dashboard'),
            {'tab': 'emp-interviews', 'interview_application': application.id},
        )

        self.assertEqual(response.status_code, 200)
        form = response.context['interview_proposal_form']
        self.assertEqual(form.fields['application'].initial, application.id)

    def test_job_detail_shows_resume_match_percentage_for_applicant(self):
        profile = Profile.objects.get(user=self.applicant_user)
        profile.skills = "Python, Django"
        profile.save(update_fields=["skills"])

        job = JobPost.objects.create(
            owner=self.employer_user,
            title='Backend Engineer',
            company='Acme Inc',
            location='Atlanta, GA',
            pay_range='$80k-$100k',
            skills='Python, Django, SQL',
            work_setting='hybrid',
            description='Build APIs',
        )

        self.client.login(username='applicant', password='pass12345')
        response = self.client.get(reverse('jobposts.detail', args=[job.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Resume Match 67%')


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class ApplicantMatchingTests(TestCase):
    def setUp(self):
        self.employer = User.objects.create_user(
            username="employer_match",
            email="employer_match@example.com",
            password="pass12345",
        )
        Profile.objects.create(
            user=self.employer,
            account_type=Profile.AccountType.EMPLOYER,
        )
        self.applicant = User.objects.create_user(
            username="applicant_match",
            password="pass12345",
        )
        Profile.objects.create(
            user=self.applicant,
            account_type=Profile.AccountType.APPLICANT,
            skills="Python, Django, AWS",
        )
        self.job = JobPost.objects.create(
            owner=self.employer,
            title="Backend Engineer",
            company="Acme",
            location="Atlanta, GA",
            pay_range="$100k-$130k",
            skills="Python, Django, SQL",
            work_setting="hybrid",
            description="Build APIs",
        )

    def test_dashboard_creates_skill_match_and_notifies_employer(self):
        self.client.login(username="applicant_match", password="pass12345")
        response = self.client.get(reverse("jobposts.dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertIn(self.job, response.context["recommendations"])
        match = ApplicantJobMatch.objects.get(applicant=self.applicant, job=self.job)
        self.assertGreaterEqual(match.score, 1)
        self.assertIn("python", match.matched_skills)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.employer.email, mail.outbox[0].to)

    def test_dashboard_does_not_send_duplicate_match_email(self):
        self.client.login(username="applicant_match", password="pass12345")
        self.client.get(reverse("jobposts.dashboard"))
        self.client.get(reverse("jobposts.dashboard"))
        self.assertEqual(len(mail.outbox), 1)

    def test_dashboard_ignores_matches_at_or_below_fifty_percent(self):
        low_overlap_job = JobPost.objects.create(
            owner=self.employer,
            title="Platform Engineer",
            company="Acme",
            location="Atlanta, GA",
            pay_range="$100k-$130k",
            skills="Python, Java, Go, Kubernetes",
            work_setting="hybrid",
            description="Build platform tooling",
        )

        self.client.login(username="applicant_match", password="pass12345")
        response = self.client.get(reverse("jobposts.dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertNotIn(low_overlap_job, response.context["recommendations"])
        self.assertFalse(
            ApplicantJobMatch.objects.filter(
                applicant=self.applicant,
                job=low_overlap_job,
            ).exists()
        )
