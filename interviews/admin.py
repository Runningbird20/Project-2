from django.contrib import admin

from .models import InterviewSlot


@admin.register(InterviewSlot)
class InterviewSlotAdmin(admin.ModelAdmin):
    list_display = ("id", "application", "employer", "applicant", "start_at", "end_at", "status")
    list_filter = ("status", "start_at")
    search_fields = ("application__job__title", "application__job__company", "applicant__username", "employer__username")

