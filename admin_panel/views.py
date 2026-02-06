from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.db.models import Count, Sum, Q
from suv_tashish_crm.models import Order, Client, Courier, Region, Admin
from django.utils import timezone
import random
from decimal import Decimal
import datetime
import json
import csv
import os
import re
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import get_user_model

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def admin_dashboard(request):
    # Auth guard temporarily disabled; re-enable when ready
    today_orders = Order.objects.filter(created_at__date=timezone.localdate()).count()
    active_couriers = Courier.objects.filter(is_active=True).count()
    total_clients = Client.objects.count()
    debtors = Client.objects.filter(debt__gt=0).count()

    top_debtors_qs = Client.objects.filter(debt__gt=0).order_by('-debt')[:5]
    # prefer CSV names for clients that have generic 'Mijoz ...' placeholders
    static_regions = []
    try:
        static_regions = read_csv_data()
    except Exception:
        static_regions = []

    def _normalize_to_998(raw_digits: str):
        if not raw_digits:
            return None
        d = ''.join(ch for ch in raw_digits if ch.isdigit())
        if len(d) < 9:
            return None
        last9 = d[-9:]
        std = '998' + last9
        if len(std) == 12:
            return std
        return None

    csv_phone_map = {}
    csv_phone_by_last6 = {}
    for r in static_regions:
        p = (r.get('phone') or '').strip()
        norm = _normalize_to_998(p)
        if norm:
            csv_phone_map[norm] = r.get('name')
        digits_only = ''.join(ch for ch in p if ch.isdigit())
        if len(digits_only) >= 6:
            csv_phone_by_last6[digits_only[-6:]] = r.get('name')

    top_debtors = []
    for c in top_debtors_qs:
        name = c.full_name or ''
        # prefer CSV mapping when name is generic
        use_name = name
        if (not name) or name.strip().lower().startswith('mijoz'):
            norm = _normalize_to_998(c.phone or '')
            if norm and norm in csv_phone_map:
                use_name = csv_phone_map.get(norm)
            else:
                # try last-6 fallback
                digits_only = ''.join(ch for ch in (c.phone or '') if ch.isdigit())
                if len(digits_only) >= 6 and digits_only[-6:] in csv_phone_by_last6:
                    use_name = csv_phone_by_last6.get(digits_only[-6:])

        top_debtors.append({'id': c.id, 'full_name': use_name, 'region': getattr(c.region, 'name', None), 'debt': getattr(c, 'debt', 0)})
    # Build simple stats for the chart: last 7 days and last 30 days
    weekly_labels = []
    weekly_counts = []
    monthly_labels = []
    monthly_counts = []
    try:
        today = timezone.localdate()
        # last 7 days
        for i in range(6, -1, -1):
            day = today - datetime.timedelta(days=i)
            weekly_labels.append(day.strftime('%a'))
            weekly_counts.append(Order.objects.filter(created_at__date=day).count())

        # last 30 days: labels are day numbers (e.g., '01', '02', ...)
        for i in range(29, -1, -1):
            day = today - datetime.timedelta(days=i)
            monthly_labels.append(day.strftime('%d %b'))
            monthly_counts.append(Order.objects.filter(created_at__date=day).count())
    except Exception:
        weekly_labels = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun']
        weekly_counts = [0,0,0,0,0,0,0]
        monthly_labels = [f"{i+1}" for i in range(30)]
        monthly_counts = [0] * 30

    # Top clients by number of orders (for dashboard sidebar)
    try:
        top_clients_qs = (
            Order.objects.values('client__id', 'client__full_name')
            .annotate(orders_count=Count('id'))
            .order_by('-orders_count')[:5]
        )
        top_clients = [{'id': t['client__id'], 'full_name': t.get('client__full_name') or '—', 'orders_count': t.get('orders_count', 0)} for t in top_clients_qs]
    except Exception:
        top_clients = []
    # Top couriers by delivered orders (dynamic)
    try:
        top_couriers_qs = (
            Order.objects.filter(status='done')
            .values('courier__id', 'courier__full_name')
            .annotate(delivered=Count('id'))
            .order_by('-delivered')[:5]
        )
        top_couriers = [{'id': t.get('courier__id'), 'full_name': t.get('courier__full_name') or '—', 'delivered': t.get('delivered', 0)} for t in top_couriers_qs]
    except Exception:
        top_couriers = []

    # Orders per region (dynamic)
    try:
        region_stats_qs = (
            Order.objects.values('client__region__name')
            .annotate(total_orders=Count('id'))
            .order_by('-total_orders')[:10]
        )
        region_stats = [{'region': t.get('client__region__name') or '—', 'total_orders': t.get('total_orders', 0)} for t in region_stats_qs]
    except Exception:
        region_stats = []

    context = {
        'today_orders': today_orders,
        'active_couriers': active_couriers,
        'total_clients': total_clients,
        'debtors': debtors,
        'top_debtors': top_debtors,
        'top_clients': top_clients,
        'top_couriers': top_couriers,
        'region_stats': region_stats,
        'weekly_labels_json': json.dumps(weekly_labels, ensure_ascii=False),
        'weekly_data_json': json.dumps(weekly_counts),
        'monthly_labels_json': json.dumps(monthly_labels, ensure_ascii=False),
        'monthly_data_json': json.dumps(monthly_counts),
    }

    return render(request, 'admin/admin_dashboard.html', context)


def read_csv_data():
    regions = []
    csv_path = os.path.join(BASE_DIR, 'Volidam.csv')
    with open(csv_path, 'r', encoding='utf-8') as file:
        reader = csv.reader(file)
        next(reader)  # Skip header
        for row in reader:
            regions.append({
                'name': row[0],
                'bottle': row[1],
                'location': row[2],
                'phone': row[3] if len(row) > 3 else ''
            })
    return regions


def regions_view(request):
    """Show regions list. Uses DB if available, falls back to CSV data."""
    static_regions = []
    try:
        static_regions = read_csv_data()
    except Exception:
        static_regions = []

    regions = []
    locations = []

    try:
        qs = Region.objects.all()
        for r in qs:
            name = getattr(r, 'name', '')
            bottle = getattr(r, 'bottle', '') if hasattr(r, 'bottle') else ''
            loc = getattr(r, 'location', '') if hasattr(r, 'location') else ''
            phone = getattr(r, 'phone', '') if hasattr(r, 'phone') else ''
            regions.append({'name': name, 'bottle': bottle, 'location': loc, 'phone': phone})
            if loc and loc not in locations:
                locations.append(loc)

        # If DB has no regions but CSV does, show CSV rows instead
        if not regions and static_regions:
            regions = static_regions
            seen = set()
            locations = []
            for r in static_regions:
                loc = (r.get('location') or '').strip()
                if loc and loc not in seen:
                    seen.add(loc)
                    locations.append(loc)
    except Exception:
        regions = static_regions
        seen = set()
        locations = []
        for r in regions:
            loc = (r.get('location') or '').strip()
            if loc and loc not in seen:
                seen.add(loc)
                locations.append(loc)

    return render(request, 'admin/regions.html', {'regions': regions, 'locations': locations})


def add_region(request):
    if request.method == 'POST':
        # Auth guard temporarily disabled; re-enable when ready
        try:
            import json
            payload = json.loads(request.body.decode('utf-8'))
            name = (payload.get('name') or '').strip()
            bottle = (payload.get('bottle') or '').strip()
            location = (payload.get('location') or '').strip()
            phone = (payload.get('phone') or '').strip()
            if not name:
                return JsonResponse({'status': 'error', 'message': "Hudud nomi kerak."})

            # create or get Region in DB
            region_obj, created = Region.objects.get_or_create(name=name)

            # We keep CSV metadata for backward compatibility but do not write to CSV here.
            return JsonResponse({'status': 'success', 'region': {'name': region_obj.name, 'bottle': bottle, 'location': location, 'phone': phone, 'created': created}})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})


def update_region(request):
    if request.method == 'POST':
        # Auth guard temporarily disabled; re-enable when ready
        # Expect JSON payload with old name and new fields
        try:
            import json
            payload = json.loads(request.body.decode('utf-8'))
            orig_name = payload.get('name') or payload.get('orig_name')
            new_name = payload.get('newName') or payload.get('name_new') or payload.get('new_name')
            new_bottle = payload.get('bottle')
            new_location = payload.get('location') or payload.get('newLocation')
            new_phone = payload.get('phone') or payload.get('newPhone')
            # Server-side phone validation: if provided, must be +998 followed by 9 digits
            if new_phone:
                new_phone = new_phone.strip()
                if not re.match(r'^\+998\d{9}$', new_phone):
                    return JsonResponse({'status': 'error', 'message': "Telefon formati noto'g'ri. Iltimos '+998XXXXXXXXX' formatida kiriting."})

            if not orig_name:
                return JsonResponse({'status': 'error', 'message': 'Orig name required.'})

            try:
                region_obj = Region.objects.get(name=orig_name)
            except Region.DoesNotExist:
                return JsonResponse({'status': 'not_found'})

            if new_name:
                region_obj.name = new_name
                region_obj.save()

            # We intentionally do not store bottle/location/phone on Region model (legacy CSV kept separately)
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})


def delete_region(request):
    if request.method == 'POST':
        # Auth guard temporarily disabled; re-enable when ready
        try:
            import json
            payload = json.loads(request.body.decode('utf-8'))
            name = (payload.get('name') or '').strip()
            if not name:
                return JsonResponse({'status': 'error', 'message': "Hudud nomi kerak."})

            try:
                region_obj = Region.objects.get(name=name)
                region_obj.delete()
                return JsonResponse({'status': 'success'})
            except Region.DoesNotExist:
                return JsonResponse({'status': 'not_found'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})


def couriers_view(request):
    # Auth guard temporarily disabled; re-enable when ready
    # Provide dynamic list of couriers to the template
    try:
        qs = Courier.objects.select_related('region').all().order_by('full_name')
        couriers = []
        for c in qs:
            status_label = 'Faol' if getattr(c, 'is_active', False) else 'Nofaol'
            couriers.append({
                'id': c.id,
                'full_name': c.full_name,
                'phone': c.phone,
                'region': getattr(c.region, 'name', ''),
                'is_active': getattr(c, 'is_active', False),
                'status_label': status_label,
            })
    except Exception:
        couriers = []

    # Pop any flash messages set by other views (add/edit/delete)
    flash_message = request.session.pop('flash_message', None)
    flash_type = request.session.pop('flash_type', None)

    # Render the modern styled template with optional flash
    return render(request, 'admin/couriers.html', {'couriers': couriers, 'flash_message': flash_message, 'flash_type': flash_type})


def region_clients_api(request):
    """Return JSON list of clients for a given region name.

    Query param: ?name=<region name>
    """
    name = request.GET.get('name') or request.POST.get('name')
    if not name:
        return JsonResponse({'status': 'error', 'message': 'Region name required.'}, status=400)

    try:
        clients_qs = Client.objects.filter(region__name=name)
    except Exception:
        clients_qs = Client.objects.none()

    clients = []
    for c in clients_qs:
        try:
            lat = float(getattr(c, 'location_lat', 0) or 0)
            lon = float(getattr(c, 'location_lon', 0) or 0)
        except Exception:
            lat = 0.0
            lon = 0.0

        clients.append({
            'id': c.id,
            'full_name': c.full_name,
            'phone': c.phone,
            'lat': lat,
            'lon': lon,
            'note': c.note or '',
        })

    return JsonResponse({'status': 'ok', 'clients': clients})


def clients_positions_api(request):
    """Return JSON list of all clients with lat/lon for admin map display."""
    try:
        qs = Client.objects.all()
    except Exception:
        qs = Client.objects.none()
    items = []
    for c in qs:
        try:
            lat = float(getattr(c, 'location_lat', 0) or 0)
            lon = float(getattr(c, 'location_lon', 0) or 0)
        except Exception:
            lat = 0.0; lon = 0.0
        # skip clients without a meaningful location
        if lat == 0 and lon == 0:
            continue
        items.append({'id': c.id, 'full_name': c.full_name, 'phone': c.phone, 'lat': lat, 'lon': lon, 'region': getattr(c.region, 'name', None)})
    return JsonResponse({'status': 'ok', 'clients': items})


def clients_view(request):
    # Auth guard temporarily disabled; re-enable when ready
    # Provide dynamic client profiles to template
    try:
        static_regions = read_csv_data()
    except Exception:
        static_regions = []
    static_map = {r.get('name'): r.get('location') for r in static_regions}
    clients_qs = Client.objects.select_related('region').all()
    clients = []
    for c in clients_qs:
        address = ''
        if c.region:
            address = static_map.get(c.region.name) or getattr(c.region, 'name', '')
        last_order = Order.objects.filter(client=c).order_by('-created_at').first()
        last_order_date = ''
        if last_order and getattr(last_order, 'created_at', None):
            try:
                last_order_date = last_order.created_at.strftime('%Y-%m-%d %H:%M')
            except Exception:
                last_order_date = str(last_order.created_at)
        clients.append({
            'id': c.id,
            'full_name': c.full_name,
            'phone': c.phone,
            'address': address,
            'debt': getattr(c, 'debt', 0),
            'bottle_balance': getattr(c, 'bottle_balance', 0),
            'last_order_date': last_order_date,
        })
    return render(request, 'admin/clients.html', {'clients': clients})

from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from .models import AdminProfile

User = get_user_model()


# =========================
# PROFIL SAHIFASI
# =========================
from .models import AdminProfile


def profile_view(request):
    # Do not force redirect to login here; render profile page and
    # show editable fields only for authenticated users.
    admin_data = None
    if request.user.is_authenticated:
        # Admin profili yaratish yoki olish (default qiymatlar bilan)
        admin_data, created = AdminProfile.objects.get_or_create(
            user=request.user,
            defaults={
                'full_name': request.user.username,
                'phone': '',
                'role': 'Administrator'
            }
        )

    # Barcha adminlar ro'yxatini olish (template uchun)
    all_admins = Admin.objects.all()

    return render(request, 'admin/profile.html', {
        'admin_profile': admin_data,
        'user': request.user,
        'all_admins': all_admins,
        'total_admins': all_admins.count(),
    })

# =========================
# PROFILNI YANGILASH API
# =========================
@login_required(login_url='/admin_panel/login/')
def api_update_profile(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Faqat POST so‘rov qabul qilinadi'}, status=405)

    admin_name = request.POST.get('admin_name', '').strip()
    username = request.POST.get('username', '').strip()
    email = request.POST.get('email', '').strip()
    password = request.POST.get('password', '').strip()

    user = request.user

    try:
        # ===== USER =====
        if username and username != user.username:
            if User.objects.filter(username=username).exclude(id=user.id).exists():
                return JsonResponse({'status': 'error', 'message': 'Bu login (username) band'}, status=400)
            user.username = username

        if email:
            try:
                validate_email(email)
            except ValidationError:
                return JsonResponse({'status': 'error', 'message': 'Email noto‘g‘ri formatda'}, status=400)
            user.email = email

        if admin_name:
            user.first_name = admin_name

        if password:
            if len(password) < 8:
                return JsonResponse({'status': 'error', 'message': 'Parol kamida 8 ta belgidan iborat bo‘lishi kerak'}, status=400)
            user.set_password(password)

        user.save()

        if password:
            update_session_auth_hash(request, user)  # parol o'zgarganda logout bo'lmasligi uchun

        # ===== ADMIN PROFILE =====
        AdminProfile.objects.update_or_create(
            user=user,
            defaults={'full_name': admin_name or user.get_full_name() or user.username}
        )

        return JsonResponse({'status': 'ok', 'message': 'Profil muvaffaqiyatli yangilandi'})

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Xatolik: {str(e)}'}, status=500)

def notifications_api(request):
    """Return unseen notifications for admin panel (JSON)."""
    try:
        from suv_tashish_crm.models import Notification
        qs = Notification.objects.filter(seen=False).order_by('-created_at')[:50]
        data = []
        for n in qs:
            data.append({'id': n.id, 'title': n.title, 'message': n.message, 'created_at': n.created_at.isoformat()})
        return JsonResponse({'status': 'ok', 'notifications': data})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


def orders_view(request):
    # Auth guard temporarily disabled; re-enable when ready

    # pop any flash message set by other views (edit/delete)
    flash_message = request.session.pop('flash_message', None)
    flash_type = request.session.pop('flash_type', None)
    # Fetch recent orders with related client/courier/region
    orders_qs = Order.objects.select_related('client__region', 'courier').order_by('-created_at')[:50]

    orders = []
    for o in orders_qs:
        # determine address: prefer CSV location for the client's region if available
        o_address = ''
        if o.client and o.client.region:
            # static_location_map may not be defined yet; try to read CSV and map
            try:
                static_regions_temp = read_csv_data()
                static_map_temp = { r.get('name'): r.get('location') for r in static_regions_temp }
                o_address = static_map_temp.get(o.client.region.name) or getattr(o.client.region, 'name', '')
            except Exception:
                o_address = getattr(o.client.region, 'name', '')

        # map internal status to Uzbek label and CSS class
        if o.status == 'done':
            s_label = 'Yetkazildi'
            s_class = 'text-green-600 bg-green-100'
        elif o.status in ('delivering', 'assigned'):
            s_label = 'Jarayonda'
            s_class = 'text-yellow-600 bg-yellow-100'
        else:
            s_label = 'Berilmadi'
            s_class = 'text-red-600 bg-red-100'

        orders.append({
            'order_id': o.id,
            'order_label': f"#{o.id}",
            'client_id': o.client.id if o.client else None,
            'user_id': f"u_{o.client.id}",
            'client_name': o.client.full_name,
            'phone': o.client.phone,
            'address': o_address,
            'lat': getattr(o.client, 'location_lat', None) if o.client else None,
            'lon': getattr(o.client, 'location_lon', None) if o.client else None,
            # prefer the comment attached to the order (client_note); fallback to client's profile note
            'comment': (getattr(o, 'client_note', None) or (o.client.note if o.client else '')),
            'status': o.status,
            'status_label': s_label,
            'status_class': s_class,
            'courier': o.courier.full_name if o.courier else None,
            'bottles': o.bottle_count,
            'amount': int(o.debt_change) if getattr(o, 'debt_change', None) is not None else None,
            # payment info (stored on Order when courier confirms delivery)
            'payment_type': (lambda pt: ('Pul berdi (naqd)' if pt=='cash' else ('Qarz bo\'ldi' if pt=='debt' else ('Click/online' if pt=='click' else ''))))(getattr(o, 'payment_type', None)),
            'payment_amount': int(o.payment_amount) if getattr(o, 'payment_amount', None) is not None else None,
        })

    # Top clients by number of orders
    top_clients = (
        Order.objects.values('client__id', 'client__full_name', 'client__phone')
        .annotate(orders_count=Count('id'))
        .order_by('-orders_count')[:10]
    )

    # Top couriers by delivered orders
    top_couriers = (
        Order.objects.filter(status='done')
        .values('courier__id', 'courier__full_name')
        .annotate(delivered=Count('id'))
        .order_by('-delivered')[:10]
    )

    # Orders per region
    region_stats = (
        Order.objects.values('client__region__id', 'client__region__name')
        .annotate(total_orders=Count('id'))
        .order_by('-total_orders')
    )

    # include static regions parsed from CSV so templates can show static region info if needed
    static_regions = read_csv_data()

    # build a mapping from region name -> location (CSV 'location' column)
    static_location_map = { r.get('name'): r.get('location') for r in static_regions }

    # Also provide all client profiles so the Orders page can show "all profiles"
    clients_qs = Client.objects.select_related('region').all()

    profiles = []
    for c in clients_qs:
        # prefer CSV location for region if available, otherwise use Region.name
        address = ''
        if c.region:
            address = static_location_map.get(c.region.name) or getattr(c.region, 'name', '')

        # determine last order status for this client
        last_order = Order.objects.filter(client=c).order_by('-created_at').first()
        if last_order:
            st = last_order.status
            if st == 'done':
                p_label = 'Yetkazildi'
                p_class = 'text-green-600 bg-green-100'
            elif st in ('delivering', 'assigned'):
                p_label = 'Jarayonda'
                p_class = 'text-yellow-600 bg-yellow-100'
            else:
                p_label = 'Berilmadi'
                p_class = 'text-red-600 bg-red-100'
        else:
            p_label = ''
            p_class = 'text-gray-600'

        profiles.append({
            'client_id': c.id,
            'order_label': '',
            'user_id': f"u_{c.id}",
            'client_name': c.full_name,
            'phone': c.phone,
            'address': address,
            'comment': c.note or '',
            'debt': getattr(c, 'debt', Decimal('0.00')) or Decimal('0.00'),
            'status_label': p_label,
            'status_class': p_class,
            'status': '',
            'courier': None,
            'bottles': getattr(c, 'bottle_balance', 0),
        })

    context = {
        'orders': orders,
        'profiles': profiles,
        'static_regions': static_regions,
        'regions': Region.objects.order_by('name'),
        'flash_message': flash_message,
        'flash_type': flash_type,
        'top_clients': top_clients,
        'top_couriers': top_couriers,
        'region_stats': region_stats,
    }
    return render(request, 'admin/orders.html', context)


def seed_region_orders(request):
    """Create one static order per entry in Volidam.csv.

    This view must be called with POST (token-protected). For each CSV row:
    - ensure a Region exists
    - create or get a Client for that region (unique phone generated if missing)
    - create an Order for that client
    """
    if request.session.get('role') != 'admin':
        # require login as admin
        return redirect('/login/')

    if request.method != 'POST':
        return redirect('orders_view')

    static_regions = read_csv_data()
    # Auth guard temporarily disabled; re-enable when ready
    created = 0
    for idx, r in enumerate(static_regions):
        region_name = r.get('name') or f'Region {idx}'
        region_obj, _ = Region.objects.get_or_create(name=region_name)

        # Try to use CSV phone if provided and unique, otherwise create synthetic phone
        phone = r.get('phone') or ''
        if phone:
            # normalize phone length
            phone = phone.strip()
            if len(phone) > 15:
                phone = phone[:15]

        if not phone or Client.objects.filter(phone=phone).exists():
            # generate unique phone-like identifier
            phone = f"r{idx}_{int(timezone.now().timestamp())}"[:15]
            # ensure uniqueness by appending idx if necessary
            while Client.objects.filter(phone=phone).exists():
                phone = f"{phone}_{random.randint(0,999)}"[:15]

        # Use CSV name when available, otherwise a neutral client name
        csv_name = (r.get('name') or '').strip()
        if csv_name:
            client_name = csv_name
        else:
            client_name = f"Mijoz {idx + 1}"

        client, created_client = Client.objects.get_or_create(phone=phone, defaults={
            'full_name': client_name,
            'region': region_obj,
            'location_lat': 0.0,
            'location_lon': 0.0,
        })

        # If client existed but has a generic 'Mijoz N' name and CSV provides a better name, update it
        if not created_client and csv_name and (client.full_name.startswith('Mijoz') or client.full_name.strip() == ''):
            client.full_name = csv_name
            client.save()

        # assign a random debt for some clients (30% chance)
        if created_client:
            if random.random() < 0.3:
                debt_amount = Decimal(str(round(random.uniform(10, 300), 2)))
                client.debt = debt_amount
            else:
                client.debt = Decimal('0.00')
            client.save()

        # create a static order for the client (1-5 bottles randomly)
        bottles = random.randint(1, 5)
        Order.objects.create(
            client=client,
            courier=None,
            bottle_count=bottles,
            client_note=f"Static seed order for {region_name}",
            status='done',
        )

        # update client stats
        client.last_order = timezone.now()
        client.bottle_balance = getattr(client, 'bottle_balance', 0) + 0
        client.save()
        created += 1

    # Redirect back with a very small message via session (optional)
    request.session['seeded_regions'] = created
    return redirect('orders_view')


def edit_client(request, client_id):
    try:
        client = Client.objects.get(pk=client_id)
    except Client.DoesNotExist:
        return redirect('orders_view')

    if request.method == 'POST':
        client.full_name = request.POST.get('full_name', client.full_name)
        phone = request.POST.get('phone', client.phone)
        if phone and phone != client.phone:
            # ensure unique phone - basic check
            if not Client.objects.filter(phone=phone).exclude(pk=client.pk).exists():
                client.phone = phone
        region_id = request.POST.get('region_id', '').strip()
        if region_id:
            try:
                region_obj = Region.objects.get(pk=int(region_id))
                client.region = region_obj
            except (Region.DoesNotExist, ValueError):
                pass
        client.note = request.POST.get('note', client.note)
        client.save()
        # set flash message to show on orders page
        request.session['flash_message'] = 'Mijoz muvaffaqiyatli tahrirlandi.'
        request.session['flash_type'] = 'success'
        return redirect('orders_view')

    # Prepare regions list with CSV 'location' as display text when available
    static_regions = read_csv_data()
    static_map = {r.get('name'): r.get('location') for r in static_regions}
    regions_qs = Region.objects.order_by('name')
    regions_with_location = [(r.id, static_map.get(r.name) or r.name) for r in regions_qs]
    return render(request, 'admin/edit_client.html', {'client': client, 'regions_with_location': regions_with_location})


def delete_client(request, client_id):
    if request.method == 'POST':
        try:
            client = Client.objects.get(pk=client_id)
            client.delete()
        except Client.DoesNotExist:
            pass
    # set flash message for deletion
    request.session['flash_message'] = 'Mijoz o`chirildi.'
    request.session['flash_type'] = 'danger'
    return redirect('orders_view')


def add_courier(request):
    # Add a new courier via simple form
    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        region_id = request.POST.get('region_id', '').strip()
        is_active = True if request.POST.get('is_active') == 'on' else False

        region_obj = None
        if region_id:
            # Accept either an integer PK or a region name from CSV choices
            try:
                region_obj = Region.objects.get(pk=int(region_id))
            except Exception:
                try:
                    region_obj, _ = Region.objects.get_or_create(name=region_id)
                except Exception:
                    region_obj = None

        if full_name and phone:
            Courier.objects.create(full_name=full_name, phone=phone, region=region_obj, is_active=is_active)
            request.session['flash_message'] = 'Kuryer qo\'shildi.'
            request.session['flash_type'] = 'success'
            return redirect('couriers_view')

    # Build region choices: prefer DB Regions, but append unique CSV locations for convenience
    # Build region choices: prefer CSV 'location' values first to avoid CSV-name pollution
    try:
        static_regions = read_csv_data()
    except Exception:
        static_regions = []
    try:
        db_regions = list(Region.objects.order_by('name'))
    except Exception:
        db_regions = []

    seen = set()
    region_choices = []
    # prefer CSV locations (these are actual hudud names in Volidam.csv)
    for r in static_regions:
        loc = (r.get('location') or '').strip()
        if loc and loc not in seen:
            seen.add(loc)
            region_choices.append({'value': loc, 'label': loc})
    # then append DB regions that are not duplicates
    for r in db_regions:
        name = (r.name or '').strip()
        if name and name not in seen:
            seen.add(name)
            region_choices.append({'value': str(r.id), 'label': name})

    return render(request, 'admin/add_edit_courier_clean.html', {'region_choices': region_choices, 'action': 'add'})


def edit_courier(request, courier_id):
    try:
        courier = Courier.objects.get(pk=courier_id)
    except Courier.DoesNotExist:
        request.session['flash_message'] = 'Kuryer topilmadi.'
        request.session['flash_type'] = 'danger'
        return redirect('couriers_view')

    if request.method == 'POST':
        courier.full_name = request.POST.get('full_name', courier.full_name).strip()
        phone = request.POST.get('phone', courier.phone).strip()
        if phone and phone != courier.phone:
            # ensure unique phone among couriers (best effort)
            if not Courier.objects.filter(phone=phone).exclude(pk=courier.pk).exists():
                courier.phone = phone

        region_id = request.POST.get('region_id', '').strip()
        if region_id:
            try:
                courier.region = Region.objects.get(pk=int(region_id))
            except Exception:
                try:
                    region_obj, _ = Region.objects.get_or_create(name=region_id)
                    courier.region = region_obj
                except Exception:
                    pass

        courier.is_active = True if request.POST.get('is_active') == 'on' else False
        courier.save()

        request.session['flash_message'] = 'Kuryer muvaffaqiyatli tahrirlandi.'
        request.session['flash_type'] = 'success'
        return redirect('couriers_view')

    # Build region choices (same as add view)
    try:
        db_regions = list(Region.objects.order_by('name'))
    except Exception:
        db_regions = []
    try:
        static_regions = read_csv_data()
    except Exception:
        static_regions = []

    seen = set()
    region_choices = []
    for r in db_regions:
        name = (r.name or '').strip()
        if name and name not in seen:
            seen.add(name)
            region_choices.append({'value': str(r.id), 'label': name})
    for r in static_regions:
        loc = (r.get('location') or '').strip()
        if loc and loc not in seen:
            seen.add(loc)
            region_choices.append({'value': loc, 'label': loc})

    return render(request, 'admin/add_edit_courier_clean.html', {'region_choices': region_choices, 'courier': courier, 'action': 'edit'})


def delete_courier(request, courier_id):
    if request.method == 'POST':
        try:
            courier = Courier.objects.get(pk=courier_id)
            courier.delete()
            request.session['flash_message'] = 'Kuryer o\'chirildi.'
            request.session['flash_type'] = 'danger'
        except Courier.DoesNotExist:
            request.session['flash_message'] = 'Kuryer topilmadi.'
            request.session['flash_type'] = 'danger'
    return redirect('couriers_view')


def reports_view(request):
    # Build weekly and monthly revenue datasets and top couriers for the template
    import json
    from django.db.models import Q

    try:
        today = timezone.localdate()
    except Exception:
        today = datetime.date.today()

    # Weekly: last 7 days (labels and sums)
    weekly_labels = []
    weekly_data = []
    try:
        for i in range(6, -1, -1):
            day = today - datetime.timedelta(days=i)
            weekly_labels.append(day.strftime('%a'))
            # Sum payment_amount for orders delivered that day (prefer delivered_at, fallback to created_at)
            qs = Order.objects.filter(
                Q(delivered_at__date=day) | (Q(status='done') & Q(created_at__date=day))
            )
            total = qs.aggregate(total=Sum('payment_amount'))
            val = total.get('total')
            # fallback to count of delivered orders if payment_amount not set
            if not val:
                val = qs.count()
            try:
                weekly_data.append(int(val))
            except Exception:
                weekly_data.append(0)
    except Exception:
        weekly_labels = []
        weekly_data = []

    # Monthly: last 12 months
    monthly_labels = []
    monthly_data = []
    try:
        for i in range(11, -1, -1):
            ref = (today.replace(day=1) - datetime.timedelta(days=1)) - datetime.timedelta(days=30 * i)
            year = ref.year
            month = ref.month
            monthly_labels.append(ref.strftime('%b'))
            qs = Order.objects.filter(
                Q(delivered_at__year=year, delivered_at__month=month) | (Q(status='done') & Q(created_at__year=year, created_at__month=month))
            )
            total = qs.aggregate(total=Sum('payment_amount'))
            val = total.get('total')
            if not val:
                val = qs.count()
            try:
                monthly_data.append(int(val))
            except Exception:
                monthly_data.append(0)
    except Exception:
        monthly_labels = []
        monthly_data = []

    # Top couriers: percentage score relative to top performer (use delivered counts)
    top_couriers = []
    try:
        qs = (
            Order.objects.filter(status='done')
            .values('courier__id', 'courier__full_name')
            .annotate(delivered=Count('id'))
            .order_by('-delivered')[:5]
        )
        max_delivered = 0
        for i, t in enumerate(qs):
            if i == 0:
                max_delivered = t.get('delivered', 0) or 0
            top_couriers.append({'id': t.get('courier__id'), 'name': t.get('courier__full_name') or '—', 'delivered': t.get('delivered', 0)})
        for c in top_couriers:
            try:
                c['score'] = int((c['delivered'] / max_delivered) * 100) if max_delivered else 0
            except Exception:
                c['score'] = 0
    except Exception:
        top_couriers = []

    context = {
        'weekly_labels_json': json.dumps(weekly_labels, ensure_ascii=False),
        'weekly_data_json': json.dumps(weekly_data),
        'monthly_labels_json': json.dumps(monthly_labels, ensure_ascii=False),
        'monthly_data_json': json.dumps(monthly_data),
        'top_couriers': top_couriers,
    }
    return render(request, 'admin/reports.html', context)


def courier_ranking_view(request):
    """Show courier ranking based on number of delivered orders."""
    try:
        qs = (
            Order.objects.filter(status='done')
            .values('courier__id', 'courier__full_name')
            .annotate(delivered=Count('id'))
            .order_by('-delivered')
        )
        ranking = []
        max_delivered = 0
        for i, t in enumerate(qs):
            if i == 0:
                max_delivered = t.get('delivered', 0) or 0
            ranking.append({
                'id': t.get('courier__id'),
                'name': t.get('courier__full_name') or '—',
                'delivered': t.get('delivered', 0),
            })
    except Exception:
        ranking = []
        max_delivered = 0

    # compute score percent relative to top performer
    for r in ranking:
        try:
            r['score_percent'] = int((r['delivered'] / max_delivered) * 100) if max_delivered else 0
        except Exception:
            r['score_percent'] = 0

    return render(request, 'admin/courier_ranking.html', {'ranking': ranking})


def debtors_view(request):
    """Show clients with outstanding debt as profile cards.

    This view lists `Client` records with `debt > 0`. For each client we include:
    - last order id (if any)
    - user id label
    - phone
    - courier who served last order (if any)
    - debt amount
    - status (derived from last order)
    - days overdue (based on client's last_order timestamp if available)
    """
    from django.utils import timezone

    title = 'Qarzdorlar'
    # Exclude obvious test/sample names (e.g. names starting with 'Mijoz')
    # so the debtors page doesn't show statically-added sample records.
    clients_qs = Client.objects.filter(debt__gt=0).exclude(full_name__startswith='Mijoz').select_related('region')
    debtors = []
    now = timezone.now()
    # load static CSV mapping (phone -> csv name) to prefer CSV name when available
    try:
        static_regions = read_csv_data()
    except Exception:
        static_regions = []

    # build mapping from CSV region name -> CSV location (address)
    static_location_map = { r.get('name'): r.get('location') for r in static_regions }

    def _normalize_to_998(raw_digits: str):
        """Normalize any digits string to the form '998' + 9 local digits (12 digits total).
        Returns the normalized digits (without '+') or None if not possible.
        Strategy: take the last 9 digits as local number and prepend '998'.
        """
        if not raw_digits:
            return None
        d = ''.join(ch for ch in raw_digits if ch.isdigit())
        if len(d) < 9:
            return None
        last9 = d[-9:]
        std = '998' + last9
        if len(std) == 12:
            return std
        return None

    csv_phone_map = {}
    for r in static_regions:
        p = (r.get('phone') or '').strip()
        norm = _normalize_to_998(p)
        if norm:
            csv_phone_map[norm] = r.get('name')

    # build a fallback mapping by last-6-digits to catch phones with different formatting
    csv_phone_by_last6 = {}
    for r in static_regions:
        p = ''.join(ch for ch in (r.get('phone') or '') if ch.isdigit())
        if len(p) >= 6:
            csv_phone_by_last6[p[-6:]] = r.get('name')

    # Prefer real couriers from DB; fallback to a small static list if none
    try:
        couriers_qs = list(Courier.objects.all())
        if couriers_qs:
            couriers_list = [{'name': c.full_name, 'phone': getattr(c, 'phone', '-') } for c in couriers_qs]
        else:
            couriers_list = [
                {'name': 'Oybek Kurye', 'phone': '+998901112233'},
                {'name': 'Aziz Kurye', 'phone': '+998902223344'},
                {'name': 'Dilorom Kurye', 'phone': '+998903334455'},
            ]
    except Exception:
        couriers_list = [
            {'name': 'Oybek Kurye', 'phone': '+998901112233'},
            {'name': 'Aziz Kurye', 'phone': '+998902223344'},
            {'name': 'Dilorom Kurye', 'phone': '+998903334455'},
        ]

    for c in clients_qs:
        last_order = Order.objects.filter(client=c).order_by('-created_at').first()
        order_id = last_order.id if last_order else None
        # Determine courier info: prefer order.courier if present, otherwise pick a static courier
        if last_order and last_order.courier:
            courier_name = last_order.courier.full_name
            courier_phone = getattr(last_order.courier, 'phone', '-')
        else:
            # pick a courier deterministically by client id from the DB-derived list
            sc = couriers_list[c.id % len(couriers_list)]
            courier_name = sc['name']
            courier_phone = sc['phone']
        # determine status label
        if last_order:
            st = last_order.status
            if st == 'done':
                s_label = 'Yetkazildi'
            elif st in ('delivering', 'assigned'):
                s_label = 'Jarayonda'
            else:
                s_label = 'Berilmadi'
        else:
            s_label = ''

        # days overdue: compare now and client's last_order
        days_overdue = 0
        if getattr(c, 'last_order', None):
            try:
                delta = now.date() - c.last_order.date()
                days_overdue = delta.days
            except Exception:
                days_overdue = 0

        # Format phone: normalize to +998XXXXXXXXX (13 chars including '+') when possible
        raw_phone = (c.phone or '')
        norm = _normalize_to_998(raw_phone)
        if norm:
            formatted_phone = '+' + norm
        else:
            # fallback: strip non-digits and show what's available
            digits = ''.join(ch for ch in raw_phone if ch.isdigit())
            formatted_phone = digits or raw_phone

        # If CSV has a name for this phone, prefer it. Also try last-6-digits fallback.
        csv_name = None
        if norm and norm in csv_phone_map:
            csv_name = csv_phone_map.get(norm)
        else:
            # try fallback by last-6-digits
            digits_only = ''.join(ch for ch in raw_phone if ch.isdigit())
            if len(digits_only) >= 6:
                last6 = digits_only[-6:]
                if last6 in csv_phone_by_last6:
                    csv_name = csv_phone_by_last6.get(last6)

        # If we found a better name in CSV and client currently has a generic 'Mijoz N' name, update DB
        try:
            if csv_name and (c.full_name.startswith('Mijoz') or c.full_name.strip() == ''):
                c.full_name = csv_name
                c.save()
        except Exception:
            # If save fails for any reason, continue without interrupting the listing
            pass

        # determine address: prefer CSV location for client's region name
        address = ''
        if c.region:
            address = static_location_map.get(c.region.name) or getattr(c.region, 'name', '')

        # last order date (when they took the last order)
        last_order_date = ''
        if last_order and getattr(last_order, 'created_at', None):
            try:
                last_order_date = last_order.created_at.strftime('%Y-%m-%d %H:%M')
            except Exception:
                last_order_date = str(last_order.created_at)

        debtors.append({
            'client_id': c.id,
            'order_id': order_id,
            'user_id': f"u_{c.id}",
            'name': csv_name or c.full_name,
            'phone': formatted_phone,
                'courier': courier_name,
                'courier_phone': courier_phone,
            'debt': getattr(c, 'debt', 0),
            'status_label': s_label,
            'days_overdue': days_overdue,
            'address': address,
            'last_order_date': last_order_date,
        })

    # Pop any flash message set by previous actions (e.g., mark_debtor_paid)
    flash_message = request.session.pop('flash_message', None)
    flash_type = request.session.pop('flash_type', None)
    return render(request, 'admin/debtors.html', {'debtors': debtors, 'title': title, 'flash_message': flash_message, 'flash_type': flash_type})


def mark_debtor_paid(request, client_id):
    if request.method == 'POST':
        try:
            client = Client.objects.get(pk=client_id)
            client.debt = 0
            client.save()
            request.session['flash_message'] = f"{client.full_name} - qarz to'landi."
            request.session['flash_type'] = 'success'
        except Client.DoesNotExist:
            request.session['flash_message'] = 'Mijoz topilmadi.'
            request.session['flash_type'] = 'danger'
    return redirect('debtors_view')


def inactive_clients_view(request):
    """List clients who have not had an order for `cutoff_days` or more.

    Default cutoff is 30 days, but can be overridden with ?cutoff=<days>.
    """
    from django.utils import timezone

    try:
        cutoff_days = int(request.GET.get('cutoff', 30))
    except Exception:
        cutoff_days = 30

    cutoff_date = timezone.now() - datetime.timedelta(days=cutoff_days)

    # Select clients whose last_order is null (never ordered) or older than cutoff
    try:
        qs = Client.objects.filter(Q(last_order__isnull=True) | Q(last_order__lte=cutoff_date)).order_by('last_order')[:100]
    except Exception:
        qs = Client.objects.none()

    clients = []
    now = timezone.now()
    for c in qs:
        if getattr(c, 'last_order', None):
            try:
                last_date = c.last_order.strftime('%Y-%m-%d')
                days_since = (now.date() - c.last_order.date()).days
            except Exception:
                last_date = str(c.last_order)
                days_since = None
        else:
            last_date = None
            days_since = None

        phone = c.phone or ''
        clients.append({
            'client_id': c.id,
            'name': c.full_name,
            'phone': phone,
            'last_order_date': last_date,
            'days_since': days_since,
        })

    return render(request, 'admin/inactive_clients.html', {'clients': clients, 'cutoff_days': cutoff_days})


@csrf_exempt
def delete_order(request, order_id):
    """Delete an order by ID."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=400)
    
    try:
        order = Order.objects.get(pk=order_id)
        order.delete()
        return JsonResponse({'status': 'ok', 'message': 'Buyurtma o\'chirildi'})
    except Order.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Buyurtma topilmadi'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
