import os
from datetime import timedelta
import re

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.db.models import Q
from django.utils import timezone


def _normalize_skill_option_name(raw_value):
    return re.sub(r"\s+", " ", (raw_value or "").strip())


class SkillOption(models.Model):
    name = models.CharField(max_length=120)
    normalized_name = models.CharField(max_length=120, unique=True, db_index=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_skill_options",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        self.name = _normalize_skill_option_name(self.name)
        self.normalized_name = self.name.lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

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
    resume_file = models.FileField(
        upload_to="profile_resumes/",
        blank=True,
        null=True,
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

    parsed_resume_skills = models.TextField(blank=True)
    
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
    def resume_file_name(self):
        if not self.resume_file:
            return ""
        return os.path.basename(self.resume_file.name)

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
    last_viewed_at = models.DateTimeField(null=True, blank=True)
    last_notified_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.search_name

    @property
    def normalized_filters(self):
        raw_filters = self.filters or {}
        return {
            "skills": (raw_filters.get("skills", "") or "").strip(),
            "location": (raw_filters.get("location", "") or "").strip(),
            "projects": (raw_filters.get("projects", "") or "").strip(),
        }

    def matching_profiles_queryset(self):
        filters = self.normalized_filters
        skills = filters["skills"]
        location = filters["location"]
        projects = filters["projects"]

        qs = Profile.objects.filter(
            account_type=Profile.AccountType.APPLICANT,
            visible_to_recruiters=True,
        ).select_related("user").order_by("user__username")

        if skills:
            for term in [token.strip() for token in skills.split(",") if token.strip()]:
                qs = qs.filter(skills__icontains=term)
        if location:
            qs = qs.filter(
                Q(location__icontains=location)
                | Q(city__icontains=location)
                | Q(state__icontains=location)
                | Q(address_line_1__icontains=location)
            )
        if projects:
            qs = qs.filter(Q(projects__icontains=projects) | Q(headline__icontains=projects))

        return qs

    def new_matches_queryset(self):
        reference_time = self.last_viewed_at or self.created_at or (timezone.now() - timedelta(days=1))
        return self.matching_profiles_queryset().filter(created_at__gt=reference_time)

    def matches_to_notify_queryset(self):
        reference_time = self.created_at or (timezone.now() - timedelta(days=1))
        if self.last_viewed_at and self.last_viewed_at > reference_time:
            reference_time = self.last_viewed_at
        if self.last_notified_at and self.last_notified_at > reference_time:
            reference_time = self.last_notified_at
        return self.matching_profiles_queryset().filter(created_at__gt=reference_time)

    def mark_viewed(self):
        self.last_viewed_at = timezone.now()
        self.save(update_fields=["last_viewed_at"])

    def mark_notified(self):
        self.last_notified_at = timezone.now()
        self.save(update_fields=["last_notified_at"])

    @property
    def filters_summary(self):
        filters = self.normalized_filters
        summary_parts = []
        if filters["skills"]:
            summary_parts.append(f"Skills: {filters['skills']}")
        if filters["location"]:
            summary_parts.append(f"Location: {filters['location']}")
        if filters["projects"]:
            summary_parts.append(f"Projects: {filters['projects']}")
        return " | ".join(summary_parts) if summary_parts else "All candidates"

    @property
    def has_new_matches(self):
        return self.new_matches_queryset().exists()
