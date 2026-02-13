from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model


# ================= REGION =================
class Region(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

class Business(models.Model):
    name = models.CharField(max_length=255, verbose_name="Biznes nomi")
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name
# ================= ADMIN =================
class Admin(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="suv_admin_profile",
        related_query_name="suv_admin_profile",
    )
    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=15)
    telegram_id = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return self.full_name


# ================= COURIER =================
class Courier(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="suv_courier_profile",
        related_query_name="suv_courier_profile",
        null=True,
        blank=True,
    )
    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=15)
    region = models.ForeignKey(Region, on_delete=models.SET_NULL, null=True, blank=True)
    telegram_id = models.CharField(max_length=50, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="couriers", null=True)
    # ✅ first login: password change majburiy
    must_change_password = models.BooleanField(default=True)

    # ixtiyoriy GPS
    lat = models.FloatField(null=True, blank=True)
    lon = models.FloatField(null=True, blank=True)

    def __str__(self):
        return self.full_name


# ================= CLIENT =================
class Client(models.Model):
    # ✅ foydalanuvchiga bog'lash (client login ishlashi uchun)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="suv_client_profile",
        related_query_name="suv_client_profile",
    )
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="clients", null=True)
    full_name = models.CharField(max_length=255)
    first_name = models.CharField(max_length=150, null=True, blank=True)
    last_name = models.CharField(max_length=150, null=True, blank=True)
    phone = models.CharField(max_length=15, unique=True)
    customer_id = models.CharField(max_length=32, unique=True, null=True, blank=True)
    region = models.ForeignKey(Region, on_delete=models.SET_NULL, null=True, blank=True)

    location_lat = models.FloatField(null=True, blank=True)
    location_lon = models.FloatField(null=True, blank=True)

    bottle_balance = models.IntegerField(default=1)
    debt = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    last_order = models.DateTimeField(null=True, blank=True)
    note = models.TextField(null=True, blank=True)
    agreed_to_contract = models.BooleanField(default=False)

    # ✅ first login: password change majburiy
    must_change_password = models.BooleanField(default=True)

    # agar "parent_admin" kerak bo'lsa — qoldir
    parent_admin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_clients",
    )

    # agar "default bottles" kerak bo'lsa — qoldir
    bottles_count = models.PositiveIntegerField(default=1)

    def __str__(self):
        return self.full_name


# ================= NOTIFICATION =================
class Notification(models.Model):
    title = models.CharField(max_length=255)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    seen = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


# ================= ORDER =================
class Order(models.Model):
    STATUS_CHOICES = [
        ("pending", "Kutilmoqda"),
        ("assigned", "Tayinlangan"),
        ("delivering", "Jarayonda"),
        ("done", "Yetkazildi"),
        ("canceled", "Bekor qilindi"),
    ]

    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="orders",
    )

    courier = models.ForeignKey(
        Courier,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
    )

    # mas'ul admin (clientdan keladi)
    parent_admin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
    )

    bottles = models.PositiveIntegerField(default=1, verbose_name="Suv miqdori (dona)")
    note = models.TextField(null=True, blank=True)
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="orders", null=True)
    # GPS koordinatalar
    lat = models.DecimalField(max_digits=22, decimal_places=16, null=True, blank=True)
    lon = models.DecimalField(max_digits=22, decimal_places=16, null=True, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    created_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    # moliya
    debt_change = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    payment_type = models.CharField(max_length=20, null=True, blank=True)
    payment_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    def save(self, *args, **kwargs):
        # ✅ parent_admin clientdan olinadi
        if self.client and not self.parent_admin:
            self.parent_admin = self.client.parent_admin

        # ✅ bottles bo'sh bo'lsa client defaultdan
        if self.client and (not self.bottles or self.bottles == 0):
            self.bottles = self.client.bottles_count or 1

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Order #{self.id} - {self.client.full_name} ({self.bottles} ta)"

    class Meta:
        ordering = ["-created_at"]


# ================= HISTORY =================
class BottleHistory(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="bottle_history")
    change = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    comment = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]


class DebtHistory(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="debt_history")
    change = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    comment = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]


# ================= USER PROFILE / ROLE =================
class UserProfile(models.Model):
    ROLE_ADMIN = "admin"
    ROLE_COURIER = "courier"
    ROLE_CLIENT = "client"

    ROLE_CHOICES = [
        (ROLE_ADMIN, "Admin"),
        (ROLE_COURIER, "Courier"),
        (ROLE_CLIENT, "Client"),
    ]

    user = models.OneToOneField(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name="profile",
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} ({self.role})"


# ================= PUSH TOKEN =================
class PushToken(models.Model):
    user = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name="push_tokens",
        null=True,
        blank=True,
    )

    token = models.CharField(max_length=512, unique=True)
    platform = models.CharField(max_length=32, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        t = self.token[:24] + "..." if self.token else ""
        return f"{self.platform or 'device'} - {t}"