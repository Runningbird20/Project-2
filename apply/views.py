from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Application
from jobposts.models import JobPost # Make sure this matches your jobposts app model
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json

@login_required
def submit_application(request, job_id):
    if request.method == "POST":
        # 1. Get the job object from the jobposts app
        job = get_object_or_404(JobPost, id=job_id)
        
        # 2. Get form data
        note = request.POST.get("note", "")
        resume_type = request.POST.get("resume_type") # 'profile' or 'uploaded'
        resume_file = request.FILES.get("resume_file") # The actual file

        # 3. Check if user already applied to avoid duplicates
        if Application.objects.filter(user=request.user, job=job).exists():
            messages.warning(request, f"You have already applied for {job.title}.")
            return redirect('jobposts.search')

        # 4. Create the application
        Application.objects.create(
            user=request.user,
            job=job,
            note=note,
            resume_type=resume_type,
            # We only save the file if they chose 'uploaded'
            resume_file=resume_file if resume_type == 'uploaded' else None
        )

        messages.success(request, f"Application for {job.title} submitted successfully!")
        return redirect('jobposts.search')

    return redirect('jobposts.search')

@login_required
def application_status(request):
    applications = Application.objects.filter(user=request.user).select_related("job")
    return render(request, "apply/status.html", {"applications": applications})

@require_POST
@login_required
def update_status(request, application_id):
    try:
        data = json.loads(request.body)
        new_status = data.get("status")
        application = Application.objects.get(id=application_id, user=request.user)

        if new_status in dict(Application.STATUS_CHOICES):
            application.status = new_status
            application.save()
            return JsonResponse({"success": True})
        return JsonResponse({"success": False}, status=400)
    except Application.DoesNotExist:
        return JsonResponse({"success": False}, status=404)