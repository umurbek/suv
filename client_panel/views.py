from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from suv_tashish_crm.models import Client, Notification
from django.views.decorators.csrf import csrf_exempt
import json
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta


def dashboard(request):
    client = None
    if request.session.get('client_id'):
        try:
            client = Client.objects.filter(id=request.session.get('client_id')).first()
        except Exception:
            client = None
    # Ensure session reflects current client name/phone (keeps sidebar consistent)
    try:
        if client:
            request.session['client_name'] = client.first_name or getattr(client, 'full_name', '') or ''
            request.session['client_phone'] = client.phone or ''
    except Exception:
        pass
    # Prepare metrics for admin-like dashboard presentation
    metrics = {}
    recent_orders = []
    weekly_counts = [0,0,0,0,0,0,0]
    if client:
        metrics['bottle_balance'] = getattr(client, 'bottle_balance', 0)
        metrics['debt'] = float(getattr(client, 'debt', 0) or 0)
        try:
            from suv_tashish_crm.models import Order
            qs = Order.objects.filter(client=client).order_by('-created_at')[:10]
            for o in qs:
                recent_orders.append({'id': o.id, 'status': o.status, 'created_at': o.created_at, 'bottles': o.bottle_count, 'note': getattr(o, 'client_note', '')})
            # simple counts by weekday for last 7 days
            import datetime
            today = datetime.date.today()
            for i in range(7):
                day = today - datetime.timedelta(days=6-i)
                weekly_counts[i] = Order.objects.filter(client=client, created_at__date=day).count()
        except Exception:
            recent_orders = []
    # also provide available regions for client to choose when ordering
    regions = []
    try:
        from suv_tashish_crm.models import Region
        regions = list(Region.objects.all().values('id', 'name'))
    except Exception:
        regions = []

    # prepare JSON-safe regions list for template JS
    try:
        import json as _json
        regions_json = _json.dumps(regions)
    except Exception:
        regions_json = '[]'

    ctx = {'client': client, 'metrics': metrics, 'recent_orders': recent_orders, 'weekly_counts': weekly_counts, 'regions': regions, 'regions_json': regions_json}
    return render(request, 'client/client_dashboard.html', ctx)


def orders_view(request):
    # show order history for the logged-in client
    if not request.session.get('client_id'):
        return redirect('/login/')
    client = Client.objects.filter(id=request.session.get('client_id')).first()
    orders = []
    if client:
        try:
            from suv_tashish_crm.models import Order
            qs = Order.objects.filter(client=client).order_by('-created_at')[:100]
            for o in qs:
                orders.append({
                    'id': o.id,
                    'created_at': o.created_at,
                    'status': o.status,
                    'bottles': o.bottle_count,
                    'note': o.client_note,
                    'amount': int(o.debt_change) if getattr(o, 'debt_change', None) is not None else 0,
                })
        except Exception:
            orders = []
    return render(request, 'client/orders.html', {'client': client, 'orders': orders})


def api_client_orders(request):
    """Return JSON list of orders for the logged-in client."""
    if not request.session.get('client_id'):
        return JsonResponse({'status': 'error', 'message': 'Not authenticated'}, status=403)
    client = Client.objects.filter(id=request.session.get('client_id')).first()
    if not client:
        return JsonResponse({'status': 'error', 'message': 'Client not found'}, status=404)
    items = []
    try:
        from suv_tashish_crm.models import Order
        qs = Order.objects.filter(client=client).order_by('-created_at')[:100]
        for o in qs:
            items.append({
                'id': o.id,
                'created_at': o.created_at.isoformat() if getattr(o, 'created_at', None) else '',
                'status': o.status,
                'bottles': o.bottle_count,
                'note': getattr(o, 'client_note', ''),
                'amount': int(o.debt_change) if getattr(o, 'debt_change', None) is not None else 0,
            })
    except Exception:
        items = []
    return JsonResponse({'status': 'ok', 'data': items})


def profile_view(request):
    # Show profile edit form
    client = None
    if not request.session.get('client_id'):
        return redirect('/login/')
    try:
        client = Client.objects.filter(id=request.session.get('client_id')).first()
    except Exception:
        client = None
    # keep session values in sync with actual client record
    try:
        if client:
            request.session['client_name'] = client.first_name or getattr(client, 'full_name', '') or ''
            request.session['client_phone'] = client.phone or ''
    except Exception:
        pass
    # load static regions from CSV to allow selection in profile address field
    try:
        from admin_panel.views import read_csv_data
        static_regions = read_csv_data()
        regions = [r.get('name') for r in static_regions if r.get('name')]
    except Exception:
        regions = []

    return render(request, 'client/profile.html', {'client': client, 'regions': regions})


@csrf_exempt
def api_update_profile(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'})
    if not request.session.get('client_id'):
        return JsonResponse({'status': 'error', 'message': 'Not authenticated'})
    client = Client.objects.filter(id=request.session.get('client_id')).first()
    if not client:
        return JsonResponse({'status': 'error', 'message': 'Client not found'})
    # accept JSON or form
    data = {}
    try:
        if request.content_type == 'application/json':
            data = json.loads(request.body.decode('utf-8'))
        else:
            data = request.POST
    except Exception:
        data = request.POST

    first = (data.get('first_name') or '').strip()
    last = (data.get('last_name') or '').strip()
    phone = (data.get('phone') or data.get('client_phone') or '').strip()
    address = (data.get('address') or '').strip()
    lat = data.get('lat')
    lon = data.get('lon')

    updated = False
    if first:
        client.first_name = first
        updated = True
    if last:
        client.last_name = last
        updated = True
    if phone:
        client.phone = phone
        updated = True
    if lat and lon:
        try:
            client.location_lat = float(lat)
            client.location_lon = float(lon)
            updated = True
        except Exception:
            pass
    if address:
        # try to set a Region by name
        from suv_tashish_crm.models import Region
        region_obj = Region.objects.filter(name=address).first()
        if region_obj is None:
            # try to find in CSV; if not present, append new region to Volidam.csv
            try:
                import os, csv
                try:
                    from admin_panel.views import BASE_DIR, read_csv_data
                except Exception:
                    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                    read_csv_data = None
                csv_path = os.path.join(BASE_DIR, 'Volidam.csv')
                found_in_csv = False
                if os.path.exists(csv_path):
                    with open(csv_path, 'r', encoding='utf-8') as f:
                        reader = csv.reader(f)
                        next(reader, None)
                        for row in reader:
                            name = row[0] if len(row) > 0 else ''
                            if name and name.strip() == address.strip():
                                found_in_csv = True
                                break
                if not found_in_csv:
                    # append new region row (name, bottle, location, phone)
                    with open(csv_path, 'a', encoding='utf-8', newline='') as f:
                        writer = csv.writer(f)
                        writer.writerow([address.strip(), '', '', ''])
            except Exception:
                pass
            # create Region record in DB
            try:
                region_obj, _ = Region.objects.get_or_create(name=address.strip())
            except Exception:
                region_obj = None
        client.region = region_obj
        updated = True

    if updated:
        client.save()
    # If lat/lon provided, try reverse geocode to human-readable address and set region
    if lat and lon:
        try:
            from geopy.geocoders import Nominatim
            geolocator = Nominatim(user_agent='crm_app')
            loc = geolocator.reverse(f"{lat},{lon}", language='en')
            if loc and loc.address:
                addr = loc.address
                from suv_tashish_crm.models import Region
                region_obj, _ = Region.objects.get_or_create(name=addr)
                client.region = region_obj
                client.location_lat = float(lat)
                client.location_lon = float(lon)
                client.save()
        except Exception:
            pass
    # If profile is now complete (has first_name and phone), notify admin and update CSV
    if client.first_name and client.phone:
        try:
            # append/update CSV row by phone
            import os, csv
            try:
                from admin_panel.views import BASE_DIR
            except Exception:
                BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            csv_path = os.path.join(BASE_DIR, 'Volidam.csv')
            rows = []
            found = False
            if os.path.exists(csv_path):
                with open(csv_path, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    headers = next(reader, None)
                    for row in reader:
                        if len(row) > 3 and row[3] == client.phone:
                            # replace
                            rows.append([client.full_name or f"{client.first_name} {client.last_name}", row[1] if len(row)>1 else '', client.region.name if client.region else row[2] if len(row)>2 else '', client.phone])
                            found = True
                        else:
                            rows.append(row)
            if not found:
                # append
                with open(csv_path, 'a', encoding='utf-8', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow([client.full_name or f"{client.first_name} {client.last_name}", '', client.region.name if client.region else '', client.phone])
            else:
                with open(csv_path, 'w', encoding='utf-8', newline='') as f:
                    writer = csv.writer(f)
                    if headers:
                        writer.writerow(headers)
                    for r in rows:
                        writer.writerow(r)
        except Exception:
            pass
        try:
            Notification.objects.create(title='Mijoz profili to\'ldirildi', message=f'Client {client.id} ({client.phone}) yangilandi')
        except Exception:
            pass

    return JsonResponse({'status': 'ok'})


@csrf_exempt
def api_create_order(request):
    # minimal create order endpoint used by dashboard JS
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'})
    # ensure we have a client associated with the session. If not, try
    # to fall back to client info included in the POST (name/phone) so
    # mobile/web users don't get blocked when session cookies are lost.
    client = None
    if request.session.get('client_id'):
        client = Client.objects.filter(id=request.session.get('client_id')).first()
    if not client:
        # try to find client by phone/name provided in the POST body
        phone = (request.POST.get('phone') or request.POST.get('client_phone') or '').strip()
        name = (request.POST.get('name') or request.POST.get('client_name') or '').strip()
        if phone:
            try:
                # keep behavior consistent with login: create if missing
                from suv_tashish_crm.models import Region
                region_obj = None
                client, created = Client.objects.get_or_create(phone=phone, defaults={'full_name': name or '', 'region': region_obj, 'location_lat': 0.0, 'location_lon': 0.0})
                if created and name:
                    # try split name
                    parts = name.split()
                    if len(parts) > 1:
                        client.first_name = parts[0]
                        client.last_name = ' '.join(parts[1:])
                    else:
                        client.first_name = name
                    client.save()
                # bind to session so subsequent requests work normally
                request.session['role'] = 'client'
                request.session['client_id'] = client.id
                try:
                    request.session['client_name'] = client.first_name or client.full_name or ''
                    request.session['client_phone'] = client.phone or ''
                except Exception:
                    pass
            except Exception:
                client = None
        else:
            return JsonResponse({'status': 'error', 'message': 'Not authenticated'})
    if not client:
        return JsonResponse({'status': 'error', 'message': 'Client not found'})
    bottles = request.POST.get('bottles') or request.POST.get('bottle')
    note = request.POST.get('note') or ''
    lat = request.POST.get('lat') or request.POST.get('location_lat')
    lon = request.POST.get('lon') or request.POST.get('location_lon')
    try:
        from suv_tashish_crm.models import Order
        bottle_count = int(bottles or 1)
        # Prevent accidental duplicate submissions: if a very recent pending order
        # with same client, bottle_count and note exists (within 10 seconds),
        # return existing order id instead of creating a new one.
        try:
            recent_cutoff = timezone.now() - timedelta(seconds=10)
            existing = Order.objects.filter(client=client, status='pending', bottle_count=bottle_count, client_note=note, created_at__gte=recent_cutoff).order_by('-created_at').first()
            if existing:
                return JsonResponse({'status': 'ok', 'order_id': existing.id, 'duplicate': True})
        except Exception:
            existing = None

        o = Order.objects.create(client=client, bottle_count=bottle_count, client_note=note)
        # compute monetary amount server-side: 1 bottle = 12_000 UZS
        try:
            unit_price = 12000
            amount = bottle_count * unit_price
            o.debt_change = Decimal(amount)
            o.save()
        except Exception:
            pass
        # if client sent location, save it to client profile for courier use
        try:
            if lat and lon:
                client.location_lat = float(lat)
                client.location_lon = float(lon)
        except Exception:
            pass

        # accept optional client name/phone/region updates from the order form
        try:
            name = request.POST.get('name') or request.POST.get('first_name')
            phone = request.POST.get('phone')
            region_id = request.POST.get('region')
            updated = False
            if name:
                # write into first_name (keep full_name unchanged)
                client.first_name = name.strip()
                updated = True
            if phone:
                client.phone = phone.strip()
                updated = True
            if region_id:
                try:
                    from suv_tashish_crm.models import Region
                    region_obj = Region.objects.filter(id=region_id).first()
                    if region_obj:
                        client.region = region_obj
                        updated = True
                except Exception:
                    pass
            if updated:
                client.save()
                # reflect name/phone in session so sidebar shows them
                try:
                    request.session['client_name'] = client.first_name or ''
                    request.session['client_phone'] = client.phone or ''
                except Exception:
                    pass
            # save lat/lon after potential profile changes
            try:
                if lat and lon:
                    client.location_lat = float(lat)
                    client.location_lon = float(lon)
                    client.save()
            except Exception:
                pass
        except Exception:
            pass
        # notify admin
        try:
            # include client's name/phone from profile in the notification
            cn = client.first_name or client.full_name or ''
            cp = client.phone or ''
            try:
                amt = int(o.debt_change)
            except Exception:
                amt = o.bottle_count * 12000
            # include client's note (if any) in admin notification
            note_text = (o.client_note or '').strip()
            msg = f'Client {client.id} ({cn} {cp}) buyurtma berdi #{o.id} — {o.bottle_count} ta — {amt} UZS'
            if note_text:
                msg = msg + f" — Note: {note_text}"
            Notification.objects.create(title='Yangi buyurtma', message=msg)
        except Exception:
            pass
        # Send Telegram notifications to admin channel and active couriers
        try:
            from suv_tashish_crm.telegram import send_telegram
            # build message
            when = ''
            try:
                from django.utils import timezone
                when = timezone.localtime().strftime('%Y-%m-%d %H:%M:%S')
            except Exception:
                when = ''
            cname = client.first_name or client.full_name or ''
            cphone = client.phone or ''
            creg = client.region.name if getattr(client, 'region', None) else ''
            try:
                amt = int(o.debt_change)
            except Exception:
                amt = o.bottle_count * 12000
            # include client note in telegram message when present
            note_text = (o.client_note or '').strip()
            text = (
                f"📦 Yangi buyurtma\n"
                f"Time: {when}\n"
                f"Client: {cname}\n"
                f"Phone: {cphone}\n"
                f"Region: {creg}\n"
                f"Bottles: {o.bottle_count}\n"
                f"Amount: {amt} UZS\n"
                f"Order ID: {o.id}\n"
            )
            if note_text:
                text += f"Note: {note_text}\n"
            
            # send to main channel (uses settings.TELEGRAM_CHAT_ID)
            try:
                send_telegram(text)
            except Exception:
                pass
            # send direct message to active couriers who have telegram_id set
            try:
                from suv_tashish_crm.models import Courier, Admin
                couriers = Courier.objects.filter(is_active=True)
                for cur in couriers:
                    if getattr(cur, 'telegram_id', None):
                        try:
                            send_telegram(text, chat_id=cur.telegram_id)
                        except Exception:
                            pass
            except Exception:
                pass
            # also try to message any admin users with telegram_id
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
        return JsonResponse({'status': 'ok', 'order_id': o.id})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


def contact_admin(request):
    """Client-facing contact/admin help page."""
    if not request.session.get('client_id'):
        return redirect('/login/')
    client = None
    try:
        client = Client.objects.filter(id=request.session.get('client_id')).first()
    except Exception:
        client = None
    # mark last visited view so sidebar can highlight using session
    try:
        request.session['last_view'] = 'contact_admin'
    except Exception:
        pass

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
        pass

    # normalize telegram handle (without @) for links
    try:
        tg = admin_info.get('telegram') or ''
        admin_info['telegram_handle'] = tg.lstrip('@')
    except Exception:
        admin_info['telegram_handle'] = ''

    # find an assigned courier for this client (most recent order with courier)
    courier_info = None
    try:
        from suv_tashish_crm.models import Order, Courier
        o = Order.objects.filter(client=client, courier__isnull=False).order_by('-created_at').first()
        if o and o.courier:
            courier_info = {'full_name': o.courier.full_name, 'phone': o.courier.phone, 'telegram': getattr(o.courier, 'telegram_id', None)}
            # normalized telegram handle without @ for links
            try:
                tg = courier_info.get('telegram') or ''
                courier_info['telegram_handle'] = tg.lstrip('@')
            except Exception:
                courier_info['telegram_handle'] = ''
    except Exception:
        courier_info = None

    return render(request, 'client/contact_admin.html', {'client': client, 'admin': admin_info, 'courier': courier_info})


@csrf_exempt
def api_contact_admin(request):
    """Receive a client message and create a Notification for admin."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'})
    if not request.session.get('client_id'):
        return JsonResponse({'status': 'error', 'message': 'Not authenticated'})
    client = Client.objects.filter(id=request.session.get('client_id')).first()
    if not client:
        return JsonResponse({'status': 'error', 'message': 'Client not found'})
    msg = request.POST.get('message') or request.POST.get('text') or ''
    try:
        Notification.objects.create(title='Client yordam xabari', message=f'Client {client.id} ({client.phone}): {msg}')
    except Exception:
        pass
    return JsonResponse({'status': 'ok'})


def dev_set_session(request, client_id):
    """DEV helper: set a client_id in the session for testing.

    GET /client_panel/dev/set_session/<client_id>/  sets session and returns JSON.
    """
    try:
        # ensure client exists (optional)
        Client.objects.get(pk=client_id)
    except Exception:
        pass
    request.session['client_id'] = client_id
    try:
        c = Client.objects.get(pk=client_id)
        request.session['client_name'] = c.first_name or c.full_name or ''
        request.session['client_phone'] = c.phone or ''
    except Exception:
        request.session.pop('client_name', None)
        request.session.pop('client_phone', None)
    return JsonResponse({'status': 'ok', 'client_id': client_id})


def dev_login_as(request, client_id):
    """DEV helper: set client_id in session and redirect to client dashboard."""
    try:
        Client.objects.get(pk=client_id)
    except Exception:
        pass
    request.session['client_id'] = client_id
    try:
        c = Client.objects.get(pk=client_id)
        request.session['client_name'] = c.first_name or c.full_name or ''
        request.session['client_phone'] = c.phone or ''
    except Exception:
        request.session.pop('client_name', None)
        request.session.pop('client_phone', None)
    return redirect('/client_panel/dashboard/')
