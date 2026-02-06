from django.db import models
from django.conf import settings

class PanelClient(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="panel_client_profile",
        null=True,
        blank=True,
    )
    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, null=True, blank=True)
    bottles_count = models.PositiveIntegerField(default=1)
    location = models.CharField(max_length=255)

    parent_admin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="panel_managed_clients"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.full_name


class Order(models.Model):
    STATUS_CHOICES = [
        ("pending", "Kutilmoqda"),
        ("on_way", "Yo‘lda"),
        ("completed", "Yetkazildi"),
        ("canceled", "Bekor qilindi"),
    ]

    # ✅ suv_tashish_crm dagi Clientga string orqali bog'laymiz
    client = models.ForeignKey(
        "suv_tashish_crm.Client",
        on_delete=models.CASCADE,
        related_name="panel_orders",
        null=True,
        blank=True,
    )

    parent_admin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="panel_orders",
    )

    courier = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="panel_courier_orders",
    )

    bottles = models.PositiveIntegerField(default=1)
    note = models.TextField(null=True, blank=True)

    lat = models.DecimalField(max_digits=22, decimal_places=16, null=True, blank=True)
    lon = models.DecimalField(max_digits=22, decimal_places=16, null=True, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

        # client_panel/models.py
from django.db import models
from django.conf import settings

class PushToken(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="client_push_tokens",   # ✅ o'zgardi
        related_query_name="client_push_token",  # ✅ optional, lekin yaxshi
        null=True,
        blank=True,
    )
    token = models.CharField(max_length=512, unique=True)
    platform = models.CharField(max_length=20, blank=True, default="")  # android/ios/web
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.platform}:{self.token[:20]}"
    





