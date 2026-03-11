from django.contrib import admin

from .models import InterviewFeedback, InterviewSkillEndorsement, InterviewSlot
from project2.admin_permissions import StaffReadOnlyAdminMixin


@admin.register(InterviewSlot)
class InterviewSlotAdmin(StaffReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ("id", "application", "employer", "applicant", "start_at", "end_at", "status")
    list_filter = ("status", "start_at")
    search_fields = ("application__job__title", "application__job__company", "applicant__username", "employer__username")


@admin.register(InterviewFeedback)
class InterviewFeedbackAdmin(StaffReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = (
        "id",
        "interview_slot",
        "employer",
        "recommendation",
        "technical_score",
        "communication_score",
        "problem_solving_score",
        "updated_at",
    )
    list_filter = ("recommendation", "updated_at")
    search_fields = (
        "interview_slot__application__job__title",
        "interview_slot__application__job__company",
        "interview_slot__applicant__username",
        "employer__username",
        "decision_rationale",
    )


@admin.register(InterviewSkillEndorsement)
class InterviewSkillEndorsementAdmin(StaffReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ("id", "interview_slot", "employer", "applicant", "skill_name", "endorsed_at")
    list_filter = ("endorsed_at",)
    search_fields = (
        "skill_name",
        "interview_slot__application__job__title",
        "interview_slot__application__job__company",
        "applicant__username",
        "employer__username",
    )

