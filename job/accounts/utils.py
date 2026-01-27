import random
import string
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail
import pyotp

from .models import OTP


def generate_numeric_otp(length=6):
    return ''.join(random.choices(string.digits, k=length))


def create_otp_for_user(user, channel='email', lifetime_minutes=10):
    code = generate_numeric_otp(6)
    now = timezone.now()
    expires_at = now + timedelta(minutes=lifetime_minutes)
    record = OTP.objects.create(user=user, code=code, channel=channel, expires_at=expires_at)
    return record


def send_email_otp(user, otp_record):
    # Simple email sender using Django's send_mail — project should configure email backend.
    subject = 'Your verification code'
    message = f'Your verification code is: {otp_record.code}. It expires at {otp_record.expires_at}.'
    from_email = settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else None
    recipient_list = [user.email]
    # Fallback to console or raise if no email configured — send_mail handles backend.
    send_mail(subject, message, from_email, recipient_list, fail_silently=True)


def send_sms_otp(user, otp_record):
    # Placeholder - integrate with Twilio or other SMS provider in production.
    # For now we log to console so devs can simulate SMS sending.
    # Do not store SMS content in insecure logs in production.
    phone = 'N/A'
    try:
        phone = user.customuser.phone_number or 'N/A'
    except Exception:
        pass
    print(f"[SMS to {user.username} ({phone})] OTP: {otp_record.code}")


def create_totp_secret():
    # Use pyotp to generate a random base32 secret
    return pyotp.random_base32()


def verify_totp(totp_secret, token, valid_window=1):
    # valid_window allows some leeway for clock skew
    try:
        totp = pyotp.TOTP(totp_secret)
        return totp.verify(token, valid_window=valid_window)
    except Exception:
        return False
