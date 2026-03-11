from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import InterviewSkillEndorsement, InterviewSlot
from .services import (
    create_slot_from_form,
    is_applicant,
    is_employer,
    build_ics_content,
    mark_application_interview,
    notify_booking,
    normalize_skill_token,
    parse_skill_tokens,
)
from .forms import InterviewFeedbackForm, InterviewSlotProposalForm


@login_required
@require_POST
def propose_slot(request):
    if not is_employer(request.user):
        return HttpResponseForbidden("Only employers can propose interview slots.")

    form = InterviewSlotProposalForm(request.POST, employer=request.user)
    if not form.is_valid():
        messages.error(request, "Could not create slot. Check date/time and fields.")
        return redirect(f"{reverse('jobposts.dashboard')}?tab=emp-interviews")

    slot = create_slot_from_form(form)
    messages.success(request, "Interview slot proposed.")
    month_key = timezone.localtime(slot.start_at).strftime("%Y-%m")
    return redirect(
        f"{reverse('jobposts.dashboard')}?tab=emp-interviews&interview_month={month_key}&interview_application={slot.application_id}"
    )


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


@login_required
@require_POST
def save_feedback(request, slot_id):
    if not is_employer(request.user):
        return HttpResponseForbidden("Only employers can save interview feedback.")

    slot = get_object_or_404(
        InterviewSlot.objects.select_related("application", "application__job", "feedback"),
        id=slot_id,
        employer=request.user,
        status=InterviewSlot.Status.BOOKED,
    )
    if slot.end_at > timezone.now():
        return HttpResponseForbidden("Interview feedback can be submitted only after the interview has ended.")

    form = InterviewFeedbackForm(
        request.POST,
        instance=getattr(slot, "feedback", None),
        prefix=f"feedback-{slot.id}",
    )
    if not form.is_valid():
        messages.error(request, "Could not save interview feedback. Please review all fields.")
    else:
        with transaction.atomic():
            feedback = form.save(commit=False)
            feedback.interview_slot = slot
            feedback.employer = request.user
            feedback.save()

            try:
                applicant_profile = slot.applicant.profile
            except ObjectDoesNotExist:
                applicant_profile = None

            allowed_skill_map = {
                normalize_skill_token(skill): skill
                for skill in parse_skill_tokens(getattr(applicant_profile, "skills", ""))
            }
            selected_skill_keys = []
            seen_keys = set()
            for raw_skill in request.POST.getlist("endorsed_skills"):
                key = normalize_skill_token(raw_skill)
                if not key or key not in allowed_skill_map or key in seen_keys:
                    continue
                seen_keys.add(key)
                selected_skill_keys.append(key)

            existing = InterviewSkillEndorsement.objects.filter(interview_slot=slot)
            existing_keys = set(existing.values_list("skill_key", flat=True))
            existing.exclude(skill_key__in=selected_skill_keys).delete()
            for key in selected_skill_keys:
                if key in existing_keys:
                    continue
                InterviewSkillEndorsement.objects.create(
                    interview_slot=slot,
                    employer=request.user,
                    applicant=slot.applicant,
                    skill_name=allowed_skill_map[key],
                    skill_key=key,
                )
        messages.success(request, "Interview feedback saved.")

    month_key = timezone.localtime(slot.start_at).strftime("%Y-%m")
    return redirect(f"{reverse('jobposts.dashboard')}?tab=emp-interviews&interview_month={month_key}")
