from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from accounts.models import Profile, ProfileLink, SavedCandidateSearch
from apply.models import Application
from chatbot.models import ChatFeedback
from interviews.models import InterviewSlot
from jobposts.models import ApplicantJobMatch, JobPost
from messaging.models import Message
from pulses.models import Pulse


class Command(BaseCommand):
    help = "Delete orphaned rows left behind by previously deleted user accounts."

    def handle(self, *args, **options):
        User = get_user_model()
        user_ids = User.objects.values_list("id", flat=True)

        deleted_total = 0

        cleanup_sets = [
            ("Profile", Profile.objects.exclude(user_id__in=user_ids)),
            ("SavedCandidateSearch", SavedCandidateSearch.objects.exclude(employer_id__in=user_ids)),
            ("Application", Application.objects.exclude(user_id__in=user_ids)),
            ("JobPost", JobPost.objects.exclude(owner_id__isnull=True).exclude(owner_id__in=user_ids)),
            ("ApplicantJobMatch", ApplicantJobMatch.objects.exclude(applicant_id__in=user_ids)),
            ("Message(sender)", Message.objects.exclude(sender_id__in=user_ids)),
            ("Message(recipient)", Message.objects.exclude(recipient_id__in=user_ids)),
            ("InterviewSlot(application)", InterviewSlot.objects.exclude(application_id__in=Application.objects.values_list("id", flat=True))),
            ("InterviewSlot(employer)", InterviewSlot.objects.exclude(employer_id__in=user_ids)),
            ("InterviewSlot(applicant)", InterviewSlot.objects.exclude(applicant_id__in=user_ids)),
            ("Pulse", Pulse.objects.exclude(user_id__in=user_ids)),
            ("ChatFeedback", ChatFeedback.objects.exclude(user_id__in=user_ids)),
        ]

        for label, queryset in cleanup_sets:
            count = queryset.count()
            if count:
                queryset.delete()
                deleted_total += count
                self.stdout.write(self.style.WARNING(f"Deleted {count} orphan {label} rows"))

        updated_booked_by = (
            InterviewSlot.objects.exclude(booked_by_id__isnull=True)
            .exclude(booked_by_id__in=user_ids)
            .update(booked_by=None)
        )
        if updated_booked_by:
            self.stdout.write(
                self.style.WARNING(
                    f"Nullified booked_by on {updated_booked_by} InterviewSlot rows with missing users"
                )
            )

        orphan_links = ProfileLink.objects.exclude(profile_id__in=Profile.objects.values_list("id", flat=True))
        orphan_links_count = orphan_links.count()
        if orphan_links_count:
            orphan_links.delete()
            deleted_total += orphan_links_count
            self.stdout.write(self.style.WARNING(f"Deleted {orphan_links_count} orphan ProfileLink rows"))

        if deleted_total == 0 and updated_booked_by == 0:
            self.stdout.write(self.style.SUCCESS("No orphaned deleted-account data found."))
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Cleanup complete. Deleted {deleted_total} orphan rows; updated {updated_booked_by} rows."
                )
            )
