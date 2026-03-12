from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse

from accounts.views import profile
from .models import Application
from jobposts.models import JobPost
from jobposts.models import ApplicantJobMatch
from jobposts.matching import sync_applicant_job_matches
from django.http import JsonResponse, HttpResponseForbidden, HttpResponse, Http404
from django.views.decorators.http import require_POST
import json
import csv
from datetime import timedelta
from django.utils import timezone
from accounts.models import Profile
from messaging.models import Message
from .services import (
    auto_archive_old_rejections,
    enforce_employer_response_deadline,
    calculate_application_streak,
)
from interviews.services import get_applicant_interview_context
from apply.resume_parser import parse_resume

PRIVATE_NOTE_MAX_LENGTH = 2000

def _benefits_score_from_company_perks(company_perks_text):
    perks_text = (company_perks_text or "").strip()
    if not perks_text:
        return 5
    tokens = [
        token.strip()
        for token in perks_text.replace("\n", ",").replace(";", ",").split(",")
        if token.strip()
    ]
    if not tokens:
        return 5
    return min(10, max(6, len(tokens)))


def _default_offer_letter_title(application):
    return f"Offer for {application.job.title} at {application.job.company}"


def _default_offer_letter_body(application):
    owner_name = "Hiring Team"
    if application.job.owner:
        owner_name = application.job.owner.get_full_name() or application.job.owner.username
    return (
        f"Dear {application.user.get_full_name() or application.user.username},\n\n"
        f"We are pleased to offer you the position of {application.job.title} at {application.job.company}. "
        "We are excited about the skills and experience you would bring to our team.\n\n"
        "Please review the details below and contact us if you have any questions.\n\n"
        "Sincerely,\n"
        f"{owner_name}"
    )


def _default_offer_compensation(application):
    if application.job.salary_max:
        return f"${application.job.salary_max:,}"
    if application.job.salary_min:
        return f"${application.job.salary_min:,}"
    return application.job.pay_range or "Compensation details to be provided."


def _default_offer_response_deadline():
    return (timezone.now() + timedelta(days=7)).strftime("%B %d, %Y")


REJECTION_FEEDBACK_TEMPLATES = {
    "skills_alignment": {
        "label": "Skills Alignment",
        "body": (
            "Thank you for applying. We are moving forward with candidates whose recent skills "
            "and project experience more closely match this role."
        ),
    },
    "experience_scope": {
        "label": "Experience Scope",
        "body": (
            "Thank you for your time. We selected candidates with more direct experience in the "
            "scope and seniority this position currently requires."
        ),
    },
    "role_fit": {
        "label": "Role Fit",
        "body": (
            "We appreciate your interest. We decided to continue with applicants whose background "
            "is a closer fit for this specific team and role focus."
        ),
    },
}


def _serialize_rejection_feedback_templates():
    return [
        {
            "key": key,
            "label": template_data["label"],
            "body": template_data["body"],
        }
        for key, template_data in REJECTION_FEEDBACK_TEMPLATES.items()
    ]


def _build_rejection_feedback_text(template_key, personalized_note):
    template_data = REJECTION_FEEDBACK_TEMPLATES.get(template_key)
    if not template_data:
        return ""
    note_text = (personalized_note or "").strip()
    sections = [template_data["body"]]
    if note_text:
        sections.append(f"Additional note from your recruiter:\n{note_text}")
    return "\n\n".join(sections)


def _as_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    if isinstance(value, (int, float)):
        return bool(value)
    return False


def _ensure_offer_defaults(application):
    changed_fields = []
    if not application.offer_letter_title:
        application.offer_letter_title = _default_offer_letter_title(application)
        changed_fields.append("offer_letter_title")
    if not application.offer_letter_body:
        application.offer_letter_body = _default_offer_letter_body(application)
        changed_fields.append("offer_letter_body")
    if not application.offer_compensation:
        application.offer_compensation = _default_offer_compensation(application)
        changed_fields.append("offer_compensation")
    if not application.offer_start_date:
        application.offer_start_date = "To be discussed with recruiter"
        changed_fields.append("offer_start_date")
    if not application.offer_response_deadline:
        application.offer_response_deadline = _default_offer_response_deadline()
        changed_fields.append("offer_response_deadline")
    if changed_fields:
        application.save(update_fields=changed_fields)

@login_required
def submit_application(request, job_id):
    """Handles the submission of a job application."""
    if request.method != "POST":
        return redirect("jobposts.search")

    job = get_object_or_404(JobPost, id=job_id)
    note = request.POST.get("note", "")
    resume_type = request.POST.get("resume_type")  # expects 'profile' or 'uploaded'
    resume_file = request.FILES.get("resume_file")

    if Application.objects.filter(user=request.user, job=job).exists():
        messages.warning(request, f"You have already applied for {job.title}.")
        return redirect("jobposts.search")

    # Safety: normalize resume_type
    if resume_type not in ("profile", "uploaded"):
        resume_type = "profile"

    application = Application.objects.create(
        user=request.user,
        job=job,
        note=note,
        resume_type=resume_type,
        resume_file=resume_file if resume_type == "uploaded" else None,
    )

    if application.resume_file:
        try:
            parsed = parse_resume(application.resume_file.path)
            skills_list = parsed.get("skills", [])
            skills_csv = ", ".join(skills_list)
            profile = request.user.profile
            profile.parsed_resume_skills = skills_csv
            profile.save()

        except Exception as exc:
            if settings.DEBUG:
                print("Resume parsing failed:", exc)

        


    if request.user.email:
        try:
            send_mail(
                subject=f"Application submitted: {job.title}",
                message=(
                    f"Hi {request.user.username},\n\n"
                    f"Thank you for applying to {job.title} at {job.company}. "
                    "Your application has been successfully submitted.\n\n"
                    "You can track the status of your application, receive updates, and "
                    "manage your submissions anytime by logging into your PandaPulse "
                    "account.\n\n"
                    "We wish you the best of luck and will notify you as soon as there "
                    "are any updates.\n\n"
                    "Best regards,\n"
                    "The PandaPulse Team\n"
                ),
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@pandapulse.local"),
                recipient_list=[request.user.email],
                fail_silently=False,
            )
        except Exception as exc:
            if settings.DEBUG:
                messages.warning(request, f"Application confirmation email could not be sent: {exc}")
            else:
                messages.warning(request, "Application confirmation email could not be sent.")

    if job.owner and job.owner.email:
        try:
            send_mail(
                subject=f"New application received: {job.title}",
                message=(
                    f"{application.user.username} submitted an application for '{job.title}'.\n\n"
                    "Log in to PandaPulse to review the candidate."
                ),
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@pandapulse.local"),
                recipient_list=[job.owner.email],
                fail_silently=False,
            )
        except Exception as exc:
            if settings.DEBUG:
                messages.warning(request, f"Employer notification email could not be sent: {exc}")
            else:
                messages.warning(request, "Employer notification email could not be sent.")

    messages.success(request, f"Application for {job.title} submitted successfully!")

    # ✅ This survives redirects and can be consumed by templates
    request.session["panda_apply_success"] = True

    return redirect("apply:application_submitted", job_id=job.id)

@login_required
def application_submitted(request, job_id):
    job = get_object_or_404(JobPost, id=job_id)
    template_data = {
        "title": "Application Submitted",
        "job": job,
    }
    return render(request, "apply/application_submitted.html", {"template_data": template_data})

@login_required
def application_status(request):
    """View for applicants to see the status of their own applications (Read-Only)."""
    enforce_employer_response_deadline()
    auto_archive_old_rejections()
    sync_applicant_job_matches(request.user)
    active_applications = Application.objects.filter(
        user=request.user,
        archived_by_applicant=False,
    ).select_related("job")
    for application in active_applications:
        template_data = REJECTION_FEEDBACK_TEMPLATES.get(application.rejection_feedback_template, {})
        application.rejection_feedback_template_label = template_data.get("label", "")
        application.rejection_feedback_template_body = template_data.get("body", "")
    received_offers = Application.objects.filter(
        user=request.user,
        status__in=("offer", "closed"),
    ).select_related("job", "job__owner").order_by("-responded_at", "-applied_at")
    received_offer_rows = []
    for offer in received_offers:
        salary_value = offer.job.salary_max or offer.job.salary_min or 0
        salary_display = (
            f"${salary_value:,}" if salary_value else (offer.job.pay_range or "Not specified")
        )
        try:
            owner_profile = offer.job.owner.profile if offer.job.owner else None
        except Profile.DoesNotExist:
            owner_profile = None
        benefits_score = _benefits_score_from_company_perks(
            getattr(owner_profile, "company_perks", "")
        )
        received_offer_rows.append(
            {
                "application_id": offer.id,
                "company": offer.job.company,
                "title": offer.job.title,
                "received_at": offer.responded_at or offer.applied_at,
                "salary_value": salary_value,
                "salary_display": salary_display,
                "work_setting": offer.job.work_setting,
                "work_setting_label": offer.job.get_work_setting_display(),
                "visa": "yes" if offer.job.visa_sponsorship else "no",
                "visa_label": "Yes" if offer.job.visa_sponsorship else "No",
                "benefits_score": benefits_score,
            }
        )
    archived_applications = Application.objects.filter(
        user=request.user,
        archived_by_applicant=True,
    ).select_related("job")
    all_applications = Application.objects.filter(user=request.user).select_related("job")

    activity_events = []
    for application in all_applications:
        role_label = f"{application.job.title} at {application.job.company}"

        if application.employer_viewed_at:
            activity_events.append(
                {
                    "timestamp": application.employer_viewed_at,
                    "event_type": "Viewed",
                    "detail": f"Your application for {role_label} was viewed by the employer.",
                }
            )

        if application.status in {"review", "interview", "offer", "closed"} and application.responded_at:
            activity_events.append(
                {
                    "timestamp": application.responded_at,
                    "event_type": "Shortlisted",
                    "detail": f"You were shortlisted for {role_label}.",
                }
            )

        if application.status != "applied":
            status_time = application.rejected_at if application.status == "rejected" else application.responded_at
            if status_time:
                activity_events.append(
                    {
                        "timestamp": status_time,
                        "event_type": "Status Update",
                        "detail": (
                            f"{role_label} changed to {application.get_status_display()}."
                        ),
                    }
                )
        if application.status == "rejected" and application.rejection_feedback_sent_at:
            activity_events.append(
                {
                    "timestamp": application.rejection_feedback_sent_at,
                    "event_type": "Feedback",
                    "detail": f"Recruiter shared rejection feedback for {role_label}.",
                }
            )

    activity_events.sort(key=lambda item: item["timestamp"], reverse=True)
    activity_events = activity_events[:3]

    matched_jobs = (
        ApplicantJobMatch.objects.filter(applicant=request.user)
        .select_related("job")
        .order_by("-score", "-updated_at")
    )
    for match in matched_jobs:
        match.matched_skills_list = [
            token.strip()
            for token in (match.matched_skills or "").split(",")
            if token.strip()
        ]
    interview_context = get_applicant_interview_context(
        request.user,
        month_key=request.GET.get("interview_month"),
    )
    return render(
        request,
        "apply/status.html",
        {
            "applications": active_applications,
            "received_offer_rows": received_offer_rows,
            "archived_applications": archived_applications,
            "matched_jobs": matched_jobs,
            "activity_events": activity_events,
            "application_streak": calculate_application_streak(request.user),
            **interview_context,
        },
    )


@login_required
@require_POST
def save_applicant_private_note(request, application_id):
    application = get_object_or_404(Application, id=application_id, user=request.user)
    note_text = (request.POST.get("applicant_private_note") or "").strip()
    if len(note_text) > PRIVATE_NOTE_MAX_LENGTH:
        messages.warning(
            request,
            f"Applicant note must be {PRIVATE_NOTE_MAX_LENGTH} characters or fewer.",
        )
    else:
        application.applicant_private_note = note_text
        application.save(update_fields=["applicant_private_note"])
        messages.success(request, "Private note saved.")
    return redirect(f"{reverse('apply:application_status')}?tab=tab-applications")


@login_required
@require_POST
def save_employer_private_note(request, application_id):
    application = get_object_or_404(
        Application.objects.select_related("job"),
        id=application_id,
    )
    if application.job.owner != request.user:
        return HttpResponseForbidden("Unauthorized")

    note_text = (request.POST.get("employer_private_note") or "").strip()
    if len(note_text) > PRIVATE_NOTE_MAX_LENGTH:
        messages.warning(
            request,
            f"Employer note must be {PRIVATE_NOTE_MAX_LENGTH} characters or fewer.",
        )
    else:
        application.employer_private_note = note_text
        application.save(update_fields=["employer_private_note"])
        messages.success(request, "Private note saved.")
    return redirect("apply:employer_pipeline", job_id=application.job.id)


@login_required
@require_POST
def update_status(request, application_id):
    try:
        data = json.loads(request.body)
        new_status = data.get("status")
        send_feedback = _as_bool(data.get("send_feedback"))
        feedback_template_key = (data.get("feedback_template") or "").strip()
        feedback_note = (data.get("feedback_note") or "").strip()

        application = get_object_or_404(Application, id=application_id)

        if application.job.owner != request.user:
            return JsonResponse({"success": False, "error": "Unauthorized"}, status=403)

        valid_statuses = [choice[0] for choice in Application.STATUS_CHOICES]

        if new_status in valid_statuses:
            if send_feedback and new_status != "rejected":
                return JsonResponse(
                    {"success": False, "error": "Feedback can only be sent for rejected applicants."},
                    status=400,
                )
            if send_feedback and feedback_template_key not in REJECTION_FEEDBACK_TEMPLATES:
                return JsonResponse(
                    {"success": False, "error": "Invalid rejection feedback template."},
                    status=400,
                )
            if len(feedback_note) > 1000:
                return JsonResponse(
                    {"success": False, "error": "Feedback note must be 1000 characters or fewer."},
                    status=400,
                )

            application.status = new_status
            application.responded_at = timezone.now()
            if new_status == "rejected":
                application.rejected_at = timezone.now()
                application.auto_rejected_for_timeout = False
                application.rejected_offer_by_applicant = False
                if send_feedback:
                    application.rejection_feedback_template = feedback_template_key
                    application.rejection_feedback_note = feedback_note
                    application.rejection_feedback_sent_at = timezone.now()
                else:
                    application.rejection_feedback_template = ""
                    application.rejection_feedback_note = ""
                    application.rejection_feedback_sent_at = None
            else:
                application.rejected_at = None
                application.archived_by_applicant = False
                application.archived_by_employer = False
                application.auto_rejected_for_timeout = False
                application.rejected_offer_by_applicant = False
                application.rejection_feedback_template = ""
                application.rejection_feedback_note = ""
                application.rejection_feedback_sent_at = None
            application.save()
            if new_status == "offer":
                _ensure_offer_defaults(application)

            rejection_feedback_text = ""
            if new_status == "rejected" and send_feedback:
                rejection_feedback_text = _build_rejection_feedback_text(feedback_template_key, feedback_note)
                if rejection_feedback_text:
                    try:
                        Message.objects.create(
                            sender=request.user,
                            recipient=application.user,
                            body=(
                                f"Feedback for your {application.job.title} application at "
                                f"{application.job.company}:\n\n{rejection_feedback_text}"
                            ),
                        )
                    except Exception as exc:
                        if settings.DEBUG:
                            messages.warning(request, f"Rejection feedback message could not be sent: {exc}")
                        else:
                            messages.warning(request, "Rejection feedback message could not be sent.")

            if application.user.email:
                try:
                    status_email_message = (
                        f"Hi {application.user.username},\n\n"
                        "We wanted to let you know that there has been an update to your "
                        f"application for {application.job.title} at {application.job.company}.\n\n"
                        f"Current status: {application.get_status_display()}\n\n"
                    )
                    if rejection_feedback_text:
                        status_email_message += (
                            "Recruiter feedback:\n"
                            f"{rejection_feedback_text}\n\n"
                        )
                    status_email_message += (
                        "To view more details and any next steps, please log in to your "
                        "PandaPulse account. We encourage you to check your dashboard "
                        "regularly for additional updates.\n\n"
                        "Wishing you the best,\n"
                        "The PandaPulse Team\n"
                    )
                    send_mail(
                        subject=f"Application status update: {application.job.title}",
                        message=status_email_message,
                        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@pandapulse.local"),
                        recipient_list=[application.user.email],
                        fail_silently=False,
                    )
                except Exception as exc:
                    if settings.DEBUG:
                        messages.warning(request, f"Application status update email could not be sent: {exc}")
                    else:
                        messages.warning(request, "Application status update email could not be sent.")
            
            messages.success(request, f"Status updated for {application.user.username}.")
            
            return JsonResponse({"success": True, "feedback_sent": bool(rejection_feedback_text)})
        
        return JsonResponse({"success": False, "error": f"Invalid status: {new_status}"}, status=400)

    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)
    
@login_required
def employer_pipeline(request, job_id):
    """View for employers to manage applicants in a Kanban-style pipeline."""
    enforce_employer_response_deadline()
    auto_archive_old_rejections()
    job = get_object_or_404(JobPost, id=job_id, owner=request.user)
    applications = Application.objects.filter(job=job).select_related('user')
    now = timezone.now()
    applications.filter(employer_viewed=False).update(
        employer_viewed=True,
        employer_viewed_at=now,
    )
    applications = Application.objects.filter(job=job).select_related('user')
    
    pipeline = {
        'applied': applications.filter(status='applied'),
        'review': applications.filter(status='review'),
        'interview': applications.filter(status='interview'),
        'offer': applications.filter(status='offer'),
        'rejected': applications.filter(status='rejected', archived_by_employer=False),
    }
    active_count = applications.exclude(status='rejected').count()
    rejected_count = applications.filter(status='rejected', archived_by_employer=False).count()
    archived_rejected = applications.filter(
        status='rejected',
        archived_by_employer=True,
    ).order_by('-rejected_at', '-applied_at')
    
    return render(request, 'apply/employer_pipeline.html', {
        'job': job,
        'pipeline': pipeline,
        'active_count': active_count,
        'rejected_count': rejected_count,
        'archived_rejected': archived_rejected,
        'rejection_feedback_templates': _serialize_rejection_feedback_templates(),
    })


@login_required
@require_POST
def archive_application(request, application_id):
    application = get_object_or_404(Application, id=application_id, user=request.user)
    if application.status != "rejected":
        messages.warning(request, "Only rejected applications can be archived.")
        return redirect("apply:application_status")

    application.archived_by_applicant = True
    application.save(update_fields=["archived_by_applicant"])
    messages.success(request, "Application archived.")
    return redirect("apply:application_status")


@login_required
@require_POST
def archive_rejected_applicant(request, application_id):
    application = get_object_or_404(
        Application.objects.select_related("job"),
        id=application_id,
    )
    if application.job.owner != request.user:
        return HttpResponseForbidden("Unauthorized")
    if application.status != "rejected":
        messages.warning(request, "Only rejected applicants can be archived.")
        return redirect("apply:employer_pipeline", job_id=application.job.id)

    application.archived_by_employer = True
    application.save(update_fields=["archived_by_employer"])
    messages.success(request, "Rejected applicant archived.")
    return redirect("apply:employer_pipeline", job_id=application.job.id)


@login_required
@require_POST
def reject_offer(request, application_id):
    application = get_object_or_404(
        Application.objects.select_related("job", "job__owner"),
        id=application_id,
        user=request.user,
    )
    if application.status not in ("offer", "closed"):
        messages.warning(request, "You can only reject active offers.")
        return redirect("apply:application_status")

    application.status = "rejected"
    application.rejected_at = timezone.now()
    application.responded_at = timezone.now()
    application.auto_rejected_for_timeout = False
    application.rejected_offer_by_applicant = True
    application.rejection_feedback_template = ""
    application.rejection_feedback_note = ""
    application.rejection_feedback_sent_at = None
    application.archived_by_applicant = False
    application.archived_by_employer = False
    application.save(
        update_fields=[
            "status",
            "rejected_at",
            "responded_at",
            "auto_rejected_for_timeout",
            "rejected_offer_by_applicant",
            "rejection_feedback_template",
            "rejection_feedback_note",
            "rejection_feedback_sent_at",
            "archived_by_applicant",
            "archived_by_employer",
        ]
    )

    if application.job.owner and application.job.owner.email:
        try:
            send_mail(
                subject=f"Offer declined: {application.job.title}",
                message=(
                    f"{application.user.get_full_name() or application.user.username} declined the offer "
                    f"for {application.job.title} at {application.job.company}."
                ),
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@pandapulse.local"),
                recipient_list=[application.job.owner.email],
                fail_silently=True,
            )
        except Exception:
            pass

    messages.success(request, "Offer rejected. This will be reflected in the employer pipeline.")
    return redirect("apply:application_status")

@login_required
def export_applicants_csv(request, job_id):
    """Generates a CSV export of all applicants for a specific job."""
    job = get_object_or_404(JobPost, id=job_id, owner=request.user)
    applications = Application.objects.filter(job=job).select_related('user')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{job.title}_applicants.csv"'

    writer = csv.writer(response)
    writer.writerow(['Applicant Name', 'Email', 'Status', 'Applied Date', 'Note', 'Resume Type'])

    for app in applications:
        writer.writerow([
            app.user.get_full_name() or app.user.username,
            app.user.email,
            app.get_status_display(),
            app.applied_at.strftime('%Y-%m-%d %H:%M'),
            app.note,
            app.get_resume_type_display()
        ])

    return response


@login_required
def customize_offer_letter(request, application_id):
    application = get_object_or_404(
        Application.objects.select_related("job", "user", "job__owner"),
        id=application_id,
    )
    if application.job.owner != request.user:
        return HttpResponseForbidden("Unauthorized")

    if application.status not in ("offer", "closed"):
        messages.warning(request, "Move the applicant to Offer before customizing the letter.")
        return redirect("apply:employer_pipeline", job_id=application.job.id)

    _ensure_offer_defaults(application)

    if request.method == "POST":
        application.offer_letter_title = request.POST.get("offer_letter_title", "").strip()
        application.offer_letter_body = request.POST.get("offer_letter_body", "").strip()
        application.offer_compensation = request.POST.get("offer_compensation", "").strip()
        application.offer_start_date = request.POST.get("offer_start_date", "").strip()
        application.offer_response_deadline = request.POST.get("offer_response_deadline", "").strip()
        application.offer_additional_terms = request.POST.get("offer_additional_terms", "").strip()
        application.save(
            update_fields=[
                "offer_letter_title",
                "offer_letter_body",
                "offer_compensation",
                "offer_start_date",
                "offer_response_deadline",
                "offer_additional_terms",
            ]
        )

        if application.user.email:
            try:
                send_mail(
                    subject=f"Your offer details were updated: {application.job.title}",
                    message=(
                        f"Hi {application.user.username},\n\n"
                        f"{application.job.company} updated your offer details for {application.job.title}.\n"
                        "Log in to PandaPulse to review the latest offer letter.\n\n"
                        "Best,\n"
                        "PandaPulse Team"
                    ),
                    from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@pandapulse.local"),
                    recipient_list=[application.user.email],
                    fail_silently=True,
                )
            except Exception:
                pass

        messages.success(request, "Offer letter updated.")
        return redirect("apply:employer_pipeline", job_id=application.job.id)

    template_data = {
        "title": "Customize Offer Letter",
        "application": application,
        "job": application.job,
    }
    return render(request, "apply/customize_offer_letter.html", {"template_data": template_data})


@login_required
def offer_letter(request, application_id):
    application = get_object_or_404(
        Application.objects.select_related("user", "job", "job__owner"),
        id=application_id
    )

    is_applicant = application.user == request.user
    is_recruiter = application.job.owner == request.user

    # Only applicant or the job owner can view the offer letter
    if not (is_applicant or is_recruiter):
        return HttpResponseForbidden("You do not have access to this offer letter.")

    # Only visible once accepted (you said “once they get accepted”)
    # Use 'offer' as accepted stage (or include 'closed' if you later use it for “accepted/complete”).
    if application.status not in ("offer", "closed"):
        raise Http404("Offer letter not available.")

    applicant_profile, _ = Profile.objects.get_or_create(user=application.user)
    if application.job.owner:
        recruiter_profile, _ = Profile.objects.get_or_create(user=application.job.owner)
    else:
        recruiter_profile = applicant_profile

    template_data = {
        "title": "Offer Letter",
        "application": application,
        "job": application.job,
        "applicant_profile": applicant_profile,
        "recruiter_profile": recruiter_profile,
        "is_applicant": is_applicant,
        "is_recruiter": is_recruiter,
        "today": timezone.now(),
        "offer_title": application.offer_letter_title or _default_offer_letter_title(application),
        "offer_body": application.offer_letter_body or _default_offer_letter_body(application),
        "offer_compensation": application.offer_compensation or _default_offer_compensation(application),
        "offer_start_date": application.offer_start_date or "To be discussed with recruiter",
        "offer_response_deadline": application.offer_response_deadline or _default_offer_response_deadline(),
        "offer_additional_terms": application.offer_additional_terms,
    }

    return render(request, "apply/offer_letter.html", {"template_data": template_data})
