from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import InterviewSlot
from .services import (
    create_slot_from_form,
    is_applicant,
    is_employer,
    build_ics_content,
    mark_application_interview,
    notify_booking,
)
from .forms import InterviewSlotProposalForm


@login_required
@require_POST
def propose_slot(request):
    if not is_employer(request.user):
        return HttpResponseForbidden("Only employers can propose interview slots.")

    form = InterviewSlotProposalForm(request.POST, employer=request.user)
    if not form.is_valid():
        messages.error(request, "Could not create slot. Check date/time and fields.")
        return redirect("jobposts.dashboard")

    create_slot_from_form(form)
    messages.success(request, "Interview slot proposed.")
    return redirect("jobposts.dashboard")


@login_required
@require_POST
def book_slot(request, slot_id):
    if not is_applicant(request.user):
        return HttpResponseForbidden("Only applicants can select interview slots.")

    with transaction.atomic():
        slot = get_object_or_404(
            InterviewSlot.objects.select_for_update().select_related("application", "application__job"),
            id=slot_id,
            applicant=request.user,
        )
        if slot.status != InterviewSlot.Status.OPEN:
            messages.error(request, "This interview slot is no longer available.")
            return redirect("apply:application_status")

        slot.status = InterviewSlot.Status.BOOKED
        slot.booked_at = timezone.now()
        slot.booked_by = request.user
        slot.save(update_fields=["status", "booked_at", "booked_by"])

        InterviewSlot.objects.filter(
            application=slot.application,
            applicant=request.user,
            status=InterviewSlot.Status.OPEN,
        ).exclude(id=slot.id).update(status=InterviewSlot.Status.CANCELED)

        mark_application_interview(slot.application)
        notify_booking(slot)

    messages.success(request, "Interview scheduled successfully.")
    return redirect("apply:application_status")


@login_required
def download_ics(request, slot_id):
    slot = get_object_or_404(InterviewSlot.objects.select_related("application", "application__job"), id=slot_id)
    if request.user.id not in [slot.applicant_id, slot.employer_id]:
        return HttpResponseForbidden("Unauthorized.")
    if slot.status != InterviewSlot.Status.BOOKED:
        return HttpResponseForbidden("ICS is available for scheduled interviews only.")

    response = HttpResponse(build_ics_content(slot), content_type="text/calendar")
    response["Content-Disposition"] = f'attachment; filename="interview-{slot.id}.ics"'
    return response
