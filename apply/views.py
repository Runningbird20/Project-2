from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Application
from jobposts.models import JobPost
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json
import csv
from django.http import HttpResponse

@login_required
def submit_application(request, job_id):
    if request.method == "POST":
        job = get_object_or_404(JobPost, id=job_id)
        
        note = request.POST.get("note", "")
        resume_type = request.POST.get("resume_type") 
        resume_file = request.FILES.get("resume_file")

        if Application.objects.filter(user=request.user, job=job).exists():
            messages.warning(request, f"You have already applied for {job.title}.")
            return redirect('jobposts.search')

        Application.objects.create(
            user=request.user,
            job=job,
            note=note,
            resume_type=resume_type,
            resume_file=resume_file if resume_type == 'uploaded' else None
        )

        messages.success(request, f"Application for {job.title} submitted successfully!")
        return redirect('jobposts.search')

    return redirect('jobposts.search')

@login_required
def application_status(request):
    """View for applicants to see the status of their own applications."""
    applications = Application.objects.filter(user=request.user).select_related("job")
    return render(request, "apply/status.html", {"applications": applications})

@require_POST
@login_required
def update_status(request, application_id):
    """
    AJAX view to update application status. 
    Accessible by the Applicant (for tracking) and the Employer (via Kanban).
    """
    try:
        data = json.loads(request.body)
        new_status = data.get("status")
        
        application = get_object_or_404(Application, id=application_id)

        is_applicant = (application.user == request.user)
        is_employer = (application.job.owner == request.user)

        if not (is_applicant or is_employer):
            return JsonResponse({"success": False, "error": "Unauthorized"}, status=403)

        if new_status in dict(Application.STATUS_CHOICES):
            application.status = new_status
            application.save()
            return JsonResponse({"success": True})
        
        return JsonResponse({"success": False}, status=400)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)

@login_required
def employer_pipeline(request, job_id):
    """View for employers to manage applicants in a Kanban-style pipeline."""
    job = get_object_or_404(JobPost, id=job_id, owner=request.user)
    applications = Application.objects.filter(job=job).select_related('user')
    
    pipeline = {
        'applied': applications.filter(status='applied'),
        'review': applications.filter(status='review'),
        'interview': applications.filter(status='interview'),
        'offer': applications.filter(status='offer'),
        'rejected': applications.filter(status='rejected'),
    }
    
    return render(request, 'apply/employer_pipeline.html', {
        'job': job,
        'pipeline': pipeline
    })

@login_required
def export_applicants_csv(request, job_id):
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