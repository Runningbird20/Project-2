from django import forms

from .models import JobPost


class JobPostForm(forms.ModelForm):
    class Meta:
        model = JobPost
        fields = ['title', 'company', 'location', 'pay_range', 'description']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'e.g. Backend Engineer'}),
            'company': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Acme Inc'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Remote or Atlanta, GA'}),
            'pay_range': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. $70k-$90k'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Role overview, responsibilities, requirements...'}),
        }
