from django.test import TestCase
from django.core import mail
from django.test.utils import override_settings
from django.contrib.auth.models import User
from django.urls import reverse
from unittest.mock import patch
from decimal import Decimal

from accounts.models import Profile
from map.models import OfficeLocation
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
