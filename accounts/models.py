from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from datetime import timedelta
from django.utils import timezone
import re

class Profile(models.Model):

    class AccountType(models.TextChoices):
        APPLICANT = "APPLICANT", "Job Applicant"
        EMPLOYER = "EMPLOYER", "Employer"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    last_activity = models.DateTimeField(null=True, blank=True)
    is_typing = models.BooleanField(default=False)
    last_typing_update = models.DateTimeField(null=True, blank=True)

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
    location = models.CharField(max_length=255, blank=True)
    address_line_1 = models.CharField(max_length=255, blank=True)
    address_line_2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, blank=True, default="United States")
    projects = models.TextField(blank=True)

    # Employer-only fields
    company_name = models.CharField(max_length=120, blank=True)
    company_website = models.URLField(blank=True)
    company_description = models.TextField(blank=True)
    company_culture = models.TextField(blank=True)
    company_perks = models.TextField(blank=True)

    visible_to_recruiters = models.BooleanField(
        default=True,
        help_text="Allow recruiters to view your profile."
    )
    show_headline = models.BooleanField(default=True)
    show_skills = models.BooleanField(default=True)
    show_education = models.BooleanField(default=True)
    show_work_experience = models.BooleanField(default=True)
    show_links = models.BooleanField(default=True)
    hide_email_from_employers = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} Profile"

    @property
    def profile_picture_or_default_url(self):
        if self.profile_picture:
            return self.profile_picture.url
        return f"{settings.MEDIA_URL}profile_pics/default-icon.png"

    @property
    def location_city_state(self):
        """Return privacy-safe city/state for profiles."""
        city = (self.city or "").strip()
        state = (self.state or "").strip()
        if city and state:
            return f"{city}, {state}"

        # Legacy fallback for pre-structured addresses.
        raw = (self.location or "").strip()
        if not raw:
            return ""
        parts = [part.strip() for part in raw.split(",") if part.strip()]
        if len(parts) < 2:
            return ""

        last_part = parts[-1]
        has_explicit_country = not any(ch.isdigit() for ch in last_part) and len(last_part) > 2
        if has_explicit_country and len(parts) >= 3:
            city = parts[-3]
            region = parts[-2]
        else:
            city = parts[-2]
            region = parts[-1]

        match = re.match(r"^([A-Za-z]{2})(?:\s+\d{5}(?:-\d{4})?)?$", region)
        if match:
            return f"{city}, {match.group(1).upper()}"
        return ""

    @property
    def full_address(self):
        has_core_address = any(
            [
                (self.address_line_1 or "").strip(),
                (self.city or "").strip(),
                (self.state or "").strip(),
                (self.postal_code or "").strip(),
            ]
        )
        if not has_core_address:
            return (self.location or "").strip()

        parts = [
            (self.address_line_1 or "").strip(),
            (self.address_line_2 or "").strip(),
            (self.city or "").strip(),
            f"{(self.state or '').strip()} {(self.postal_code or '').strip()}".strip(),
            (self.country or "").strip(),
        ]
        combined = ", ".join([part for part in parts if part])
        if combined:
            return combined
        return (self.location or "").strip()


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
            qs = qs.filter(
                Q(location__icontains=loc)
                | Q(city__icontains=loc)
                | Q(state__icontains=loc)
                | Q(address_line_1__icontains=loc)
            )
        if proj:
            qs = qs.filter(Q(projects__icontains=proj) | Q(headline__icontains=proj))

        return qs.exists()
