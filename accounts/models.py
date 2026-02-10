# accounts/models.py
from django.conf import settings
from django.db import models

class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")

    headline = models.CharField(max_length=120, blank=True)
    # quick MVP: comma-separated skills
    skills = models.CharField(max_length=300, blank=True, help_text="Comma-separated, e.g. Python, Django, SQL")

    # MVP as freeform text; can later normalize into separate Education/Experience models
    education = models.TextField(blank=True, help_text="Write your education background")
    work_experience = models.TextField(blank=True, help_text="Write your work experience")

    def __str__(self):
        return f"{self.user.username} Profile"


class ProfileLink(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="links")
    label = models.CharField(max_length=60, blank=True)
    url = models.URLField()

    def __str__(self):
        return self.label or self.url
