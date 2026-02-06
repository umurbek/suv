from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group

from suv_tashish_crm.models import Courier


class Command(BaseCommand):
    help = "Link all courier* users with Courier profiles"

    def handle(self, *args, **options):
        group, _ = Group.objects.get_or_create(name="courier")

        users = User.objects.filter(username__startswith="courier")
        if not users.exists():
            self.stdout.write(self.style.WARNING("No courier* users found"))
            return

        linked = 0
        created = 0

        for u in users:
            u.groups.add(group)

            c = Courier.objects.filter(user=u).first()
            if c:
                linked += 1
                continue

            # try phone == username
            c = Courier.objects.filter(phone=u.username).first()
            if c:
                c.user = u
                c.is_active = True
                c.save(update_fields=["user", "is_active"])
                linked += 1
                continue

            # create new courier profile
            Courier.objects.create(
                user=u,
                full_name=u.username,
                phone=u.username,
                is_active=True,
            )
            created += 1

        self.stdout.write(self.style.SUCCESS(
            f"Done. Linked: {linked}, Created: {created}"
        ))