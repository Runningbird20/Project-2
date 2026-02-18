from django.db import models
from django.conf import settings


class JobPost(models.Model):
    COMPANY_SIZE_CHOICES = [
        ("small", "Small (1-50)"),
        ("mid_size", "Mid-size (51-500)"),
        ("large", "Large (501-5,000)"),
        ("fortune_500", "Fortune 500"),
        ("startup", "Startup"),
        ("enterprise", "Enterprise"),
        ("other", "Other"),
    ]
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
    company_size = models.CharField(max_length=20, choices=COMPANY_SIZE_CHOICES, default="other")
    visa_sponsorship = models.BooleanField(default=False)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} at {self.company}"
