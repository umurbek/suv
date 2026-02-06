from django.db import models
from django.contrib.auth.models import User

class AdminProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="admin_panel_profile",          # ✅ o'zgardi
        related_query_name="admin_panel_profile",    # ✅ qo'shildi
    )
    phone = models.CharField(max_length=30, blank=True, null=True)

    def __str__(self):
        return f"AdminProfile({self.user.username})"
from django.db import models
from django.contrib.auth.models import User

class Courier(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="courier_profile",
        related_query_name="courier_profile",
    )

    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=30)
    is_active = models.BooleanField(default=True)
    # qolgan fieldlar...
# api/models.py
from django.db import models
from django.utils import timezone


class AdminBootstrapRequest(models.Model):
    """
    Admin tiklash/ro‘yxatdan o‘tish uchun OTP.
    """
    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=32)
    email = models.EmailField()

    code = models.CharField(max_length=6)
    expires_at = models.DateTimeField()

    attempts = models.PositiveIntegerField(default=0)
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["email", "is_verified"]),
            models.Index(fields=["expires_at"]),
        ]

    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at