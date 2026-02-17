from django import forms

from .models import OfficeLocation


class OfficeLocationForm(forms.ModelForm):
    class Meta:
        model = OfficeLocation
        fields = [
            'address_line_1',
            'address_line_2',
            'city',
            'state',
            'postal_code',
            'country',
        ]
        widgets = {
            'address_line_1': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'e.g. 75 5th St NW',
                }
            ),
            'address_line_2': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Suite, floor, unit (optional)',
                }
            ),
            'city': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'e.g. Atlanta',
                }
            ),
            'state': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'e.g. GA',
                }
            ),
            'postal_code': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'e.g. 30308',
                }
            ),
            'country': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'e.g. United States',
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['country'].initial = 'United States'
        self.has_location_data = False

    def clean(self):
        cleaned_data = super().clean()
        line_1 = (cleaned_data.get('address_line_1') or '').strip()
        line_2 = (cleaned_data.get('address_line_2') or '').strip()
        city = (cleaned_data.get('city') or '').strip()
        state = (cleaned_data.get('state') or '').strip()
        postal_code = (cleaned_data.get('postal_code') or '').strip()
        country = (cleaned_data.get('country') or '').strip()

        self.has_location_data = any([line_1, line_2, city, state, postal_code, country])

        if self.has_location_data:
            required_fields = {
                'address_line_1': line_1,
                'city': city,
                'state': state,
                'postal_code': postal_code,
            }
            for field_name, value in required_fields.items():
                if not value:
                    self.add_error(field_name, 'This field is required to pin an office location.')
            if not country:
                cleaned_data['country'] = 'United States'

        return cleaned_data
