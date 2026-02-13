from django.db import models
from django.conf import settings


class JobPost(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='job_posts',
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=200)
    company = models.CharField(max_length=150)
    location = models.CharField(max_length=150)
    pay_range = models.CharField(max_length=100)
    skills = models.CharField(max_length=300, blank=True)
    salary_min = models.IntegerField(null=True, blank=True)
    salary_max = models.IntegerField(null=True, blank=True)
    WORK_SETTING_CHOICES = [
        ("remote", "Remote"),
        ("onsite", "On-site"),
        ("hybrid", "Hybrid"),
    ]
    work_setting = models.CharField(max_length=20, choices=WORK_SETTING_CHOICES, default="onsite")
    visa_sponsorship = models.BooleanField(default=False)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} at {self.company}"
