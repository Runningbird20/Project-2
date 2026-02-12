from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse

from accounts.models import Profile
from .models import JobPost


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
            'location': 'Remote',
            'pay_range': '$70k-$90k',
            'work_setting': 'remote',
            'description': 'Build APIs and services.',
        }

        response = self.client.post(reverse('jobposts.create'), payload)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(JobPost.objects.count(), 1)

    def test_applicant_post_does_not_create_jobpost(self):
        self.client.login(username='applicant', password='pass12345')
        payload = {
            'title': 'Backend Engineer',
            'company': 'Acme Inc',
            'location': 'Remote',
            'pay_range': '$70k-$90k',
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
            'location': 'Remote',
            'pay_range': '$70k-$90k',
            'work_setting': 'remote',
            'description': 'Build APIs and services.',
        }
        self.client.login(username='employer2', password='pass12345')
        response = self.client.post(reverse('jobposts.edit', args=[post.id]), payload)
        post.refresh_from_db()

        self.assertEqual(response.status_code, 404)
        self.assertEqual(post.title, 'Backend Engineer')
