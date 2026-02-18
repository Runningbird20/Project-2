from django import forms

from .models import JobPost


class JobPostForm(forms.ModelForm):
    def clean(self):
        cleaned_data = super().clean()
        salary_min = cleaned_data.get('salary_min')
        salary_max = cleaned_data.get('salary_max')

        if salary_min is None:
            self.add_error('salary_min', 'Minimum salary is required.')
        if salary_max is None:
            self.add_error('salary_max', 'Maximum salary is required.')

        if salary_min is not None and salary_max is not None and salary_max < salary_min:
            self.add_error('salary_max', 'Maximum salary must be greater than or equal to minimum salary.')

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if instance.salary_min is not None and instance.salary_max is not None:
            instance.pay_range = f'${instance.salary_min:,}-${instance.salary_max:,}'
        if commit:
            instance.save()
        return instance

    class Meta:
        model = JobPost
        fields = [
            'title',
            'company',
            'company_size',
            'location',
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
            'company_size': forms.Select(attrs={'class': 'form-select'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Remote or Atlanta, GA'}),
            'salary_min': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '70000', 'min': '0', 'step': '1'}),
            'salary_max': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '90000', 'min': '0', 'step': '1'}),
            'work_setting': forms.Select(attrs={'class': 'form-select'}),
            'visa_sponsorship': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'skills': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Python, Django, AWS'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Role overview, responsibilities, requirements...'}),
        }
