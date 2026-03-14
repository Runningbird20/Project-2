from unittest.mock import patch
from urllib.parse import quote

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounts.models import Profile
from jobposts.models import JobPost
from .models import OfficeLocation


class MapViewTests(TestCase):
    def test_job_location_page_renders(self):
        user = User.objects.create_user(username='owner', password='pass12345')
        post = JobPost.objects.create(
            owner=user,
            title='Backend Engineer',
            company='Acme Inc',
            location='Atlanta, GA',
            pay_range='$80k-$100k',
            work_setting='onsite',
            description='Build APIs.',
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

        response = self.client.get(reverse('map.job_location', args=[post.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Open in Google Maps')

    def test_job_location_page_uses_return_to_for_back_navigation(self):
        user = User.objects.create_user(username='owner_nav', password='pass12345')
        post = JobPost.objects.create(
            owner=user,
            title='Backend Engineer',
            company='Acme Inc',
            location='Atlanta, GA',
            pay_range='$80k-$100k',
            work_setting='onsite',
            description='Build APIs.',
        )
        return_to = reverse('jobposts.search')

        response = self.client.get(
            f"{reverse('map.job_location', args=[post.id])}?return_to={quote(return_to, safe='')}"
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Back to Open Positions')
        self.assertContains(response, f'href="{return_to}"')

    @patch("map.views.geocode_office_address", return_value=("30.2672", "-97.7431"))
    def test_jobs_map_page_lists_only_jobs_within_radius(self, _mock_geocode):
        owner = User.objects.create_user(username='owner2', password='pass12345')
        applicant = User.objects.create_user(username='applicant_map', password='pass12345')
        Profile.objects.create(
            user=applicant,
            account_type=Profile.AccountType.APPLICANT,
            location='500 W 2nd St, Austin, TX 78701, United States',
        )

        pinned_post = JobPost.objects.create(
            owner=owner,
            title='Frontend Engineer',
            company='Beta Inc',
            location='Austin, TX',
            pay_range='$90k-$120k',
            salary_min=90000,
            salary_max=120000,
            work_setting='onsite',
            description='Build UI.',
        )
        unpinned_post = JobPost.objects.create(
            owner=owner,
            title='No Pin Job',
            company='Beta Inc',
            location='Remote',
            pay_range='$90k-$120k',
            salary_min=90000,
            salary_max=120000,
            work_setting='remote',
            description='No location pin.',
        )
        OfficeLocation.objects.create(
            job_post=pinned_post,
            address_line_1='500 W 2nd St',
            city='Austin',
            state='TX',
            postal_code='78701',
            country='United States',
            latitude='30.266666',
            longitude='-97.733330',
        )

        far_post = JobPost.objects.create(
            owner=owner,
            title='Far Away Engineer',
            company='Gamma Inc',
            location='Seattle, WA',
            pay_range='$120k-$150k',
            salary_min=120000,
            salary_max=150000,
            work_setting='onsite',
            description='Far away role.',
        )
        OfficeLocation.objects.create(
            job_post=far_post,
            address_line_1='1201 3rd Ave',
            city='Seattle',
            state='WA',
            postal_code='98101',
            country='United States',
            latitude='47.606200',
            longitude='-122.332100',
        )

        self.client.login(username='applicant_map', password='pass12345')
        response = self.client.get(reverse('map.jobs_map'), {'radius_miles': '25'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Job Postings Near You')
        self.assertContains(response, pinned_post.title)
        self.assertNotContains(response, unpinned_post.title)
        self.assertNotContains(response, far_post.title)

    def test_jobs_map_prompts_when_applicant_has_no_address(self):
        applicant = User.objects.create_user(username='applicant_no_addr', password='pass12345')
        Profile.objects.create(
            user=applicant,
            account_type=Profile.AccountType.APPLICANT,
            location='',
        )

        self.client.login(username='applicant_no_addr', password='pass12345')
        response = self.client.get(reverse('map.jobs_map'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Add your full address in Profile to view nearby jobs on the map.')
