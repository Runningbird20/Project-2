from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from jobposts.models import JobPost


class AdminReadOnlyStaffTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.superuser = user_model.objects.create_user(
            username="admin_root",
            password="test-password-123",
            is_superuser=True,
            is_staff=True,
        )
        self.staff = user_model.objects.create_user(
            username="admin_viewer",
            password="test-password-123",
            is_staff=True,
        )
        self.owner = user_model.objects.create_user(
            username="job_owner",
            password="test-password-123",
        )
        self.job = JobPost.objects.create(
            owner=self.owner,
            title="Backend Engineer",
            company="Acme",
            location="Atlanta, GA",
            pay_range="$100k-$130k",
            work_setting="hybrid",
            description="Build APIs",
        )

    def test_staff_can_view_admin_pages(self):
        self.client.login(username="admin_viewer", password="test-password-123")
        index_response = self.client.get(reverse("admin:index"))
        list_response = self.client.get(reverse("admin:jobposts_jobpost_changelist"))
        change_response = self.client.get(reverse("admin:jobposts_jobpost_change", args=[self.job.id]))

        self.assertEqual(index_response.status_code, 200)
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(change_response.status_code, 200)

    def test_staff_cannot_open_add_page(self):
        self.client.login(username="admin_viewer", password="test-password-123")
        add_response = self.client.get(reverse("admin:jobposts_jobpost_add"))
        self.assertEqual(add_response.status_code, 403)

    def test_superuser_can_open_add_page(self):
        self.client.login(username="admin_root", password="test-password-123")
        add_response = self.client.get(reverse("admin:jobposts_jobpost_add"))
        self.assertEqual(add_response.status_code, 200)
