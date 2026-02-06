from django.db import models
from django.contrib.auth.models import User


class AdminProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='admin_profile',
        verbose_name="Foydalanuvchi"
    )

    full_name = models.CharField(
        max_length=255,
        verbose_name="To‘liq ismi"
    )

    phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name="Telefon raqami"
    )

    role = models.CharField(
        max_length=50,
        default="Moderator",
        verbose_name="Roli"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Yaratilgan sana"
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Yangilangan sana"
    )

    def __str__(self):
        return self.full_name or self.user.username

    class Meta:
        verbose_name = "Admin profili"
        verbose_name_plural = "Admin profillari"
        ordering = ('-created_at',)
