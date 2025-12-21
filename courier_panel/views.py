from django.shortcuts import render, redirect
from django.utils import timezone
from datetime import timedelta
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from suv_tashish_crm.models import Courier, Order, Client
import json
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone


# Simple in-memory store for courier positions (development only)
COURIER_POSITIONS = {}

# Static/demo entries to show on dashboard and API responses (developer/demo mode)
STATIC_DEBTORS = [
    {'id': 'S-1001', 'name': 'Static Mijoz 1', 'phone': '+998901112233', 'debt': 150000.0, 'days_overdue': 12},
    {'id': 'S-1002', 'name': 'Static Mijoz 2', 'phone': '+998901112234', 'debt': 75000.0, 'days_overdue': 20},
]

STATIC_INACTIVE_CLIENTS = [
    {'id': 'I-2001', 'name': 'Static Nofaol 1', 'phone': '+998902223344', 'last_order': (timezone.now()-timedelta(days=15)), 'days_since': 15},
    {'id': 'I-2002', 'name': 'Static Nofaol 2', 'phone': '+998903334455', 'last_order': (timezone.now()-timedelta(days=30)), 'days_since': 30},
]


def dashboard(request):
    # Auth guard temporarily disabled; allow access during development
    courier_id = request.session.get('courier_id')
    courier = None
    if courier_id:
        try:
            courier = Courier.objects.get(pk=courier_id)
        except Courier.DoesNotExist:
            courier = None

    # Today's orders assigned to this courier
    today = timezone.now().date()
    todays_orders_qs = Order.objects.filter(courier=courier, created_at__date=today)
    todays_count = todays_orders_qs.count()

    # Delivered count
    delivered_count = Order.objects.filter(courier=courier, status='done').count()

    # Weekly deliveries (last 7 days) - counts per day
    deliveries_by_day = []
    labels = []
    for i in range(6, -1, -1):
        day = timezone.now().date() - timedelta(days=i)
        count = Order.objects.filter(courier=courier, created_at__date=day).count()
        labels.append(day.strftime('%a'))
        deliveries_by_day.append(count)

    # Recent orders for this courier
    recent_orders = Order.objects.filter(courier=courier).order_by('-created_at')[:10]
    # Top clients by orders (global) - useful for courier sidebar
    try:
        top_clients = (
            Order.objects.values('client__id', 'client__full_name')
            .annotate(orders_count=Count('id'))
            .order_by('-orders_count')[:5]
        )
    except Exception:
        top_clients = []

    # Debtors: clients with outstanding debt (top 10)
    try:
        debtors_qs = Client.objects.filter(debt__gt=0).order_by('-debt')[:10]
        debtors = []
        for c in debtors_qs:
            days_overdue = None
            if getattr(c, 'last_order', None):
                try:
                    days_overdue = (timezone.now().date() - c.last_order.date()).days
                except Exception:
                    days_overdue = None
            debtors.append({'id': c.id, 'name': c.full_name, 'phone': c.phone, 'debt': float(c.debt or 0), 'days_overdue': days_overdue})
    except Exception:
        debtors = []

    # Append static/demo debtors (avoid duplicates by id)
    try:
        existing_ids = {str(d.get('id')) for d in debtors}
        for sd in STATIC_DEBTORS:
            if str(sd.get('id')) not in existing_ids:
                debtors.append(sd)
    except Exception:
        pass

    # Inactive clients: no orders in last 10 days
    try:
        cutoff = timezone.now() - timedelta(days=10)
        inactive_qs = Client.objects.filter(last_order__lt=cutoff).order_by('-last_order')[:10]
        inactive_clients = []
        for c in inactive_qs:
            days_since = None
            if getattr(c, 'last_order', None):
                try:
                    days_since = (timezone.now().date() - c.last_order.date()).days
                except Exception:
                    days_since = None
            inactive_clients.append({'id': c.id, 'name': c.full_name, 'phone': c.phone, 'last_order': c.last_order.strftime('%Y-%m-%d') if c.last_order else None, 'days_since': days_since})
    except Exception:
        inactive_clients = []

    # Append static/demo inactive clients (avoid duplicates)
    try:
        existing_ids = {str(c.get('id')) for c in inactive_clients}
        for si in STATIC_INACTIVE_CLIENTS:
            if str(si.get('id')) not in existing_ids:
                # normalize last_order to string date for template
                lo = si.get('last_order')
                inactive_clients.append({'id': si.get('id'), 'name': si.get('name'), 'phone': si.get('phone'), 'last_order': lo.strftime('%Y-%m-%d') if lo else None, 'days_since': si.get('days_since')})
    except Exception:
        pass

    context = {
        'courier': courier,
        'todays_count': todays_count,
        'delivered_count': delivered_count,
        'debtors': debtors,
        'inactive_clients': inactive_clients,
        'weekly_labels_json': json.dumps(labels, ensure_ascii=False),
        'weekly_data_json': json.dumps(deliveries_by_day),
        'recent_orders': recent_orders,
        'top_clients': top_clients,
    }
    return render(request, 'courier/courier_dashboard.html', context)


def api_metrics(request):
    """Return simple courier metrics (todays_count, delivered_count) for polling updates."""
    courier_id = request.session.get('courier_id')
    courier = None
    if courier_id:
        try:
            courier = Courier.objects.get(pk=courier_id)
        except Courier.DoesNotExist:
            courier = None

    today = timezone.now().date()
    todays_count = Order.objects.filter(courier=courier, created_at__date=today).count()
    # total delivered (all-time) for this courier
    delivered_count = Order.objects.filter(courier=courier, status='done').count()
    return JsonResponse({'status': 'ok', 'data': {'todays_count': todays_count, 'delivered_count': delivered_count}})


def api_today_orders(request):
    courier_id = request.session.get('courier_id')
    courier = None
    if courier_id:
        try:
            courier = Courier.objects.get(pk=courier_id)
        except Courier.DoesNotExist:
            courier = None

    today = timezone.now().date()
    qs = Order.objects.filter(courier=courier, created_at__date=today).order_by('-created_at')
    grouped = {'pending': [], 'assigned': [], 'delivering': [], 'done': []}
    for o in qs:
        client = o.client
        item = {
            'id': o.id,
            'date': o.created_at.isoformat(),
            'client': client.full_name if client else None,
            'phone': client.phone if client else None,
            'lat': getattr(client, 'location_lat', None),
            'lon': getattr(client, 'location_lon', None),
            'status': o.status,
            'bottle_count': o.bottle_count,
            'debt_change': float(o.debt_change or 0.0),
        }
        grouped.setdefault(o.status, []).append(item)

    return JsonResponse({'status': 'ok', 'data': grouped})


def api_weekly_stats(request):
    courier_id = request.session.get('courier_id')
    courier = None
    if courier_id:
        try:
            courier = Courier.objects.get(pk=courier_id)
        except Courier.DoesNotExist:
            courier = None

    labels = []
    counts = []
    revenue = []
    for i in range(6, -1, -1):
        day = timezone.now().date() - timedelta(days=i)
        qs = Order.objects.filter(courier=courier, created_at__date=day)
        labels.append(day.strftime('%a'))
        counts.append(qs.count())
        # use debt_change as proxy for revenue if available
        total = sum([float(o.debt_change or 0.0) for o in qs])
        revenue.append(total)

    return JsonResponse({'status': 'ok', 'labels': labels, 'counts': counts, 'revenue': revenue})


def api_history(request):
    courier_id = request.session.get('courier_id')
    courier = None
    if courier_id:
        try:
            courier = Courier.objects.get(pk=courier_id)
        except Courier.DoesNotExist:
            courier = None

    qs = Order.objects.filter(courier=courier).order_by('-created_at')[:100]
    items = []
    for o in qs:
        items.append({
            'id': o.id,
            'date': o.created_at.isoformat(),
            'status': o.status,
            'client': o.client.full_name if o.client else None,
            'phone': o.client.phone if o.client else None,
            'debt_change': float(o.debt_change or 0.0),
        })
    return JsonResponse({'status': 'ok', 'data': items})


def api_debtors(request):
    qs = Client.objects.filter(debt__gt=0).order_by('-debt')[:200]
    items = []
    for c in qs:
        items.append({
            'id': c.id,
            'full_name': c.full_name,
            'phone': c.phone,
            'debt': float(c.debt or 0.0),
            'note': c.note or '',
        })
    # include static/demo debtors
    try:
        for sd in STATIC_DEBTORS:
            items.append({'id': sd.get('id'), 'full_name': sd.get('name'), 'phone': sd.get('phone'), 'debt': float(sd.get('debt') or 0.0), 'note': 'demo'})
    except Exception:
        pass
    return JsonResponse({'status': 'ok', 'data': items})


def api_inactive_clients(request):
    cutoff = timezone.now() - timedelta(days=10)
    qs = Client.objects.filter(last_order__lt=cutoff).order_by('-last_order')[:200]
    items = []
    for c in qs:
        items.append({
            'id': c.id,
            'full_name': c.full_name,
            'phone': c.phone,
            'last_order': c.last_order.isoformat() if c.last_order else None,
            'total_orders': Order.objects.filter(client=c).count(),
        })
    # include static/demo inactive clients
    try:
        for si in STATIC_INACTIVE_CLIENTS:
            items.append({'id': si.get('id'), 'full_name': si.get('name'), 'phone': si.get('phone'), 'last_order': (si.get('last_order').isoformat() if si.get('last_order') else None), 'total_orders': 0})
    except Exception:
        pass
    return JsonResponse({'status': 'ok', 'data': items})


def api_new_orders(request):
    """Return recent pending orders (new orders from clients) for couriers to pick up."""
    qs = Order.objects.filter(status='pending').order_by('-created_at')[:50]
    items = []
    for o in qs:
        client = o.client
        items.append({
            'id': o.id,
            'date': o.created_at.isoformat(),
            'client': client.full_name if client else None,
            'phone': client.phone if client else None,
            'lat': getattr(client, 'location_lat', None),
            'lon': getattr(client, 'location_lon', None),
            'bottle_count': o.bottle_count,
            'note': o.client_note or '',
        })
    return JsonResponse({'status': 'ok', 'data': items})


@csrf_exempt
def api_create_order_by_courier(request):
    """Create an order on behalf of a courier for a client.

    Expects POST JSON or form fields: client_phone, client_name (optional), bottles (int), note (optional), lat, lon
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=400)

    courier_id = request.session.get('courier_id')
    courier = None
    if courier_id:
        try:
            courier = Courier.objects.get(pk=courier_id)
        except Exception:
            courier = None

    # parse payload
    data = {}
    try:
        if request.content_type == 'application/json':
            data = json.loads(request.body.decode('utf-8'))
        else:
            data = request.POST
    except Exception:
        data = request.POST

    phone = (data.get('client_phone') or data.get('phone') or '').strip()
    name = (data.get('client_name') or data.get('name') or '').strip()
    bottles = data.get('bottles') or data.get('bottle') or 1
    note = data.get('note') or ''
    lat = data.get('lat')
    lon = data.get('lon')

    if not phone:
        return JsonResponse({'status': 'error', 'message': 'client phone required'}, status=400)

    try:
        client = Client.objects.filter(phone=phone).first()
    except Exception:
        client = None

    # create client if not exists
    if not client:
        try:
            client = Client.objects.create(phone=phone, first_name=name or '')
            # if full name provided, set fields
            if name:
                parts = name.split()
                client.first_name = parts[0]
                if len(parts) > 1:
                    client.last_name = ' '.join(parts[1:])
                client.save()
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'failed to create client: {e}'}, status=500)

    # create order
    try:
        bottle_count = int(bottles or 1)
    except Exception:
        bottle_count = 1

    try:
        from decimal import Decimal
        o = Order.objects.create(client=client, bottle_count=bottle_count, client_note=note)
        try:
            unit_price = 12000
            o.debt_change = Decimal(bottle_count * unit_price)
            o.save()
        except Exception:
            pass
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    # save optional lat/lon on client
    try:
        if lat and lon:
            client.location_lat = float(lat)
            client.location_lon = float(lon)
            client.save()
    except Exception:
        pass

    # notify admin and couriers
    try:
        from suv_tashish_crm.models import Notification
        who = f'courier {courier_id}' if courier else 'anonymous/courier-missing'
        Notification.objects.create(title='Yangi buyurtma (kuryer orqali)', message=f'Order #{o.id} by {who} for client {client.id} ({client.phone})')
    except Exception:
        pass

    return JsonResponse({'status': 'ok', 'order_id': o.id})


@csrf_exempt
def api_accept_order(request):
    """Assign a pending order to the current courier (dev). POST JSON {order_id} """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=400)
    try:
        payload = json.loads(request.body.decode('utf-8'))
        order_id = int(payload.get('order_id'))
    except Exception:
        return JsonResponse({'status': 'error', 'message': 'invalid payload'}, status=400)

    courier_id = request.session.get('courier_id')
    if not courier_id:
        return JsonResponse({'status': 'error', 'message': 'no courier in session'}, status=400)

    try:
        order = Order.objects.get(pk=order_id)
    except Order.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'order not found'}, status=404)

    if order.status != 'pending':
        return JsonResponse({'status': 'error', 'message': 'order not pending'}, status=400)

    try:
        courier = Courier.objects.get(pk=courier_id)
    except Courier.DoesNotExist:
        # Clear invalid courier_id from session to avoid repeated errors
        try:
            request.session.pop('courier_id', None)
            request.session.pop('courier_name', None)
            request.session.pop('courier_phone', None)
        except Exception:
            pass
        return JsonResponse({'status': 'error', 'message': "courier not found; set a valid courier session via /courier_panel/dev/login_as/<id> or /courier_panel/dev/set_session/<id>"}, status=404)

    order.courier = courier
    order.status = 'assigned'
    order.save()
    return JsonResponse({'status': 'ok', 'order_id': order.id})


@csrf_exempt
def api_confirm_delivery(request):
    """Courier confirms that an assigned/delivering order was delivered.

    Expects POST JSON: { "order_id": <int> }
    Requires courier_id in session; only the assigned courier may confirm.
    Sets order.status = 'done' and order.delivered_at = now().
    Creates a Notification and attempts to send Telegram to admins.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=400)

    try:
        payload = json.loads(request.body.decode('utf-8'))
        order_id = int(payload.get('order_id'))
    except Exception:
        return JsonResponse({'status': 'error', 'message': 'invalid payload'}, status=400)

    courier_id = request.session.get('courier_id')
    if not courier_id:
        return JsonResponse({'status': 'error', 'message': 'no courier in session'}, status=400)

    try:
        courier = Courier.objects.get(pk=courier_id)
    except Courier.DoesNotExist:
        # Clear invalid courier_id from session and inform caller how to set it
        try:
            request.session.pop('courier_id', None)
            request.session.pop('courier_name', None)
            request.session.pop('courier_phone', None)
        except Exception:
            pass
        return JsonResponse({'status': 'error', 'message': "courier not found; set a valid courier session via /courier_panel/dev/login_as/<id> or /courier_panel/dev/set_session/<id>"}, status=404)

    try:
        order = Order.objects.get(pk=order_id)
    except Order.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'order not found'}, status=404)

    # only assigned courier can confirm delivery
    if order.courier_id != courier.id:
        return JsonResponse({'status': 'error', 'message': 'not assigned to this courier'}, status=403)

    # allowed states to confirm
    if order.status == 'done':
        return JsonResponse({'status': 'ok', 'message': 'already confirmed', 'order_id': order.id})

    # process optional payment info
    payment_type = payload.get('payment_type')
    payment_amount = payload.get('payment_amount')
    try:
        if payment_amount is not None:
            from decimal import Decimal
            try:
                amt = Decimal(str(payment_amount))
            except Exception:
                amt = Decimal('0')
        else:
            amt = None
    except Exception:
        amt = None

    # mark delivered and record payment info on the order
    try:
        order.status = 'done'
        order.delivered_at = timezone.now()
        # store payment info on the order if provided
        try:
            if payment_type:
                order.payment_type = str(payment_type)
            if amt is not None:
                order.payment_amount = amt
        except Exception:
            pass

        # if a payment_type indicates debt, increase client.debt; for cash/click, decrease debt
        try:
            client = order.client
            if client and amt is not None and amt != 0:
                from suv_tashish_crm.models import DebtHistory
                if payment_type == 'debt':
                    # client incurred new debt of amt
                    client.debt = (client.debt or 0) + amt
                    client.save()
                    DebtHistory.objects.create(client=client, change=amt, comment=f'Order #{order.id} marked debt by courier {courier.id}')
                elif payment_type in ('cash', 'click'):
                    # payment received -> reduce debt (if any) and record
                    try:
                        client.debt = (client.debt or 0) - amt
                        client.save()
                    except Exception:
                        pass
                    try:
                        DebtHistory.objects.create(client=client, change=-amt, comment=f'Payment received ({payment_type}) for order #{order.id} by courier {courier.id}')
                    except Exception:
                        pass
        except Exception:
            pass

        order.save()
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    # create notification for admin
    try:
        from suv_tashish_crm.models import Notification
        client = order.client
        client_name = client.first_name or client.full_name or '' if client else ''
        Notification.objects.create(title='Buyurtma yetkazildi', message=f'Order #{order.id} yetkazildi by {courier.full_name if courier else ""}')
    except Exception:
        pass

    # send telegram to admins about delivery
    try:
        from suv_tashish_crm.telegram import send_telegram
        text = f"✅ Buyurtma yetkazildi\nOrder ID: #{order.id}\nCourier: {courier.full_name if courier else ''}\nTime: {timezone.localtime().strftime('%Y-%m-%d %H:%M:%S')}"
        try:
            send_telegram(text)
        except Exception:
            pass
        # also message admins with telegram_id
        try:
            from suv_tashish_crm.models import Admin
            for adm in Admin.objects.all():
                if getattr(adm, 'telegram_id', None):
                    try:
                        send_telegram(text, chat_id=adm.telegram_id)
                    except Exception:
                        pass
        except Exception:
            pass
    except Exception:
        pass

    return JsonResponse({'status': 'ok', 'order_id': order.id})


def new_orders_page(request):
    """Render a dedicated New Orders page. Data is fetched via `api_new_orders` for live updates."""
    courier = None
    courier_id = request.session.get('courier_id')
    if courier_id:
        try:
            courier = Courier.objects.get(pk=courier_id)
        except Courier.DoesNotExist:
            courier = None
    # Fetch pending orders to show to courier (render server-side initially)
    try:
        qs = Order.objects.filter(status='pending').order_by('-created_at')[:50]
        new_orders = []
        for o in qs:
            client = o.client
            new_orders.append({
                'id': o.id,
                'date': o.created_at,
                'client': client.full_name if client else None,
                'phone': client.phone if client else None,
                'lat': getattr(client, 'location_lat', None),
                'lon': getattr(client, 'location_lon', None),
                'bottle_count': o.bottle_count,
                'note': o.client_note or '',
            })
    except Exception:
        new_orders = []

    context = {'courier': courier, 'new_orders': new_orders}
    return render(request, 'courier/new_orders.html', context)


def history_page(request):
    """Render a dedicated History page. Currently shows static example rows."""
    courier = None
    courier_id = request.session.get('courier_id')
    if courier_id:
        try:
            courier = Courier.objects.get(pk=courier_id)
        except Courier.DoesNotExist:
            courier = None
    # build rows from DB: include orders assigned/delivering/done for this courier
    try:
        qs = Order.objects.filter(courier=courier).exclude(status='pending').order_by('-delivered_at', '-created_at', '-created_at')[:200]
        rows = []
        for o in qs:
            # prefer delivered_at, fallback to created_at
            dt = o.delivered_at or o.created_at
            try:
                date_str = dt.strftime('%Y-%m-%d %H:%M')
            except Exception:
                date_str = str(dt)

            # Prefer debt_change as amount (if recorded). Otherwise show bottles count.
            try:
                amt = int(o.debt_change or 0)
                if amt:
                    amount = f"{amt:,} UZS"
                else:
                    amount = f"{o.bottle_count} ta"
            except Exception:
                amount = f"{o.bottle_count} ta" if getattr(o, 'bottle_count', None) is not None else '-'

            # include status label for debug/visibility
            status_label = o.status or ''
            # map payment_type to human label
            ptype = getattr(o, 'payment_type', None)
            if ptype == 'cash':
                p_label = "Pul berdi"
            elif ptype == 'debt':
                p_label = "Qarz bo'ldi"
            elif ptype == 'click':
                p_label = "Click/online"
            else:
                p_label = ''

            rows.append({
                'date': date_str,
                'order_id': f"#{o.id}",
                'client': o.client.full_name if o.client else '-',
                'amount': amount,
                'status': status_label,
                'payment_type': p_label,
            })
    except Exception:
        # fallback to empty list on error
        rows = []

    context = {'courier': courier, 'rows': rows}
    return render(request, 'courier/history.html', context)


def api_get_position(request):
    courier_id = request.session.get('courier_id')
    if not courier_id:
        return JsonResponse({'status': 'error', 'message': 'no courier in session'}, status=400)
    pos = COURIER_POSITIONS.get(courier_id)
    if not pos:
        return JsonResponse({'status': 'ok', 'data': None})
    return JsonResponse({'status': 'ok', 'data': pos})


@csrf_exempt
def api_update_position(request):
    # Accepts JSON: { lat, lon, order_id }
    if request.method != 'POST':
        return HttpResponseBadRequest('POST required')
    try:
        payload = json.loads(request.body.decode('utf-8'))
        lat = float(payload.get('lat'))
        lon = float(payload.get('lon'))
        order_id = payload.get('order_id')
    except Exception:
        return HttpResponseBadRequest('invalid json')

    courier_id = request.session.get('courier_id')
    if not courier_id:
        return JsonResponse({'status': 'error', 'message': 'no courier in session'}, status=400)

    COURIER_POSITIONS[courier_id] = {'lat': lat, 'lon': lon, 'order_id': order_id, 'ts': timezone.now().isoformat()}
    return JsonResponse({'status': 'ok'})


def dev_set_session(request, courier_id):
    """DEV only: set a courier_id in the session to allow simulator to operate.

    Call: GET /courier_panel/dev/set_session/<courier_id>/
    This will set `request.session['courier_id']` and return JSON {status: ok}.
    """
    try:
        # ensure courier exists (optional)
        Courier.objects.get(pk=courier_id)
    except Exception:
        # still set session for convenience, but warn
        pass
    request.session['courier_id'] = courier_id
    # also set display name/phone if available
    try:
        c = Courier.objects.get(pk=courier_id)
        request.session['courier_name'] = c.full_name or ''
        request.session['courier_phone'] = c.phone or ''
    except Exception:
        # clear if not found
        request.session.pop('courier_name', None)
        request.session.pop('courier_phone', None)
    return JsonResponse({'status': 'ok', 'courier_id': courier_id})


def dev_login_as(request, courier_id):
    """DEV helper: set courier_id in session and redirect to dashboard (browser-friendly).

    Visit `/courier_panel/dev/login_as/<courier_id>/` in your browser to set the session
    cookie and be redirected to the courier dashboard.
    """
    try:
        Courier.objects.get(pk=courier_id)
    except Exception:
        pass
    request.session['courier_id'] = courier_id
    try:
        c = Courier.objects.get(pk=courier_id)
        request.session['courier_name'] = c.full_name or ''
        request.session['courier_phone'] = c.phone or ''
    except Exception:
        request.session.pop('courier_name', None)
        request.session.pop('courier_phone', None)
    return redirect('/courier_panel/dashboard/')


def contact_admin(request):
    """Simple contact admin page for couriers (dev)."""
    courier = None
    courier_id = request.session.get('courier_id')
    if courier_id:
        try:
            courier = Courier.objects.get(pk=courier_id)
        except Courier.DoesNotExist:
            courier = None
    # mark last visited view so sidebar can highlight using session
    try:
        request.session['last_view'] = 'contact_admin'
    except Exception:
        pass

    # try to load an Admin contact from DB (dev). Fall back to static defaults.
    admin_info = {
        'full_name': 'Administrator',
        'phone': '+998901112233',
        'telegram': '@admin',
    }
    try:
        from suv_tashish_crm.models import Admin
        adm = Admin.objects.first()
        if adm:
            admin_info['full_name'] = adm.full_name or admin_info['full_name']
            admin_info['phone'] = adm.phone or admin_info['phone']
            admin_info['telegram'] = adm.telegram_id or admin_info['telegram']
    except Exception:
        # ignore DB errors in dev
        pass

    context = {'courier': courier, 'admin': admin_info}
    return render(request, 'courier/contact_admin.html', context)
