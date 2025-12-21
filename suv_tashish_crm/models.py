from django.db import models

class Admin(models.Model):
    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=15)
    telegram_id = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        app_label = 'suv_tashish_crm'

class Courier(models.Model):
    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=15)
    region = models.ForeignKey('Region', on_delete=models.SET_NULL, null=True)
    telegram_id = models.CharField(max_length=50, null=True, blank=True)
    is_active = models.BooleanField(default=True)

class Client(models.Model):
    full_name = models.CharField(max_length=255)
    first_name = models.CharField(max_length=150, null=True, blank=True)
    last_name = models.CharField(max_length=150, null=True, blank=True)
    phone = models.CharField(max_length=15, unique=True)
    customer_id = models.CharField(max_length=32, unique=True, null=True, blank=True)
    region = models.ForeignKey('Region', on_delete=models.SET_NULL, null=True)
    location_lat = models.FloatField()
    location_lon = models.FloatField()
    bottle_balance = models.IntegerField(default=0)
    debt = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    last_order = models.DateTimeField(null=True, blank=True)
    note = models.TextField(null=True, blank=True)

class Region(models.Model):
    name = models.CharField(max_length=255)


class Notification(models.Model):
    """Simple notification model for admin alerts (dev-friendly)."""
    title = models.CharField(max_length=255)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    seen = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('assigned', 'Assigned'),
        ('delivering', 'Delivering'),
        ('done', 'Done'),
    ]

    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    courier = models.ForeignKey(Courier, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    bottle_count = models.IntegerField()
    debt_change = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    client_note = models.TextField(null=True, blank=True)
    payment_type = models.CharField(max_length=20, null=True, blank=True)
    payment_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

class BottleHistory(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    change = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    comment = models.TextField(null=True, blank=True)

class DebtHistory(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    change = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    comment = models.TextField(null=True, blank=True)