from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from datetime import timedelta
from django.utils import timezone

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

    profile_picture = models.ImageField(
        upload_to="profile_pics/",
        blank=True,
        null=True
    )

    # Applicant fields
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

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} Profile"


class ProfileLink(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="links")
    label = models.CharField(max_length=60, blank=True)
    url = models.URLField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.label or self.url
    

class SavedCandidateSearch(models.Model):
    employer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_searches')
    search_name = models.CharField(max_length=255)
    filters = models.JSONField()  
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.search_name
    
    @property
    def has_new_matches(self):
        from .models import Profile
        from django.db.models import Q
        
        skills = self.filters.get('skills', '')
        loc = self.filters.get('location', '')
        proj = self.filters.get('projects', '')

        qs = Profile.objects.filter(
            account_type='APPLICANT',
            visible_to_recruiters=True,
            created_at__gt=timezone.now() - timedelta(days=1)
        )

        if skills:
            terms = [t.strip() for t in skills.split(",") if t.strip()]
            for t in terms:
                qs = qs.filter(skills__icontains=t)
        if loc:
            qs = qs.filter(location__icontains=loc)
        if proj:
            qs = qs.filter(Q(projects__icontains=proj) | Q(headline__icontains=proj))

        return qs.exists()