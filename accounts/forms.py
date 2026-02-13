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
    account_type = forms.ChoiceField(
        choices=Profile.AccountType.choices,
        required=True,
        widget=forms.Select(attrs={"class": "form-control"}),
        label="I am signing up as"
    )

    # Applicant fields
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
        label="Skills"
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

    # Employer fields
    company_name = forms.CharField(
        max_length=120,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
        label="Company Name"
    )
    company_website = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={"class": "form-control"}),
        label="Company Website"
    )
    company_description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        label="Company Description"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Optional: remove Django's default password help text if it appears
        if "password1" in self.fields:
            self.fields["password1"].help_text = None
        if "password2" in self.fields:
            self.fields["password2"].help_text = None

    def clean(self):
        cleaned = super().clean()
        acct = cleaned.get("account_type")

        if acct == Profile.AccountType.EMPLOYER:
            if not cleaned.get("company_name"):
                self.add_error("company_name", "Company name is required for employers.")

        return cleaned

class ProfileEditForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = [
            "account_type",
            "headline",
            "skills",
            "education",
            "work_experience",
            "company_name",
            "company_website",
            "company_description",
            "visible_to_recruiters",
            "show_headline",
            "show_skills",
            "show_education",
            "show_work_experience",
            "show_links",
        ]
        widgets = {
            "account_type": forms.Select(attrs={"class": "form-control"}),

            "headline": forms.TextInput(attrs={"class": "form-control"}),
            "skills": forms.TextInput(attrs={"class": "form-control"}),
            "education": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "work_experience": forms.Textarea(attrs={"class": "form-control", "rows": 4}),

            "company_name": forms.TextInput(attrs={"class": "form-control"}),
            "company_website": forms.URLInput(attrs={"class": "form-control"}),
            "company_description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),

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

    def clean(self):
        cleaned = super().clean()
        acct = cleaned.get("account_type")

        if acct == Profile.AccountType.EMPLOYER:
            if not cleaned.get("company_name"):
                self.add_error("company_name", "Company name is required for employers.")

        return cleaned


