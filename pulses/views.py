from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .models import Pulse
from .forms import PulseUploadForm

@login_required
def pulses_feed(request):
    pulses = Pulse.objects.select_related("user", "user__profile").all()
    template_data = {
        "title": "Pulses",
        "pulses": pulses,
    }
    return render(request, "pulses/feed.html", {"template_data": template_data})

@login_required
def upload_pulse(request):
    template_data = {"title": "Upload Pulse"}

    if request.method == "GET":
        template_data["form"] = PulseUploadForm()
        return render(request, "pulses/upload.html", {"template_data": template_data})

    form = PulseUploadForm(request.POST, request.FILES)
    template_data["form"] = form

    if not form.is_valid():
        return render(request, "pulses/upload.html", {"template_data": template_data})

    pulse = form.save(commit=False)
    pulse.user = request.user
    pulse.save()

    messages.success(request, "Pulse uploaded!")
    return redirect("pulses:feed")

@login_required
def delete_pulse(request, pulse_id):
    """
    Deletes a reel if the user is the owner or a staff member.
    """
    if request.method == "POST":
        pulse = get_object_or_404(Pulse, id=pulse_id)

        if pulse.user == request.user or request.user.is_staff:
            if pulse.video:
                pulse.video.delete(save=False)

            pulse.delete()
            messages.success(request, "Reel deleted.")
        else:
            messages.error(request, "You don't have permission to do that.")

    return redirect("pulses:feed")
