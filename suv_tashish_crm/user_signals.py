from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from suv_tashish_crm.models import Courier

User = get_user_model()

@receiver(post_save, sender=User)
def ensure_courier_profile(sender, instance, created, **kwargs):
    if not created:
        return

    username = (instance.username or "").strip()
    if not username.startswith("courier"):
        return

    g, _ = Group.objects.get_or_create(name="courier")
    instance.groups.add(g)

    Courier.objects.get_or_create(
        user=instance,
        defaults={
            "full_name": username,
            "phone": username,
            "is_active": True,
        }
    )