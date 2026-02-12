from django import forms

from .models import JobPost


class JobPostForm(forms.ModelForm):
    class Meta:
        model = JobPost
        fields = [
            'title',
            'company',
            'location',
            'pay_range',
            'salary_min',
            'salary_max',
            'work_setting',
            'visa_sponsorship',
            'skills',
            'description',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'e.g. Backend Engineer'}),
            'company': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Acme Inc'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Remote or Atlanta, GA'}),
            'pay_range': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. $70k-$90k'}),
            'salary_min': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 70000'}),
            'salary_max': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 90000'}),
            'work_setting': forms.Select(attrs={'class': 'form-select'}),
            'visa_sponsorship': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'skills': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Python, Django, AWS'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Role overview, responsibilities, requirements...'}),
        }
