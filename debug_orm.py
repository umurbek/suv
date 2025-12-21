import os
import django
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'suv_tashish_crm.settings')
django.setup()

from suv_tashish_crm.models import Order, Client

def check_orders():
    print("Checking orders...")
    for o in Order.objects.all():
        try:
            print(f"Order {o.id}: debt_change={o.debt_change!r}, payment_amount={o.payment_amount!r}")
        except Exception as e:
            print(f"Error accessing Order {o.id}: {e}")

def check_clients():
    print("Checking clients...")
    for c in Client.objects.all():
        try:
            print(f"Client {c.id}: debt={c.debt!r}")
        except Exception as e:
            print(f"Error accessing Client {c.id}: {e}")

if __name__ == '__main__':
    check_orders()
    check_clients()
