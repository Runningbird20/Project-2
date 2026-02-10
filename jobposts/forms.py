from django import forms

from .models import JobPost


class JobPostForm(forms.ModelForm):
    class Meta:
        model = JobPost
        fields = ['title', 'company', 'location', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }
