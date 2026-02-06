from django.shortcuts import redirect, render
from django.contrib import auth
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.http import HttpResponse, JsonResponse
import os

from suv_tashish_crm.models import Courier, Client, Region, Admin, Notification
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from django.db import transaction
from .models import UserProfile
import uuid, csv
try:
    from admin_panel.views import BASE_DIR
except Exception:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
from django.conf import settings
import re
from django.utils import timezone
from suv_tashish_crm.telegram import send_telegram


def redirect_to_admin_dashboard(request):
    return redirect('/admin_panel/dashboard/')


def login_view(request):
    """Custom login supporting roles: admin, courier, client."""
    # If user hasn't chosen a language yet, force chooser first
    try:
        if not request.session.get('lang'):
            return redirect('choose_language')
    except Exception:
        pass
    # load CSV locations for client region select
    try:
        from admin_panel.views import read_csv_data
        static_regions = read_csv_data()
        locations = []
        seen = set()
        for r in static_regions:
            loc = (r.get('location') or '').strip()
            if loc and loc not in seen:
                seen.add(loc)
                locations.append(loc)
    except Exception:
        locations = []

    error = None
    if request.method == 'POST':
        role = request.POST.get('role')
        # (no OTP verification here; handle login actions directly)
        # helper validators
        def is_valid_name(s):
            if not s:
                return False
            for ch in s:
                if ch.isalpha() or ch in " -'":
                    continue
                return False
            return True

        def is_valid_phone(p):
            return bool(re.match(r'^\+998\d{9}$', p))
        if role == 'admin':
            username = request.POST.get('username') or ''
            password = request.POST.get('password') or ''
            # optional admin display info
            admin_name = (request.POST.get('admin_name') or '').strip()
            admin_phone = (request.POST.get('admin_phone') or '').strip()
            user = authenticate(request, username=username, password=password)
            if user is not None:
                auth_login(request, user)
                request.session['role'] = 'admin'
                # persist admin display info in DB/session if provided or infer from Django user
                try:
                    # choose a display name and phone from POST or Django user
                    display_name = admin_name or (user.get_full_name() if hasattr(user, 'get_full_name') and user.get_full_name() else user.username)
                    display_phone = admin_phone or ''
                    # Prefer creating/finding by phone when provided to avoid duplicates
                    if display_phone:
                        admin_obj, _ = Admin.objects.get_or_create(phone=display_phone, defaults={'full_name': display_name})
                    else:
                        admin_obj, _ = Admin.objects.get_or_create(full_name=display_name, defaults={'phone': display_phone})
                    # ensure name is set
                    if admin_obj.full_name.strip() == '':
                        admin_obj.full_name = display_name
                        admin_obj.save()
                    request.session['admin_name'] = admin_obj.full_name or display_name
                    request.session['admin_phone'] = admin_obj.phone or display_phone
                except Exception:
                    # be tolerant on any DB issues in dev; still set session values
                    request.session['admin_name'] = admin_name or (user.username if hasattr(user, 'username') else '')
                    request.session['admin_phone'] = admin_phone or ''
                # notify Telegram channel about admin login (non-blocking)
                try:
                    when = timezone.localtime().strftime('%Y-%m-%d %H:%M:%S')
                    device = request.META.get('HTTP_USER_AGENT', 'Unknown')
                    name = (user.get_full_name() if hasattr(user, 'get_full_name') and user.get_full_name() else user.username)
                    phone = request.session.get('admin_phone', '') or ''
                    uid = getattr(user, 'username', '') or ''
                    text = (
                        f"🔔 Yangi login\n"
                        f"Role: Admin\n"
                        f"Time: {when}\n"
                        f"Device: {device}\n"
                        f"Name: {name}\n"
                        f"Phone: {phone}\n"
                        f"ID: {uid}"
                    )
                    send_telegram(text)
                except Exception:
                    pass
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'ok', 'next': '/admin_panel/dashboard/'})
                return redirect('/admin_panel/dashboard/')
            else:
                # Dev fallback: allow hardcoded admin/admin when DEBUG or ALLOW_DEV_ADMIN env set
                allow_dev = getattr(settings, 'DEBUG', False) or os.environ.get('ALLOW_DEV_ADMIN') == '1'
                if allow_dev and username == 'admin' and password == 'admin':
                    # set session as admin without Django auth (dev only)
                    request.session['role'] = 'admin'
                    request.session['dev_admin'] = True
                    # persist admin display info from form when dev fallback used
                    admin_name = (request.POST.get('admin_name') or '').strip()
                    admin_phone = (request.POST.get('admin_phone') or '').strip()
                    try:
                        if admin_name:
                            if admin_phone:
                                admin_obj, _ = Admin.objects.get_or_create(phone=admin_phone, defaults={'full_name': admin_name})
                            else:
                                admin_obj, _ = Admin.objects.get_or_create(full_name=admin_name, defaults={'phone': ''})
                            if admin_obj.full_name.strip() == '':
                                admin_obj.full_name = admin_name
                                admin_obj.save()
                            request.session['admin_name'] = admin_obj.full_name or admin_name
                            request.session['admin_phone'] = admin_obj.phone or ''
                    except Exception:
                        request.session['admin_name'] = admin_name
                    # notify Telegram about dev-admin fallback login
                    try:
                        when = timezone.localtime().strftime('%Y-%m-%d %H:%M:%S')
                        device = request.META.get('HTTP_USER_AGENT', 'Unknown')
                        name = admin_name or username
                        phone = admin_phone or ''
                        uid = 'dev-admin'
                        text = (
                            f"🔔 Yangi login\n"
                            f"Role: Admin (DEV)\n"
                            f"Time: {when}\n"
                            f"Device: {device}\n"
                            f"Name: {name}\n"
                            f"Phone: {phone}\n"
                            f"ID: {uid}"
                        )
                        send_telegram(text)
                    except Exception:
                        pass
                    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                        return JsonResponse({'status': 'ok', 'next': '/admin_panel/dashboard/'})
                    return redirect('/admin_panel/dashboard/')
                # Scope admin auth errors to admin panel when login originated there.
                msg = 'Admin login yoki parol noto‘g‘ri.'
                referer = request.META.get('HTTP_REFERER', '') or ''
                # If the request came from admin area, put the message into session
                # so it will be shown on admin pages instead of the generic login page.
                if '/admin_panel/' in referer or request.POST.get('admin_origin') == '1':
                    try:
                        request.session['admin_login_error'] = msg
                    except Exception:
                        pass
                    # For AJAX, return JSON error; otherwise redirect back to admin area
                    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                        return JsonResponse({'status': 'error', 'message': msg})
                    next_url = referer if referer and '/admin_panel/' in referer else '/admin_panel/dashboard/'
                    return redirect(next_url)
                error = msg

        elif role == 'courier':
            name = (request.POST.get('courier_name') or '').strip()
            phone = (request.POST.get('courier_phone') or '').strip()
            if not name or not phone:
                error = 'Iltimos ism va telefon kiriting.'
            else:
                if not is_valid_name(name):
                    error = "Ism noto‘g‘ri — faqat harflar va bo'sh joy ruxsat etiladi."
                elif not is_valid_phone(phone):
                    error = "Telefon formati xato — +998XXXXXXXXX ko'rinishida bo'lsin."
            if not error:
                # try find or create courier by phone
                courier, created = Courier.objects.get_or_create(phone=phone, defaults={'full_name': name})
                if not created and (not courier.full_name or courier.full_name.strip() == ''):
                    courier.full_name = name
                    courier.save()
                request.session['role'] = 'courier'
                request.session['courier_id'] = courier.id
                # store display values for templates
                try:
                    request.session['courier_name'] = courier.full_name or ''
                    request.session['courier_phone'] = courier.phone or ''
                except Exception:
                    pass
                # notify Telegram about courier login
                try:
                    when = timezone.localtime().strftime('%Y-%m-%d %H:%M:%S')
                    device = request.META.get('HTTP_USER_AGENT', 'Unknown')
                    cname = request.session.get('courier_name') or courier.full_name or name
                    cphone = request.session.get('courier_phone') or courier.phone or phone
                    cuid = getattr(courier, 'id', '')
                    text = (
                        f"🔔 Yangi login\n"
                        f"Role: Courier\n"
                        f"Time: {when}\n"
                        f"Device: {device}\n"
                        f"Name: {cname}\n"
                        f"Phone: {cphone}\n"
                        f"ID: {cuid}"
                    )
                    send_telegram(text)
                except Exception:
                    pass
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'ok', 'next': '/courier_panel/dashboard/'})
                return redirect('/courier_panel/dashboard/')

        elif role == 'client':
            name = (request.POST.get('client_name') or '').strip()
            # accept either client_phone or phone POST key
            phone = (request.POST.get('client_phone') or request.POST.get('phone') or '').strip()
            # accept location posted from device (fields added by JS)
            lat = (request.POST.get('location_lat') or request.POST.get('lat') or '').strip()
            lon = (request.POST.get('location_lon') or request.POST.get('lon') or '').strip()
            # No manual region selection required: we will try to infer region from lat/lon
            if not name or not phone:
                error = 'Iltimos ism va telefon kiriting.'
            else:
                if not is_valid_name(name):
                    error = "Ism noto‘g‘ri — faqat harflar va bo'sh joy ruxsat etiladi."
                elif not is_valid_phone(phone):
                    error = "Telefon formati xato — +998XXXXXXXXX ko'rinishida bo'lsin."
            if not error:
                # create or get client by phone; we'll update region/location after
                client, created = Client.objects.get_or_create(phone=phone, defaults={'full_name': name, 'location_lat': 0.0, 'location_lon': 0.0})
                if not created:
                    # update name if missing
                    updated = False
                    if not client.full_name or client.full_name.strip() == '':
                        client.full_name = name
                        updated = True
                    if updated:
                        client.save()
                # if we received lat/lon, attempt to save and reverse-geocode into Region
                region_obj = None
                try:
                    if lat and lon:
                        try:
                            client.location_lat = float(lat)
                            client.location_lon = float(lon)
                        except Exception:
                            # ignore parsing errors
                            pass
                        # attempt to reverse geocode to a human-readable region/address
                        try:
                            from geopy.geocoders import Nominatim
                            geolocator = Nominatim(user_agent='crm_app')
                            loc = geolocator.reverse(f"{lat},{lon}", language='en')
                            if loc and loc.address:
                                addr = loc.address
                                region_obj, _ = Region.objects.get_or_create(name=addr)
                        except Exception:
                            region_obj = None
                except Exception:
                    region_obj = None
                # if reverse-geocode didn't yield a region but a Region exists for client, keep it; otherwise leave null
                try:
                    if region_obj:
                        client.region = region_obj
                    client.save()
                except Exception:
                    pass
                # If newly created, generate a unique customer_id, split names, append to CSV and notify admin
                if created:
                    try:
                        # generate short unique customer id
                        cid = 'C' + uuid.uuid4().hex[:10].upper()
                        client.customer_id = cid
                        # try split name into first/last
                        parts = name.split()
                        if len(parts) > 1:
                            client.first_name = parts[0]
                            client.last_name = ' '.join(parts[1:])
                        else:
                            client.first_name = name
                            client.last_name = ''
                        client.save()
                        # append to Volidam.csv (name, bottle, location, phone) - bottle blank, location from region (if available)
                        try:
                            csv_path = os.path.join(BASE_DIR, 'Volidam.csv')
                            file_exists = os.path.exists(csv_path)
                            with open(csv_path, 'a', encoding='utf-8', newline='') as f:
                                writer = csv.writer(f)
                                if not file_exists:
                                    writer.writerow(['name', 'bottle', 'location', 'phone'])
                                writer.writerow([client.full_name or '', '', client.region.name if client.region else '', client.phone or ''])
                        except Exception:
                            pass
                        # create admin notification
                        try:
                            Notification.objects.create(title='Yangi mijoz qo\'shildi', message=f'Yangi mijoz: {client.full_name} ({client.phone}) — ID: {client.customer_id}')
                        except Exception:
                            pass
                    except Exception:
                        pass

                request.session['role'] = 'client'
                request.session['client_id'] = client.id
                # expose customer_id to session for client dashboard templates
                try:
                    if getattr(client, 'customer_id', None):
                        request.session['customer_id'] = client.customer_id
                except Exception:
                    pass
                # notify Telegram about client login
                try:
                    when = timezone.localtime().strftime('%Y-%m-%d %H:%M:%S')
                    device = request.META.get('HTTP_USER_AGENT', 'Unknown')
                    cname = client.full_name or name
                    cphone = client.phone or phone
                    cid = getattr(client, 'customer_id', '') or request.session.get('customer_id', '') or getattr(client, 'id', '')
                    text = (
                        f"🔔 Yangi login\n"
                        f"Role: Client\n"
                        f"Time: {when}\n"
                        f"Device: {device}\n"
                        f"Name: {cname}\n"
                        f"Phone: {cphone}\n"
                        f"ID: {cid}"
                    )
                    send_telegram(text)
                except Exception:
                    pass
                # If client hasn't agreed to contract yet, send them to contract page first
                next_url = '/client_panel/dashboard/'
                try:
                    if not getattr(client, 'agreed_to_contract', False):
                        next_url = '/client_panel/contract/'
                except Exception:
                    pass
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'ok', 'next': next_url})
                return redirect(next_url)
        else:
            error = 'Iltimos ro‘yni tanlang.'

    # If AJAX request and there was an error, return JSON error
    if request.headers.get('x-requested-with') == 'XMLHttpRequest' and error:
        return JsonResponse({'status': 'error', 'message': error})

    ctx = {'locations': locations, 'error': error}
    # prefill possible values from POST or session
    ctx['admin_name'] = (request.POST.get('admin_name') if request.method == 'POST' else request.session.get('admin_name'))
    ctx['admin_phone'] = (request.POST.get('admin_phone') if request.method == 'POST' else request.session.get('admin_phone'))
    ctx['courier_name'] = (request.POST.get('courier_name') if request.method == 'POST' else request.session.get('courier_name'))
    ctx['phone'] = (request.POST.get('courier_phone') if request.method == 'POST' else request.session.get('courier_phone'))
    return render(request, 'login.html', ctx)


def logout_view(request):
    # Log out Django auth user and clear our role/session keys, then redirect to login
    try:
        auth_logout(request)
    except Exception:
        pass
    for k in ['role', 'courier_id', 'client_id', 'courier_name', 'courier_phone', 'admin_name', 'admin_phone']:
        if k in request.session:
            try:
                del request.session[k]
            except Exception:
                pass
    return redirect('/login/')


def register_view(request):
    """Unified registration for admin, courier, client.

    Creates a Django `User`, a `UserProfile` with `role`, and a corresponding
    domain object (Admin, Courier, Client in suv_tashish_crm.models).
    """
    error = None
    if request.method == 'POST':
        role = request.POST.get('role')
        username = (request.POST.get('username') or '').strip()
        password = (request.POST.get('password') or '').strip()
        full_name = (request.POST.get('full_name') or '').strip()
        phone = (request.POST.get('phone') or '').strip()

        if not role or role not in ('admin', 'courier', 'client'):
            error = 'Iltimos ro\'lni tanlang.'
        elif not username or not password:
            error = 'Username va parol talab qilinadi.'
        else:
            UserModel = get_user_model()
            if UserModel.objects.filter(username=username).exists():
                error = 'Bu username allaqachon mavjud.'
            else:
                try:
                    with transaction.atomic():
                        user = UserModel.objects.create(username=username)
                        user.set_password(password)
                        # optional: set first/last name when full_name provided
                        if full_name:
                            parts = full_name.split()
                            user.first_name = parts[0]
                            if len(parts) > 1:
                                user.last_name = ' '.join(parts[1:])
                        user.save()
                        # create profile
                        prof = UserProfile.objects.create(user=user, role=role)
                        # create domain-specific profile in this app for backward compatibility
                        if role == 'admin':
                            Admin.objects.create(user=user, full_name=full_name or username, phone=phone)
                        elif role == 'courier':
                            Courier.objects.create(user=user, full_name=full_name or username, phone=phone)
                        elif role == 'client':
                            # suv_tashish_crm.Client requires location_lat/location_lon; set defaults
                            created_client = Client.objects.create(full_name=full_name or username, phone=phone or '', location_lat=0.0, location_lon=0.0)
                except Exception as e:
                    error = 'Ro\'yxatdan o\'tishda xatolik yuz berdi.'
        if not error:
            # If a client was just created, send them to contract page to accept terms
            try:
                if role == 'client' and 'created_client' in locals():
                    request.session['role'] = 'client'
                    request.session['client_id'] = created_client.id
                    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                        return JsonResponse({'status': 'ok', 'next': '/client_panel/contract/'})
                    return redirect('/client_panel/contract/')
            except Exception:
                pass
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'status': 'ok', 'next': '/login/'})
            return redirect('/login/')

    return render(request, 'register.html', {'error': error})


def set_language(request):
    """Simple view to set session language. Accepts POST or GET `lang` value and redirects back."""
    lang = request.POST.get('lang') or request.GET.get('lang')
    if lang in ('uz_lat', 'uz_cyrl', 'ru', 'en'):
        try:
            request.session['lang'] = lang
            # mark that user has explicitly chosen a language
            request.session['language_chosen'] = True
        except Exception:
            pass
    # Redirect back to Referer or root
    next_url = request.META.get('HTTP_REFERER') or '/'
    return redirect(next_url)


def choose_language(request):
    """Render a simple language picker. On POST, set session lang and redirect to login.

    This view is used as the root entry so users select the UI language first.
    """
    # Known codes accepted by our app (session keys used by language_context)
    valid_codes = ('uz_lat', 'uz_cyrl', 'ru', 'en')
    if request.method == 'POST':
        lang = (request.POST.get('lang') or '').strip()
        if lang in valid_codes:
            try:
                request.session['lang'] = lang
                request.session['language_chosen'] = True
            except Exception:
                pass
        return redirect('/login/')

    # Do NOT auto-accept GET lang queries here — require explicit POST from chooser

    # If user already chose language earlier, skip chooser and go to login
    if request.session.get('language_chosen'):
        return redirect('/login/')

    # Render a minimal chooser; labels come from language files for preview
    # We intentionally pass LANG_OPTIONS from context processor in templates.
    return render(request, 'choose_language.html', {})


def change_language(request):
    """Clear the language_chosen flag so chooser will be shown, then redirect to chooser.

    This is used from the login page 'Change language' link: it forces the language chooser
    even if the user previously chose a language.
    """
    try:
        if 'language_chosen' in request.session:
            del request.session['language_chosen']
    except Exception:
        pass
    return redirect('choose_language')

