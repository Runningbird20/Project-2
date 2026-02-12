from django.test import TestCase
from django.urls import reverse

from .models import JobPost


class JobPostViewTests(TestCase):
    def test_create_page_loads(self):
        response = self.client.get(reverse('jobposts.create'))
        self.assertEqual(response.status_code, 200)

    def test_valid_post_creates_jobpost(self):
        payload = {
            'title': 'Backend Engineer',
            'company': 'Acme Inc',
            'location': 'Remote',
            'pay_range': '$70k-$90k',
            'description': 'Build APIs and services.',
        }

        response = self.client.post(reverse('jobposts.create'), payload)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(JobPost.objects.count(), 1)
