from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from . models import Apply, Application

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


