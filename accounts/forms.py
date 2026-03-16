import re

from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.forms.utils import ErrorList
from django.utils.safestring import mark_safe

from .models import Profile
from project2.skills import normalize_skills_csv

ZIP_CITY_STATE_OVERRIDES = {
    "02108": ("Boston", "MA"),
    "10001": ("New York", "NY"),
    "10018": ("New York", "NY"),
    "27601": ("Raleigh", "NC"),
    "28202": ("Charlotte", "NC"),
    "30303": ("Atlanta", "GA"),
    "30308": ("Atlanta", "GA"),
    "33101": ("Miami", "FL"),
    "37203": ("Nashville", "TN"),
    "55401": ("Minneapolis", "MN"),
    "60601": ("Chicago", "IL"),
    "78701": ("Austin", "TX"),
    "78704": ("Austin", "TX"),
    "80202": ("Denver", "CO"),
    "84101": ("Salt Lake City", "UT"),
    "85004": ("Phoenix", "AZ"),
    "90012": ("Los Angeles", "CA"),
    "92101": ("San Diego", "CA"),
    "94103": ("San Francisco", "CA"),
    "97204": ("Portland", "OR"),
    "98101": ("Seattle", "WA"),
    "98104": ("Seattle", "WA"),
}


def _normalize_us_postal_code(raw_postal):
    postal = (raw_postal or "").strip()
    if not postal:
        return ""
    match = re.match(r"^(\d{5})(?:[-\s]?(\d{4}))?$", postal)
    if not match:
        return postal
    base = match.group(1)
    suffix = match.group(2)
    if suffix:
        return f"{base}-{suffix}"
    return base


def _split_state_and_postal(raw_region):
    region = (raw_region or "").strip()
    if not region:
        return "", ""
    match = re.match(r"^([A-Za-z]{2})(?:\s+(\d{5}(?:-\d{4})?))?$", region)
    if match:
        return match.group(1).upper(), (match.group(2) or "")
    pieces = region.split()
    if len(pieces) >= 2 and pieces[-1].isdigit():
        return " ".join(pieces[:-1]), pieces[-1]
    return region, ""


def _parse_location_parts(raw_location):
    parts = [part.strip() for part in (raw_location or "").split(",") if part.strip()]
    parsed = {
        "address_line_1": "",
        "address_line_2": "",
        "city": "",
        "state": "",
        "postal_code": "",
        "country": "United States",
    }
    if not parts:
        return parsed

    parsed["address_line_1"] = parts[0]

    if len(parts) == 1:
        return parsed
    if len(parts) == 2:
        parsed["city"] = parts[1]
        return parsed

    last_part = parts[-1]
    has_explicit_country = not any(ch.isdigit() for ch in last_part) and len(last_part) > 2
    if has_explicit_country and len(parts) >= 4:
        parsed["country"] = last_part
        parsed["city"] = parts[-3]
        state, postal = _split_state_and_postal(parts[-2])
        parsed["state"] = state
        parsed["postal_code"] = postal
        middle = parts[1:-3]
    else:
        parsed["city"] = parts[-2]
        state, postal = _split_state_and_postal(parts[-1])
        parsed["state"] = state
        parsed["postal_code"] = postal
        middle = parts[1:-2]

    if middle:
        parsed["address_line_2"] = ", ".join(middle)
    return parsed


class ApplicantAddressFieldsMixin:
    def _build_applicant_location(self, require_full):
        address_line_1 = (self.cleaned_data.get("address_line_1") or "").strip()
        address_line_2 = (self.cleaned_data.get("address_line_2") or "").strip()
        city = (self.cleaned_data.get("city") or "").strip()
        state = (self.cleaned_data.get("state") or "").strip()
        postal_code = _normalize_us_postal_code(self.cleaned_data.get("postal_code"))
        country = (self.cleaned_data.get("country") or "").strip()
        zip5_match = re.match(r"^(\d{5})", postal_code)
        zip5 = zip5_match.group(1) if zip5_match else ""
        mapped_city_state = ZIP_CITY_STATE_OVERRIDES.get(zip5)
        if mapped_city_state:
            city, state = mapped_city_state
        elif len(state) == 2:
            state = state.upper()

        has_any = any([address_line_1, address_line_2, city, state, postal_code, country])
        if require_full and not any([address_line_1, city, state, postal_code]):
            self.add_error("address_line_1", "Address is required for applicants.")
            self.add_error("city", "City is required for applicants.")
            self.add_error("state", "State is required for applicants.")
            self.add_error("postal_code", "ZIP is required for applicants.")
            return ""

        if has_any:
            required_fields = {
                "address_line_1": address_line_1,
                "city": city,
                "state": state,
                "postal_code": postal_code,
            }
            for field_name, value in required_fields.items():
                if not value:
                    self.add_error(field_name, "This field is required.")
            if any(self.errors.get(field_name) for field_name in required_fields):
                return ""

            if not country:
                country = "United States"

            self.cleaned_data["city"] = city
            self.cleaned_data["state"] = state
            self.cleaned_data["postal_code"] = postal_code
            self.cleaned_data["country"] = country

            parts = [address_line_1]
            if address_line_2:
                parts.append(address_line_2)
            parts.append(city)
            parts.append(f"{state} {postal_code}".strip())
            parts.append(country)
            return ", ".join(parts)
        return ""

class CustomErrorList(ErrorList):
    def __str__(self):
        if not self:
            return ''
        return mark_safe(''.join([f'<div class="alert alert-danger" role="alert">{e}</div>' for e in self]))

class CustomUserCreationForm(UserCreationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].help_text = None
        self.fields["password1"].help_text = password_validation.password_validators_help_text_html()
        self.fields["password2"].help_text = None
        for fieldname in ['username', 'password1', 'password2']:
            self.fields[fieldname].widget.attrs.update({'class': 'form-control'})

class SignupWithProfileForm(ApplicantAddressFieldsMixin, CustomUserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={"class": "form-control", "autocomplete": "email"}),
    )
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
    address_line_1 = forms.CharField(
        max_length=255,
        required=False,
        label="Address Line 1",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "e.g. 75 5th St NW",
            }
        ),
    )
    address_line_2 = forms.CharField(
        max_length=255,
        required=False,
        label="Address Line 2",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Suite, floor, unit (optional)",
            }
        ),
    )
    city = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "e.g. Atlanta",
            }
        ),
    )
    state = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "e.g. GA",
            }
        ),
    )
    postal_code = forms.CharField(
        max_length=20,
        required=False,
        label="ZIP",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "e.g. 30308",
            }
        ),
    )
    country = forms.CharField(
        max_length=100,
        required=False,
        initial="United States",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "e.g. United States",
            }
        ),
    )
    location = forms.CharField(
        max_length=255,
        required=False,
        label="Company Address",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "123 Peachtree St NE, Atlanta, GA 30303, United States",
            }
        ),
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["country"].initial = "United States"
        if self.is_bound:
            return
        parsed = _parse_location_parts(self.initial.get("location", ""))
        for key in ["address_line_1", "address_line_2", "city", "state", "postal_code", "country"]:
            if parsed.get(key):
                self.fields[key].initial = parsed[key]

    def clean(self):
        cleaned = super().clean()
        acct = cleaned.get("account_type")
        if acct == Profile.AccountType.EMPLOYER and not cleaned.get("company_name"):
            self.add_error("company_name", "Company name is required for employers.")
        if acct == Profile.AccountType.APPLICANT:
            cleaned["location"] = self._build_applicant_location(require_full=True)
        elif acct == Profile.AccountType.EMPLOYER:
            cleaned["location"] = self._build_applicant_location(require_full=False)
        return cleaned

    def clean_username(self):
        username = (self.cleaned_data.get("username") or "").strip()
        if not username:
            return username

        User = get_user_model()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("This username is already taken.")
        return username

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip()
        if not email:
            raise forms.ValidationError("Email is required.")
        User = get_user_model()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean_skills(self):
        return normalize_skills_csv(self.cleaned_data.get("skills", ""))

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip()
        if not email:
            return email

        User = get_user_model()
        existing = User.objects.filter(email__iexact=email)
        if self.instance and self.instance.pk:
            existing = existing.exclude(pk=self.instance.user_id)
        if existing.exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

class ProfileEditForm(ApplicantAddressFieldsMixin, forms.ModelForm):
    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        # Backward-compatible: allow posts that omit account_type and keep current value.
        self.fields["account_type"].required = False
        if user is None and self.instance and self.instance.pk:
            user = self.instance.user
        if user:
            self.fields["email"].initial = user.email
        self.fields["country"].initial = "United States"
        if self.instance and self.instance.pk and not self.is_bound:
            self.initial["skills"] = normalize_skills_csv(self.instance.skills)
            if any(
                [
                    self.instance.address_line_1,
                    self.instance.address_line_2,
                    self.instance.city,
                    self.instance.state,
                    self.instance.postal_code,
                    self.instance.country,
                ]
            ):
                self.fields["address_line_1"].initial = self.instance.address_line_1
                self.fields["address_line_2"].initial = self.instance.address_line_2
                self.fields["city"].initial = self.instance.city
                self.fields["state"].initial = self.instance.state
                self.fields["postal_code"].initial = self.instance.postal_code
                self.fields["country"].initial = self.instance.country or "United States"
            else:
                parsed = _parse_location_parts(self.instance.location)
                for key in ["address_line_1", "address_line_2", "city", "state", "postal_code", "country"]:
                    if parsed.get(key):
                        self.fields[key].initial = parsed[key]

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
    email = forms.EmailField(
        required=False,
        label="Email",
        widget=forms.EmailInput(
            attrs={"class": "form-control", "autocomplete": "email"}
        ),
    )
    address_line_1 = forms.CharField(
        max_length=255,
        required=False,
        label="Address Line 1",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "e.g. 75 5th St NW",
            }
        ),
    )
    address_line_2 = forms.CharField(
        max_length=255,
        required=False,
        label="Address Line 2",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Suite, floor, unit (optional)",
            }
        ),
    )
    city = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "e.g. Atlanta",
            }
        ),
    )
    state = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "e.g. GA",
            }
        ),
    )
    postal_code = forms.CharField(
        max_length=20,
        required=False,
        label="ZIP",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "e.g. 30308",
            }
        ),
    )
    country = forms.CharField(
        max_length=100,
        required=False,
        initial="United States",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "e.g. United States",
            }
        ),
    )

    class Meta:
        model = Profile
        fields = [
            "profile_picture",
            "resume_file",
            "account_type",
            "headline",
            "skills",
            "location",
            "address_line_1",
            "address_line_2",
            "city",
            "state",
            "postal_code",
            "country",
            "projects",
            "education",
            "work_experience",
            "visible_to_recruiters",
            "show_headline",
            "show_skills",
            "show_education",
            "show_work_experience",
            "show_links",
            "hide_email_from_employers",
        ]
        widgets = {
            "profile_picture": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "resume_file": forms.FileInput(
                attrs={
                    "class": "form-control",
                    "accept": ".pdf",
                }
            ),
            "account_type": forms.Select(attrs={"class": "form-control"}),
            "headline": forms.TextInput(attrs={"class": "form-control"}),
            "skills": forms.TextInput(attrs={"class": "form-control"}),
            "location": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "123 Peachtree St NE, Atlanta, GA 30303, United States",
                }
            ),
            "projects": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "education": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "work_experience": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "visible_to_recruiters": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "show_headline": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "show_skills": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "show_education": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "show_work_experience": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "show_links": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "hide_email_from_employers": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
        labels = {
            "profile_picture": "Profile picture",
            "resume_file": "Profile resume",
            "account_type": "Account type",
            "visible_to_recruiters": "Visible to recruiters",
            "show_headline": "Show headline",
            "show_skills": "Show skills",
            "show_education": "Show education",
            "show_work_experience": "Show work experience",
            "show_links": "Show links",
            "hide_email_from_employers": "Hide email from employers",
            "location": "Company Address",
        }

    def clean(self):
        cleaned = super().clean()
        acct = cleaned.get("account_type")

        if not acct and self.instance and self.instance.pk:
            acct = self.instance.account_type
            cleaned["account_type"] = acct
        if acct == Profile.AccountType.APPLICANT:
            cleaned["location"] = self._build_applicant_location(require_full=False)
        elif acct == Profile.AccountType.EMPLOYER:
            # Employer HQ is managed in Company Profile, not Profile Edit.
            # Keep existing values so account updates here do not clear HQ fields.
            cleaned["location"] = (self.instance.location or "")
            cleaned["address_line_1"] = (self.instance.address_line_1 or "")
            cleaned["address_line_2"] = (self.instance.address_line_2 or "")
            cleaned["city"] = (self.instance.city or "")
            cleaned["state"] = (self.instance.state or "")
            cleaned["postal_code"] = (self.instance.postal_code or "")
            cleaned["country"] = (self.instance.country or "United States")
        return cleaned

    def clean_skills(self):
        return normalize_skills_csv(self.cleaned_data.get("skills", ""))

    def clean_resume_file(self):
        resume_file = self.cleaned_data.get("resume_file")
        if not resume_file:
            return resume_file

        file_name = (getattr(resume_file, "name", "") or "").strip().lower()
        if not file_name.endswith(".pdf"):
            raise forms.ValidationError("Upload a PDF resume.")
        return resume_file


class CompanyProfileForm(ApplicantAddressFieldsMixin, forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["company_name"].required = True
        self.fields["company_name"].widget.attrs["required"] = True
        self.fields["company_name"].error_messages["required"] = "Company name is required for employers."
        self.fields["country"].initial = "United States"
        if self.instance and self.instance.pk and not self.is_bound:
            if any(
                [
                    self.instance.address_line_1,
                    self.instance.address_line_2,
                    self.instance.city,
                    self.instance.state,
                    self.instance.postal_code,
                    self.instance.country,
                ]
            ):
                self.fields["address_line_1"].initial = self.instance.address_line_1
                self.fields["address_line_2"].initial = self.instance.address_line_2
                self.fields["city"].initial = self.instance.city
                self.fields["state"].initial = self.instance.state
                self.fields["postal_code"].initial = self.instance.postal_code
                self.fields["country"].initial = self.instance.country or "United States"
            else:
                parsed = _parse_location_parts(self.instance.location)
                for key in ["address_line_1", "address_line_2", "city", "state", "postal_code", "country"]:
                    if parsed.get(key):
                        self.fields[key].initial = parsed[key]

    class Meta:
        model = Profile
        fields = [
            "company_name",
            "company_website",
            "company_description",
            "company_culture",
            "company_perks",
            "address_line_1",
            "address_line_2",
            "city",
            "state",
            "postal_code",
            "country",
        ]
        widgets = {
            "company_name": forms.TextInput(attrs={"class": "form-control"}),
            "company_website": forms.URLInput(attrs={"class": "form-control"}),
            "company_description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "company_culture": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "company_perks": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "One perk per line (e.g. 401k match, stipend, PTO)",
                }
            ),
            "address_line_1": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. 75 5th St NW",
                }
            ),
            "address_line_2": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Suite, floor, unit (optional)",
                }
            ),
            "city": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. Atlanta",
                }
            ),
            "state": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. GA",
                }
            ),
            "postal_code": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. 30308",
                }
            ),
            "country": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. United States",
                }
            ),
        }
        labels = {
            "company_name": "Company Name",
            "company_website": "Company Website",
            "company_description": "Company Description",
            "company_culture": "Company Culture",
            "company_perks": "Perks",
            "address_line_1": "Address Line 1",
            "address_line_2": "Address Line 2",
            "city": "City",
            "state": "State",
            "postal_code": "ZIP",
            "country": "Country",
        }

    def clean_company_name(self):
        value = (self.cleaned_data.get("company_name") or "").strip()
        if not value:
            raise forms.ValidationError("Company name is required for employers.")
        return value

    def clean(self):
        cleaned = super().clean()
        address_line_1 = (cleaned.get("address_line_1") or "").strip()
        address_line_2 = (cleaned.get("address_line_2") or "").strip()
        city = (cleaned.get("city") or "").strip()
        state = (cleaned.get("state") or "").strip()
        postal_code = (cleaned.get("postal_code") or "").strip()
        country = (cleaned.get("country") or "").strip()

        # HQ is optional for company profile. If only default country is present,
        # treat HQ as empty instead of forcing all fields.
        if not any([address_line_1, address_line_2, city, state, postal_code]) and country.lower() in {"", "united states"}:
            cleaned["country"] = ""

        cleaned["location"] = self._build_applicant_location(require_full=False)
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.location = self.cleaned_data.get("location", "")
        if commit:
            instance.save()
        return instance
