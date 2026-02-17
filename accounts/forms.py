from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.forms.utils import ErrorList
from django.utils.safestring import mark_safe

from .models import Profile

class CustomErrorList(ErrorList):
    def __str__(self):
        if not self:
            return ''
        return mark_safe(''.join([f'<div class="alert alert-danger" role="alert">{e}</div>' for e in self]))

class CustomUserCreationForm(UserCreationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for fieldname in ['username', 'password1', 'password2']:
            self.fields[fieldname].help_text = None
            self.fields[fieldname].widget.attrs.update({'class': 'form-control'})

class SignupWithProfileForm(CustomUserCreationForm):
    profile_picture = forms.ImageField(required=False)

    account_type = forms.ChoiceField(
        choices=Profile.AccountType.choices,
        required=True,
        widget=forms.Select(attrs={"class": "form-control"}),
        label="I am signing up as",
    )

    headline = forms.CharField(
        max_length=120,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    skills = forms.CharField(
        max_length=300,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    location = forms.CharField(
        max_length=120,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    projects = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 4}),
    )
    education = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
    )
    work_experience = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
    )

    company_name = forms.CharField(
        max_length=120,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    company_website = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={"class": "form-control"}),
    )
    company_description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
    )

    def clean(self):
        cleaned = super().clean()
        acct = cleaned.get("account_type")
        if acct == Profile.AccountType.EMPLOYER and not cleaned.get("company_name"):
            self.add_error("company_name", "Company name is required for employers.")
        return cleaned

class ProfileEditForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Backward-compatible: allow posts that omit account_type and keep current value.
        self.fields["account_type"].required = False

    link_0_label = forms.CharField(
        required=False, 
        label="Link 1 Label",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. GitHub'})
    )
    link_0_url = forms.URLField(
        required=False, 
        label="Link 1 URL",
        widget=forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://github.com/user'})
    )
    link_1_label = forms.CharField(
        required=False, 
        label="Link 2 Label",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Portfolio'})
    )
    link_1_url = forms.URLField(
        required=False, 
        label="Link 2 URL",
        widget=forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://myportfolio.com'})
    )

    class Meta:
        model = Profile
        fields = [
<<<<<<< HEAD
=======
            "profile_picture",
>>>>>>> 4c996b028ab039e2ece29bac8e189950cc13238b
            "account_type",
            "headline",
            "skills",
            "location",
            "projects",
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
            "profile_picture": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "account_type": forms.Select(attrs={"class": "form-control"}),
            "headline": forms.TextInput(attrs={"class": "form-control"}),
            "skills": forms.TextInput(attrs={"class": "form-control"}),
            "location": forms.TextInput(attrs={"class": "form-control"}),
            "projects": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "education": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "work_experience": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
<<<<<<< HEAD

            "company_name": forms.TextInput(attrs={"class": "form-control"}),
            "company_website": forms.URLInput(attrs={"class": "form-control"}),
            "company_description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),

=======
            "company_name": forms.TextInput(attrs={"class": "form-control"}),
            "company_website": forms.URLInput(attrs={"class": "form-control"}),
            "company_description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
>>>>>>> 4c996b028ab039e2ece29bac8e189950cc13238b
            "visible_to_recruiters": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "show_headline": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "show_skills": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "show_education": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "show_work_experience": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "show_links": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
        labels = {
            "profile_picture": "Profile picture",
            "account_type": "Account type",
            "visible_to_recruiters": "Visible to recruiters",
            "show_headline": "Show headline",
            "show_skills": "Show skills",
            "show_education": "Show education",
            "show_work_experience": "Show work experience",
            "show_links": "Show links",
<<<<<<< HEAD
=======
            "company_name": "Company Name",
            "company_website": "Company Website",
            "company_description": "Company Description",
>>>>>>> 4c996b028ab039e2ece29bac8e189950cc13238b
        }

    def clean(self):
        cleaned = super().clean()
        acct = cleaned.get("account_type")

        if not acct and self.instance and self.instance.pk:
            acct = self.instance.account_type
            cleaned["account_type"] = acct
        if acct == Profile.AccountType.EMPLOYER and not cleaned.get("company_name"):
            self.add_error("company_name", "Company name is required for employers.")
        return cleaned
