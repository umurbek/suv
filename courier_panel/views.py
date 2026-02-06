from django.shortcuts import render, redirect
from django.utils import timezone
from datetime import timedelta
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from suv_tashish_crm.models import Courier, Order, Client
import json
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from .utils import append_client_to_csv


# Simple in-memory store for courier positions (development only)
COURIER_POSITIONS = {}

# Static data removed



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
    today = timezone.localdate()
    todays_orders_qs = Order.objects.filter(courier=courier, created_at__date=today)
    todays_count = todays_orders_qs.count()

    # Delivered count
    delivered_count = Order.objects.filter(courier=courier, status='done').count()

    # Weekly deliveries (last 7 days) - counts per day
    deliveries_by_day = []
    labels = []
    for i in range(6, -1, -1):
        day = timezone.localdate() - timedelta(days=i)
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
                    days_overdue = (timezone.localdate() - c.last_order.date()).days
                except Exception:
                    days_overdue = None
            debtors.append({'id': c.id, 'name': c.full_name, 'phone': c.phone, 'debt': float(c.debt or 0), 'days_overdue': days_overdue})
    except Exception:
        debtors = []

    # Static debtors logic removed


    # Inactive clients: no orders in last 10 days
    try:
        cutoff = timezone.now() - timedelta(days=10)
        inactive_qs = Client.objects.filter(last_order__lt=cutoff).order_by('-last_order')[:10]
        inactive_clients = []
        for c in inactive_qs:
            days_since = None
            if getattr(c, 'last_order', None):
                try:
                    days_since = (timezone.localdate() - c.last_order.date()).days
                except Exception:
                    days_since = None
            inactive_clients.append({'id': c.id, 'name': c.full_name, 'phone': c.phone, 'last_order': c.last_order.strftime('%Y-%m-%d') if c.last_order else None, 'days_since': days_since})
    except Exception:
        inactive_clients = []

    # Static inactive clients logic removed


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
    today = timezone.localdate()
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

    today = timezone.localdate()
    
    # Get pending orders (no courier assigned yet) and orders assigned to this courier
    from django.db.models import Q
    if courier:
        qs = Order.objects.filter(
            Q(status='pending', courier__isnull=True) | Q(courier=courier),
            created_at__date=today
        ).order_by('-created_at')
    else:
        qs = Order.objects.filter(status='pending', courier__isnull=True, created_at__date=today).order_by('-created_at')
    
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
                'bottles': o.client.bottles_count,
                'debt_change': float(o.debt_change or 0.0),
                'payment_type': getattr(o, 'payment_type', None),
                'payment_amount': float(o.payment_amount) if getattr(o, 'payment_amount', None) is not None else None,
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
        day = timezone.localdate() - timedelta(days=i)
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
        # prefer delivered_at for display date when available
        display_date = (o.delivered_at or o.created_at)
        # normalize payment info
        p_type = getattr(o, 'payment_type', None) or ''
        p_amount = None
        try:
            if getattr(o, 'payment_amount', None) is not None:
                p_amount = float(o.payment_amount)
        except Exception:
            p_amount = None

        items.append({
            'id': o.id,
            'date': display_date.isoformat() if display_date else None,
            'status': o.status,
            'client': o.client.full_name if o.client else None,
            'phone': o.client.phone if o.client else None,
            'debt_change': float(o.debt_change or 0.0),
            'payment_type': p_type,
            'payment_amount': p_amount,
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
    # Static debtors removed

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
    # Static inactive clients removed

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
            'bottle_count': getattr(o, "bottles_count", None)
            if getattr(o, "bottles_count", None) is not None
            else (getattr(o.client, "bottles_count", 0) if hasattr(o, "client") and o.client_id else 0),
            'note': getattr(o, "client_note", None)
            or (getattr(o.client, "note", "") if hasattr(o, "client") and o.client_id else "")
            or (getattr(o.client, "client_note", "") if hasattr(o, "client") and o.client_id else "")
            or "",
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

    # light-weight request logging to help diagnose duplicate submissions
    try:
        with open('/tmp/create_order.log', 'a') as _lf:
            _lf.write(f"{timezone.now().isoformat()} create_order request courier={courier_id} phone={phone} bottles={bottles} content_type={request.content_type}\n")
    except Exception:
        pass

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

    # Deduplication: avoid creating duplicate orders when the same courier/client
    # posts twice quickly (e.g., double-click). If a very recent order with same
    # client and bottle_count exists (last 5 seconds), return that order instead.
    try:
        recent_cutoff = timezone.now() - timedelta(seconds=5)
        recent_qs = Order.objects.filter(client=client, bottle_count=bottle_count, created_at__gte=recent_cutoff).order_by('-created_at')
        if recent_qs.exists():
            existing = recent_qs.first()
            return JsonResponse({'status': 'ok', 'order_id': existing.id, 'note': 'duplicate_ignored'})
    except Exception:
        pass

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
    """Assign a pending order to the current courier (session). POST JSON {order_id}"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)

    # 1) payload
    try:
        payload = json.loads(request.body.decode('utf-8'))
        order_id = int(payload.get('order_id'))
    except Exception:
        return JsonResponse({'status': 'error', 'message': 'invalid payload, expected {"order_id": int}'}, status=400)

    # 2) courier from session
    courier_id = request.session.get('courier_id')
    if not courier_id:
        return JsonResponse({'status': 'error', 'message': 'Not authenticated (no courier_id in session)'}, status=401)

    try:
        courier = Courier.objects.get(pk=courier_id)
    except Courier.DoesNotExist:
        # cleanup broken session
        request.session.pop('courier_id', None)
        request.session.pop('courier_name', None)
        request.session.pop('courier_phone', None)
        return JsonResponse({'status': 'error', 'message': 'courier not found in DB'}, status=401)

    # 3) get order
    try:
        order = Order.objects.select_for_update().get(pk=order_id)
    except Order.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'order not found'}, status=404)

    # 4) rules
    if order.status != 'pending':
        return JsonResponse({'status': 'error', 'message': f'order not pending (status={order.status})'}, status=400)

    if order.courier_id is not None:
        return JsonResponse({'status': 'error', 'message': 'order already assigned'}, status=409)

    # 5) accept
    order.courier = courier
    order.status = 'assigned'
    order.save(update_fields=['courier', 'status'])

    return JsonResponse({'status': 'ok', 'order_id': order.id, 'courier_id': courier.id})
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
            if client:
                from decimal import Decimal
                from suv_tashish_crm.models import DebtHistory

                # Determine effective amount to apply: prefer explicit amt, fallback to order.payment_amount or order.debt_change
                amt_eff = None
                try:
                    if amt is not None:
                        amt_eff = amt
                    else:
                        # try payment_amount on order
                        pa = getattr(order, 'payment_amount', None)
                        dc = getattr(order, 'debt_change', None)
                        if pa is not None:
                            try:
                                amt_eff = Decimal(str(pa))
                            except Exception:
                                amt_eff = None
                        elif dc is not None:
                            try:
                                amt_eff = Decimal(str(dc))
                            except Exception:
                                amt_eff = None
                except Exception:
                    amt_eff = None

                if payment_type == 'debt':
                    # If no explicit amount and no order values, nothing to add
                    if amt_eff is not None and amt_eff != Decimal('0'):
                        client_debt = getattr(client, 'debt', None) or Decimal('0')
                        client.debt = client_debt + amt_eff
                        client.save()
                        try:
                            DebtHistory.objects.create(client=client, change=amt_eff, comment=f'Order #{order.id} marked debt by courier {courier.id}')
                        except Exception:
                            pass
                elif payment_type in ('cash', 'click'):
                    # payment received -> reduce debt (if any) and record; use amt_eff if available
                    if amt_eff is not None and amt_eff != Decimal('0'):
                        client_debt = getattr(client, 'debt', None) or Decimal('0')
                        try:
                            client.debt = client_debt - amt_eff
                            client.save()
                        except Exception:
                            pass
                        try:
                            DebtHistory.objects.create(client=client, change=-amt_eff, comment=f'Payment received ({payment_type}) for order #{order.id} by courier {courier.id}')
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
    courier = None
    courier_id = request.session.get('courier_id')
    if courier_id:
        try:
            courier = Courier.objects.get(pk=courier_id)
        except Courier.DoesNotExist:
            courier = None

    new_orders = []
    qs = Order.objects.filter(status='pending').select_related('client').order_by('-created_at')[:50]

    for o in qs:
        client = getattr(o, "client", None)

        bottles = (
            getattr(o, "bottle_count", None)
            or getattr(o, "bottles", None)
            or getattr(o, "bottles_count", None)
            or getattr(o, "bottle", None)
            or 0
        )
        try:
            bottles = int(bottles)
        except Exception:
            bottles = 0

        note = getattr(o, "client_note", None) or getattr(o, "note", None) or ""

        new_orders.append({
            'id': o.id,
            'date': o.created_at,
            'client': getattr(client, "full_name", None) if client else None,
            'phone': getattr(client, "phone", None) if client else None,
            'lat': getattr(client, 'location_lat', None) if client else None,
            'lon': getattr(client, 'location_lon', None) if client else None,
            'bottle_count': bottles,
            'note': note,
        })

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


def api_get_position_for_id(request, courier_id):
    """Return last-known position for given courier id (development in-memory store).

    This allows admin or other viewers to query courier positions by id.
    """
    try:
        pos = COURIER_POSITIONS.get(int(courier_id))
    except Exception:
        pos = None
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


def profile_view(request):
    """Allow courier to view and edit their profile (dev helper).

    The courier is determined by `request.session['courier_id']`. On POST we update
    `full_name` and `phone` fields and redirect back to profile or dashboard.
    """
    courier = None
    courier_id = request.session.get('courier_id')
    if courier_id:
        try:
            courier = Courier.objects.get(pk=courier_id)
        except Courier.DoesNotExist:
            courier = None

    if request.method == 'POST':
        # simple form fields: full_name, phone, is_active
        full_name = request.POST.get('full_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        is_active = request.POST.get('is_active') == 'on'
        if courier:
            try:
                if full_name:
                    courier.full_name = full_name
                courier.phone = phone
                courier.is_active = is_active
                courier.save()
                # update session display name/phone
                try:
                    request.session['courier_name'] = courier.full_name or ''
                    request.session['courier_phone'] = courier.phone or ''
                except Exception:
                    pass
                return redirect('courier_profile')
            except Exception:
                # fallback to showing the form with an error message
                return render(request, 'courier/profile.html', {'courier': courier, 'error': 'Ma\'lumotlarni saqlashda xato yuz berdi.'})
        else:
            return redirect('courier_dashboard')

    return render(request, 'courier/profile.html', {'courier': courier})




from django.shortcuts import render, redirect
from django.contrib import messages
from suv_tashish_crm.models import Client
from common.csv_utils import append_client_to_csv

def add_client(request):
    if request.method == "POST":
        full_name = (request.POST.get("full_name") or "").strip()
        phone = (request.POST.get("phone") or "").strip()
        address = (request.POST.get("address") or "").strip()

        if not full_name or not phone or not address:
            messages.error(request, "Iltimos, barcha maydonlarni to‘ldiring.")
            return render(request, "courier/add_client.html")

        # ✅ 1) CSV doim yozilsin
        csv_path = append_client_to_csv(full_name, phone, address,  source="courier")

        # ✅ 2) DB: agar bor bo‘lsa update, bo‘lmasa create
        obj, created = Client.objects.get_or_create(
            phone=phone,
            defaults={"full_name": full_name, "note": address},
        )
        if not created:
            # bor bo‘lsa ma'lumotni yangilab qo'yamiz (xohlasangiz)
            obj.full_name = full_name
            obj.note = address
            obj.save(update_fields=["full_name", "note"])

        messages.success(request, f"✅ Saqlandi! CSV: {csv_path}")
        return redirect("courier_panel:courier_dashboard")

    return render(request, "courier/add_client.html")
