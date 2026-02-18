from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

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
        self.assertContains(response, 'Open in OpenStreetMap')

    def test_jobs_map_page_lists_pinned_jobs(self):
        user = User.objects.create_user(username='owner2', password='pass12345')
        pinned_post = JobPost.objects.create(
            owner=user,
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
            owner=user,
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

        response = self.client.get(reverse('map.jobs_map'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Job Postings Near You')
        self.assertContains(response, pinned_post.title)
        self.assertNotContains(response, unpinned_post.title)
