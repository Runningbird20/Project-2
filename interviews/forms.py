from django import forms
from django.utils import timezone

from apply.models import Application


class InterviewSlotProposalForm(forms.Form):
    application = forms.ModelChoiceField(queryset=Application.objects.none(), required=True)
    start_at = forms.DateTimeField(
        required=True,
        widget=forms.DateTimeInput(attrs={"type": "datetime-local", "class": "form-control"}, format="%Y-%m-%dT%H:%M"),
        input_formats=["%Y-%m-%dT%H:%M"],
    )
    duration_minutes = forms.IntegerField(
        min_value=15,
        max_value=240,
        initial=30,
        widget=forms.NumberInput(attrs={"class": "form-control", "step": 15}),
    )
    meeting_link = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={"class": "form-control", "placeholder": "https://meet.google.com/..."}),
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 2, "placeholder": "Interview notes"}),
    )

    def __init__(self, *args, employer=None, **kwargs):
        super().__init__(*args, **kwargs)
        if employer is not None:
            self.fields["application"].queryset = (
                Application.objects.filter(job__owner=employer)
                .exclude(status__in=["rejected", "closed"])
                .select_related("job", "user")
                .order_by("-applied_at")
            )
            self.fields["application"].label_from_instance = (
                lambda app: f"{app.user.username} - {app.job.title} ({app.get_status_display()})"
            )
        self.fields["application"].widget.attrs.update({"class": "form-select"})

    def clean_start_at(self):
        start_at = self.cleaned_data["start_at"]
        if timezone.is_naive(start_at):
            start_at = timezone.make_aware(start_at, timezone.get_current_timezone())
        if start_at <= timezone.now():
            raise forms.ValidationError("Interview time must be in the future.")
        return start_at
