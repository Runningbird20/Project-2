from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Application
from jobposts.models import JobPost
from django.http import JsonResponse, HttpResponseForbidden, HttpResponse, Http404
from django.views.decorators.http import require_POST
import json
import csv
from django.utils import timezone
from accounts.models import Profile
from .services import auto_archive_old_rejections, enforce_employer_response_deadline

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

    Application.objects.create(
        user=request.user,
        job=job,
        note=note,
        resume_type=resume_type,
        resume_file=resume_file if resume_type == "uploaded" else None,
    )

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
    active_applications = Application.objects.filter(
        user=request.user,
        archived_by_applicant=False,
    ).select_related("job")
    archived_applications = Application.objects.filter(
        user=request.user,
        archived_by_applicant=True,
    ).select_related("job")
    return render(
        request,
        "apply/status.html",
        {
            "applications": active_applications,
            "archived_applications": archived_applications,
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
