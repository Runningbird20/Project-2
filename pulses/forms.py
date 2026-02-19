from django import forms
from .models import Pulse

class PulseUploadForm(forms.ModelForm):
    class Meta:
        model = Pulse
        fields = ["video", "caption"]
        widgets = {
            "caption": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Write a caption (optional)",
                "maxlength": 220
            }),
            "video": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }

    def clean_video(self):
        f = self.cleaned_data.get("video")
        if not f:
            return f

        # Basic file-type check (simple, not perfect)
        valid = {"video/mp4", "video/webm", "video/quicktime"}
        content_type = getattr(f, "content_type", "")
        if content_type and content_type not in valid:
            raise forms.ValidationError("Upload a valid video file (mp4, webm, mov).")

        # Optional size limit (e.g., 50MB)
        max_mb = 50
        if f.size > max_mb * 1024 * 1024:
            raise forms.ValidationError(f"Video must be under {max_mb}MB.")

        return f
