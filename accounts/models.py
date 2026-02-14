from django.conf import settings
from django.db import models

class Profile(models.Model):

    class AccountType(models.TextChoices):
        APPLICANT = "APPLICANT", "Job Applicant"
        EMPLOYER = "EMPLOYER", "Employer"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")

    account_type = models.CharField(
        max_length=20,
        choices=AccountType.choices,
        default=AccountType.APPLICANT
    )

    # Applicant-ish fields (keep your existing ones)
    headline = models.CharField(max_length=120, blank=True)
    skills = models.CharField(max_length=300, blank=True)
    education = models.TextField(blank=True)
    work_experience = models.TextField(blank=True)
    location = models.CharField(max_length=120, blank=True)
    projects = models.TextField(blank=True)

    # Employer-only fields
    company_name = models.CharField(max_length=120, blank=True)
    company_website = models.URLField(blank=True)
    company_description = models.TextField(blank=True)

    visible_to_recruiters = models.BooleanField(
        default=True,
        help_text="Allow recruiters to view your profile."
    )
    show_headline = models.BooleanField(default=True)
    show_skills = models.BooleanField(default=True)
    show_education = models.BooleanField(default=True)
    show_work_experience = models.BooleanField(default=True)
    show_links = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.username} Profile"


class ProfileLink(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="links")
    label = models.CharField(max_length=60, blank=True)
    url = models.URLField()

    def __str__(self):
        return self.label or self.url
