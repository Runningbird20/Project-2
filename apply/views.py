from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.core.mail import send_mail
from .models import Application
from jobposts.models import JobPost
from jobposts.models import ApplicantJobMatch
from jobposts.matching import sync_applicant_job_matches
from django.http import JsonResponse, HttpResponseForbidden, HttpResponse, Http404
from django.views.decorators.http import require_POST
import json
import csv
from django.utils import timezone
from accounts.models import Profile
from .services import (
    auto_archive_old_rejections,
    enforce_employer_response_deadline,
    calculate_application_streak,
)
from interviews.services import get_applicant_interview_context

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

    activity_events.sort(key=lambda item: item["timestamp"], reverse=True)
    activity_events = activity_events[:3]

    matched_jobs = (
        ApplicantJobMatch.objects.filter(applicant=request.user)
        .select_related("job")
        .order_by("-score", "-updated_at")
    )
    interview_context = get_applicant_interview_context(
        request.user,
        month_key=request.GET.get("interview_month"),
    )
    return render(
        request,
        "apply/status.html",
        {
            "applications": active_applications,
            "archived_applications": archived_applications,
            "matched_jobs": matched_jobs,
            "activity_events": activity_events,
            "application_streak": calculate_application_streak(request.user),
            **interview_context,
        },
    )

@login_required
@require_POST
def update_status(request, application_id):
    try:
        data = json.loads(request.body)
        new_status = data.get("status")
        
        application = get_object_or_404(Application, id=application_id)

        if application.job.owner != request.user:
            return JsonResponse({"success": False, "error": "Unauthorized"}, status=403)

        valid_statuses = [choice[0] for choice in Application.STATUS_CHOICES]
        
        if new_status in valid_statuses:
            application.status = new_status
            application.responded_at = timezone.now()
            if new_status == "rejected":
                application.rejected_at = timezone.now()
                application.auto_rejected_for_timeout = False
            else:
                application.rejected_at = None
                application.archived_by_applicant = False
                application.archived_by_employer = False
                application.auto_rejected_for_timeout = False
            application.save()

            if application.user.email:
                try:
                    send_mail(
                        subject=f"Application status update: {application.job.title}",
                        message=(
                            f"Hi {application.user.username},\n\n"
                            "We wanted to let you know that there has been an update to your "
                            f"application for {application.job.title} at {application.job.company}.\n\n"
                            f"Current status: {application.get_status_display()}\n\n"
                            "To view more details and any next steps, please log in to your "
                            "PandaPulse account. We encourage you to check your dashboard "
                            "regularly for additional updates.\n\n"
                            "Wishing you the best,\n"
                            "The PandaPulse Team\n"
                        ),
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
            
            return JsonResponse({"success": True})
        
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
    recruiter_profile, _ = Profile.objects.get_or_create(user=application.job.owner)

    template_data = {
        "title": "Offer Letter",
        "application": application,
        "job": application.job,
        "applicant_profile": applicant_profile,
        "recruiter_profile": recruiter_profile,
        "is_applicant": is_applicant,
        "is_recruiter": is_recruiter,
        "today": timezone.now(),
    }

    return render(request, "apply/offer_letter.html", {"template_data": template_data})
