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


class InterviewFeedback(models.Model):
    class Recommendation(models.TextChoices):
        ADVANCE = "advance", "Advance"
        HOLD = "hold", "Hold"
        REJECT = "reject", "Reject"

    interview_slot = models.OneToOneField(
        InterviewSlot,
        on_delete=models.CASCADE,
        related_name="feedback",
    )
    employer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="interview_feedback_entries",
    )
    technical_score = models.PositiveSmallIntegerField()
    communication_score = models.PositiveSmallIntegerField()
    problem_solving_score = models.PositiveSmallIntegerField()
    recommendation = models.CharField(max_length=20, choices=Recommendation.choices)
    strengths = models.TextField(blank=True)
    concerns = models.TextField(blank=True)
    decision_rationale = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"Feedback for slot {self.interview_slot_id}"

    def clean(self):
        if self.interview_slot_id and self.interview_slot.employer_id != self.employer_id:
            raise ValidationError("Feedback employer must match the interview employer.")

        for field_name in ["technical_score", "communication_score", "problem_solving_score"]:
            score = getattr(self, field_name)
            if score is None:
                raise ValidationError({field_name: "Score is required."})
            if score < 1 or score > 5:
                raise ValidationError({field_name: "Scores must be between 1 and 5."})

    def save(self, *args, **kwargs):
        if self.interview_slot_id and not self.employer_id:
            self.employer_id = self.interview_slot.employer_id
        self.full_clean()
        super().save(*args, **kwargs)


class InterviewSkillEndorsement(models.Model):
    interview_slot = models.ForeignKey(
        InterviewSlot,
        on_delete=models.CASCADE,
        related_name="skill_endorsements",
    )
    employer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="interview_skill_endorsements_given",
    )
    applicant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="interview_skill_endorsements_received",
    )
    skill_name = models.CharField(max_length=120)
    skill_key = models.CharField(max_length=120, db_index=True, blank=True)
    endorsed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-endorsed_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["interview_slot", "skill_key"],
                name="unique_interview_slot_skill_endorsement",
            )
        ]

    def __str__(self):
        return f"{self.skill_name} endorsed for slot {self.interview_slot_id}"

    def clean(self):
        if self.interview_slot_id:
            if self.interview_slot.employer_id != self.employer_id:
                raise ValidationError("Endorsement employer must match interview employer.")
            if self.interview_slot.applicant_id != self.applicant_id:
                raise ValidationError("Endorsement applicant must match interview applicant.")

        normalized = " ".join((self.skill_name or "").split()).strip()
        if not normalized:
            raise ValidationError({"skill_name": "Skill name is required."})
        self.skill_name = normalized
        self.skill_key = normalized.lower()

    def save(self, *args, **kwargs):
        if self.interview_slot_id:
            self.employer_id = self.interview_slot.employer_id
            self.applicant_id = self.interview_slot.applicant_id
        self.full_clean()
        super().save(*args, **kwargs)
