# api/services.py
import secrets
from datetime import timedelta
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings


def generate_6_digit_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def otp_expiry(minutes: int = 5):
    return timezone.now() + timedelta(minutes=minutes)


def send_admin_bootstrap_code(email: str, code: str):
    subject = "Volidam SUV – Admin tasdiqlash kodi"
    message = (
        "Assalomu alaykum!\n\n"
        "Siz 'Volidam SUV' tizimida admin tiklash/ro‘yxatdan o‘tishni so‘radingiz.\n\n"
        f"🔐 Tasdiqlash kodi: {code}\n\n"
        "⚠️ Kod 5 daqiqa amal qiladi.\n"
        "Agar siz bu so‘rovni yubormagan bo‘lsangiz, iltimos e’tibor bermang.\n\n"
        "Hurmat bilan,\n"
        "Volidam SUV jamoasi"
    )

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=False,
    )