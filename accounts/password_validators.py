import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class StrongPasswordValidator:
    def validate(self, password, user=None):
        password = password or ""
        errors = []

        if not re.search(r"[A-Z]", password):
            errors.append(_("Password must contain at least one uppercase letter."))
        if not re.search(r"[a-z]", password):
            errors.append(_("Password must contain at least one lowercase letter."))
        if not re.search(r"\d", password):
            errors.append(_("Password must contain at least one number."))
        if not re.search(r"[^A-Za-z0-9]", password):
            errors.append(_("Password must contain at least one special character."))

        if errors:
            raise ValidationError(errors)

    def get_help_text(self):
        return _(
            "Include at least one uppercase letter, one lowercase letter, one number, and one special character."
        )
