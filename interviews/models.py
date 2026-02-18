from datetime import timedelta
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apply.models import Application


class InterviewSlot(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        BOOKED = "booked", "Booked"
        CANCELED = "canceled", "Canceled"

    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name="interview_slots",
    )
    employer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="proposed_interview_slots",
    )
    applicant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="applicant_interview_slots",
    )
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    meeting_link = models.URLField(blank=True)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    proposed_at = models.DateTimeField(auto_now_add=True)
    booked_at = models.DateTimeField(null=True, blank=True)
    booked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="booked_interview_slots",
        null=True,
        blank=True,
    )
    calendar_uid = models.CharField(max_length=120, unique=True, blank=True)

    class Meta:
        ordering = ["start_at"]

    def __str__(self):
        return f"{self.application.job.title} - {self.start_at.isoformat()}"

    def clean(self):
        if self.end_at <= self.start_at:
            raise ValidationError("Interview end time must be after start time.")
        if self.application.job.owner_id != self.employer_id:
            raise ValidationError("Employer must own the job for this application.")
        if self.application.user_id != self.applicant_id:
            raise ValidationError("Applicant must match the selected application.")

    def save(self, *args, **kwargs):
        if self.application_id:
            self.employer_id = self.application.job.owner_id
            self.applicant_id = self.application.user_id
        if not self.calendar_uid:
            self.calendar_uid = f"pandapulse-{uuid.uuid4()}"
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def is_upcoming(self):
        return self.start_at >= timezone.now()

    @property
    def duration_minutes(self):
        return int((self.end_at - self.start_at).total_seconds() // 60)

    @property
    def google_calendar_url(self):
        from .services import google_calendar_link

        return google_calendar_link(self)

    @classmethod
    def create_from_duration(
        cls,
        application,
        start_at,
        duration_minutes,
        meeting_link="",
        notes="",
    ):
        return cls.objects.create(
            application=application,
            employer=application.job.owner,
            applicant=application.user,
            start_at=start_at,
            end_at=start_at + timedelta(minutes=duration_minutes),
            meeting_link=meeting_link,
            notes=notes,
        )
