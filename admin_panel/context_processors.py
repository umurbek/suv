from django.utils import timezone
from datetime import timedelta
from suv_tashish_crm.models import Client


def sidebar_debtors(request):
    # clients with debt > 0 and last_order older than 10 days
    cutoff = timezone.now() - timedelta(days=10)
    debtors_qs = Client.objects.filter(debt__gt=0, last_order__lt=cutoff).order_by('-debt')[:10]
    debtors = []
    for c in debtors_qs:
        days_overdue = (timezone.now() - c.last_order).days if c.last_order else None
        debtors.append({
            'id': c.id,
            'name': c.full_name,
            'phone': c.phone,
            'debt': float(c.debt or 0),
            'days_overdue': days_overdue,
        })
    return {'sidebar_debtors': debtors}
