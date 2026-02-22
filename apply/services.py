from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from .models import Application


def auto_archive_old_rejections():
    cutoff = timezone.now() - timedelta(days=30)
    stale_rejections = Application.objects.filter(
        status="rejected",
    ).filter(
        Q(rejected_at__lte=cutoff) | Q(rejected_at__isnull=True, applied_at__lte=cutoff)
    )
    stale_rejections.update(
        archived_by_applicant=True,
        archived_by_employer=True,
    )


def enforce_employer_response_deadline():
    cutoff = timezone.now() - timedelta(days=30)
    overdue = Application.objects.filter(
        status__in=["applied", "review", "interview", "offer"],
    ).filter(
        Q(responded_at__lte=cutoff) | Q(responded_at__isnull=True, applied_at__lte=cutoff)
    )
    overdue.update(
        status="rejected",
        rejected_at=timezone.now(),
        auto_rejected_for_timeout=True,
        rejected_offer_by_applicant=False,
    )


def calculate_application_streak(user):
    application_dates = {
        app.applied_at.date()
        for app in Application.objects.filter(user=user).only("applied_at")
    }
    if not application_dates:
        return 0

    today = timezone.localdate()
    anchor = today if today in application_dates else today - timedelta(days=1)
    if anchor not in application_dates:
        return 0

    streak = 0
    day_cursor = anchor
    while day_cursor in application_dates:
        streak += 1
        day_cursor -= timedelta(days=1)
    return streak
