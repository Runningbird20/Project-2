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
