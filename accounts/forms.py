from django.contrib.auth.forms import UserCreationForm
from django.forms.utils import ErrorList
from django.utils.safestring import mark_safe
from django import forms
from .models import Profile


class CustomErrorList(ErrorList):
    def __str__(self):
        if not self:
            return ''
        return mark_safe(''.join([f'<div class="alert alert-danger" role="alert">{e}</div>' for e in self]))


class CustomUserCreationForm(UserCreationForm):
    def __init__(self, *args, **kwargs):
        super(CustomUserCreationForm, self).__init__(*args, **kwargs)
        for fieldname in ['username', 'password1', 'password2']:
            self.fields[fieldname].help_text = None
            self.fields[fieldname].widget.attrs.update({'class': 'form-control'})


class SignupWithProfileForm(CustomUserCreationForm):
    headline = forms.CharField(
        max_length=120,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label="Headline"
    )
    skills = forms.CharField(
        max_length=300,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label="Skills",
        help_text="Comma-separated, e.g. Python, Django, SQL"
    )
    education = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        label="Education"
    )
    work_experience = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        label="Work Experience"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class ProfileEditForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = [
            "headline",
            "skills",
            "education",
            "work_experience",
            "visible_to_recruiters",
            "show_headline",
            "show_skills",
            "show_education",
            "show_work_experience",
            "show_links",
        ]
        widgets = {
            "headline": forms.TextInput(attrs={"class": "form-control"}),
            "skills": forms.TextInput(attrs={"class": "form-control"}),
            "education": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "work_experience": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "visible_to_recruiters": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "show_headline": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "show_skills": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "show_education": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "show_work_experience": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "show_links": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
        labels = {
            "visible_to_recruiters": "Visible to recruiters",
            "show_headline": "Show headline",
            "show_skills": "Show skills",
            "show_education": "Show education",
            "show_work_experience": "Show work experience",
            "show_links": "Show links",
        }

