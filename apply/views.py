from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from . models import Apply, Application
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json


@login_required
def job_board(request):
    jobs = Apply.objects.all()
    return render(request, "apply/job_board.html", {
        "jobs": jobs
    })

@login_required
def apply_to_job(request, job_id):
    if request.method == "POST":
        resume_choice = request.POST.get("resume_choice")
        note = request.POST.get("note", "")
        job = get_object_or_404(Apply, id=job_id)

        Application.objects.get_or_create(
            user=request.user,
            job=job,
            defaults={
                "note": note,
                "resume_type": resume_choice
            }
        )

        return redirect(job_board)

@login_required
def application_status(request):
    applications = Application.objects.filter(user=request.user).select_related("job")

    return render(request, "apply/status.html", {
        "applications": applications
    })

@require_POST
@login_required
def update_status(request, application_id):
    try:
        data = json.loads(request.body)
        new_status = data.get("status")

        application = Application.objects.get(
            id=application_id,
            user=request.user
        )

        if new_status in dict(Application.STATUS_CHOICES):
            application.status = new_status
            application.save()

            return JsonResponse({"success": True})

        return JsonResponse({"success": False}, status=400)

    except Application.DoesNotExist:
        return JsonResponse({"success": False}, status=404)


