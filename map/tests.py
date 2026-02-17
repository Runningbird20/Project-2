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
