from django.db import models
from django.contrib.auth.models import User
from jobposts.models import JobPost
from datetime import timedelta
from django.utils import timezone

class Apply(models.Model):
    company = models.CharField(max_length=100)
    title = models.CharField(max_length=100)
    salary_range = models.CharField(max_length=50)
    logo = models.ImageField(upload_to="logos/", blank=True, null=True)

    def __str__(self):
        return f"{self.title} @ {self.company}"
    
class Application(models.Model):
    STATUS_CHOICES = [
        ("applied", "Applied"),
        ("review", "Under Review"),
        ("interview", "Interview"),
        ("offer", "Offer"),
        ("rejected", "Rejected"),
        ("closed", "Closed"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    job = models.ForeignKey(JobPost, on_delete=models.CASCADE, related_name="applications")
    note = models.TextField(blank=True)

    resume_file = models.FileField(upload_to="resumes/", blank=True, null=True)

    resume_type = models.CharField(
        max_length=20,
        choices=[("profile", "Profile Resume"), ("uploaded", "Uploaded Resume")]
    )
    applied_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="applied")
    employer_viewed = models.BooleanField(default=False)
    employer_viewed_at = models.DateTimeField(blank=True, null=True)
    responded_at = models.DateTimeField(blank=True, null=True)
    auto_rejected_for_timeout = models.BooleanField(default=False)
    rejected_at = models.DateTimeField(blank=True, null=True)
    archived_by_applicant = models.BooleanField(default=False)
    archived_by_employer = models.BooleanField(default=False)
    rejected_offer_by_applicant = models.BooleanField(default=False)
    offer_letter_title = models.CharField(max_length=200, blank=True)
    offer_letter_body = models.TextField(blank=True)
    offer_compensation = models.CharField(max_length=200, blank=True)
    offer_start_date = models.CharField(max_length=120, blank=True)
    offer_response_deadline = models.CharField(max_length=120, blank=True)
    offer_additional_terms = models.TextField(blank=True)

    class Meta:
        unique_together = ("user", "job")

    def __str__(self):
        return f"{self.user.username} - {self.job.title}"

    @property
    def auto_archive_on(self):
        base_time = self.rejected_at or self.applied_at
        if not base_time:
            return None
        return base_time + timedelta(days=30)

    @property
    def response_due_on(self):
        base_time = self.responded_at or self.applied_at
        if not base_time:
            return None
        return base_time + timedelta(days=30)

    @property
    def response_due_within_7_days(self):
        due_on = self.response_due_on
        if not due_on:
            return False
        days_remaining = (due_on - timezone.now()).days
        return 0 <= days_remaining <= 7
