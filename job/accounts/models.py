from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
import uuid

class CustomUser(models.Model):
    USER_TYPES = (
        ('user', 'Regular User'),
        ('employee', 'Employee'),
        ('admin', 'Administrator'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    user_type = models.CharField(max_length=20, choices=USER_TYPES, default='user')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Two-factor and lockout fields
    phone_number = models.CharField(max_length=30, blank=True, null=True, help_text="Optional phone number for SMS 2FA")
    totp_secret = models.CharField(max_length=64, blank=True, null=True, help_text="TOTP secret for authenticator apps")
    two_factor_enabled = models.BooleanField(default=False)
    two_factor_method = models.CharField(max_length=20, blank=True, null=True, choices=(
        ('email', 'Email OTP'),
        ('sms', 'SMS OTP'),
        ('totp', 'Authenticator App (TOTP)'),
    ))

    # Lockout/failed attempts
    failed_login_attempts = models.PositiveIntegerField(default=0)
    lockout_until = models.DateTimeField(blank=True, null=True, help_text="If set, account is locked until this time")

    def is_locked(self):
        return self.lockout_until and timezone.now() < self.lockout_until

    def reset_failed_attempts(self):
        self.failed_login_attempts = 0
        self.lockout_until = None
        self.save(update_fields=['failed_login_attempts', 'lockout_until'])

    def __str__(self):
        return f"{self.user.username} - {self.get_user_type_display()}"


class OTP(models.Model):
    """One-time password (OTP) storage for email / sms OTP flows.

    For TOTP (authenticator app), we store the user's secret in `CustomUser.totp_secret` and do not persist codes.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    code = models.CharField(max_length=8)
    channel = models.CharField(max_length=10, choices=(('email','email'),('sms','sms')))
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)

    def is_expired(self):
        return timezone.now() > self.expires_at

    def mark_used(self):
        self.used = True
        self.save(update_fields=['used'])