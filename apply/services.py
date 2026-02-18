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
    )
