import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class StrongPasswordValidator:
    """Validator enforcing: min length, uppercase, lowercase, digit, and special char.

    This is intended to complement Django's built-in validators and should be tuned
    to match the project's security policy.
    """
    def __init__(self, min_length=10):
        self.min_length = int(min_length)

    def validate(self, password, user=None):
        if len(password) < self.min_length:
            raise ValidationError(
                _(f"This password must contain at least {self.min_length} characters."),
                code='password_too_short',
            )

        if not re.search(r'[A-Z]', password):
            raise ValidationError(_("This password must contain at least one uppercase letter."), code='password_no_upper')

        if not re.search(r'[a-z]', password):
            raise ValidationError(_("This password must contain at least one lowercase letter."), code='password_no_lower')

        if not re.search(r'[0-9]', password):
            raise ValidationError(_("This password must contain at least one digit."), code='password_no_digit')

        if not re.search(r'[!@#$%^&*(),.?":{}|<>\[\]\\/`~\-_=+;\']', password):
            raise ValidationError(_("This password must contain at least one special character."), code='password_no_special')

    def get_help_text(self):
        return _(
            f"Your password must contain at least {self.min_length} characters, a mix of uppercase and lowercase letters, numbers, and special characters."
        )
