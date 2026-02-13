from __future__ import annotations
import uuid
import random
import json
import math
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from django.contrib.auth.models import Group, User
from django.core.exceptions import FieldDoesNotExist
from django.contrib.auth import get_user_model
from django.db.models import Sum, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from suv_tashish_crm.models import Order, Courier, Client, Notification, Region
from admin_panel.models import AdminProfile
from .serializers import OrderSerializer

User = get_user_model()

ORDER_STATUSES = ("pending", "assigned", "delivering", "done")

# ================= HELPERS (O'zgartirmang) =================
def _has_field(model_cls, field_name: str) -> bool:
    try:
        model_cls._meta.get_field(field_name)
        return True
    except FieldDoesNotExist:
        return False

# ================= HELPERS =================
ADMIN_OTP_TTL_SECONDS = 10 * 60          # 10 min
ADMIN_VERIFY_TTL_SECONDS = 15 * 60       # 15 min
ADMIN_RESET_CACHE_PREFIX = "admin_reset:"
ADMIN_RESET_VERIFIED_PREFIX = "admin_reset_verified:"

def _admin_exists() -> bool:
    return User.objects.filter(
        Q(is_staff=True) | Q(is_superuser=True) | Q(groups__name="admin")
    ).distinct().exists()

def _get_bootstrap_key() -> str:
    # settings.py da ADMIN_BOOTSTRAP_KEY yo'q bo'lsa, bo'sh string qaytaradi
    return getattr(settings, "ADMIN_BOOTSTRAP_KEY", "") or ""

def _rand_code6() -> str:
    return f"{random.randint(0, 999999):06d}"
def _to_int_amount(value, default: int = 0) -> int:
    if value is None:
        return default
    try:
        return int(float(value))
    except Exception:
        return default


# ================= ROLE =================
def get_role(user) -> str:
    if not user or not user.is_authenticated:
        return "CLIENT"
    
    groups = set(user.groups.values_list("name", flat=True))
    if "admin" in groups or user.is_superuser or user.is_staff:
        return "ADMIN"
    
    if "courier" in groups or Courier.objects.filter(user=user).exists():
        return "COURIER"
    
    return "CLIENT"

def _require_admin(request):
    if get_role(request.user) != "ADMIN":
        return Response({"detail": "FORBIDDEN_ADMIN_REQUIRED"}, status=403)
    return None

def _require_courier(request):
    if get_role(request.user) != "COURIER":
        return Response({"detail": "FORBIDDEN_COURIER_REQUIRED"}, status=403)
    return None

def _require_client(request):
    if get_role(request.user) != "CLIENT":
        return Response({"detail": "FORBIDDEN_CLIENT_REQUIRED"}, status=403)
    return None

# ================= ME =================
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me_view(request):
    user = request.user
    role = get_role(user)
    must_change = False
    try:
        if role == "CLIENT":
            c = _get_client_linked(user)
            must_change = bool(getattr(c, "must_change_password", False)) if c else False
        elif role == "COURIER":
            q = _get_courier_linked(user)
            must_change = bool(getattr(q, "must_change_password", False)) if q else False
    except Exception:
        must_change = False

    return Response({
        "user_id": user.id,
        "username": user.get_username(),
        "role": role,
        "must_change_password": must_change,
    })

# ================= CHECK =================
@api_view(["GET"])
@permission_classes([AllowAny])
def check_status(request):
    return Response({
        "status": "online",
        "message": "CRM Suv tizimiga muvaffaqiyatli ulandingiz!",
        "server_ip": "192.168.13.8",
    })
@api_view(["POST"])
@permission_classes([AllowAny])
def admin_recovery_start_view(request):
    """
    Flow A:
    - Agar admin umuman yo'q bo'lsa: company_key talab qilinmaydi
    - Admin mavjud bo'lsa: company_key == settings.ADMIN_BOOTSTRAP_KEY bo'lishi shart
    """
    data = request.data or {}

    full_name = (data.get("full_name") or "").strip()
    phone = (data.get("phone") or "").strip()
    email = (data.get("email") or "").strip().lower()
    company_key = (data.get("company_key") or "").strip()

    if not full_name or not phone or not email:
        return Response({"detail": "FULL_NAME_PHONE_EMAIL_REQUIRED"}, status=400)

    exists = _admin_exists()
    if exists:
        bootstrap_key = _get_bootstrap_key()
        if not bootstrap_key or company_key != bootstrap_key:
            return Response({"detail": "COMPANY_KEY_REQUIRED_OR_INVALID"}, status=403)

    request_id = uuid.uuid4().hex
    code = _rand_code6()

    cache_key = f"{ADMIN_RESET_CACHE_PREFIX}{request_id}"
    cache.set(
        cache_key,
        {
            "full_name": full_name,
            "phone": phone,
            "email": email,
            "code": code,
            "created_at": timezone.now().isoformat(),
            "admin_existed": exists,
        },
        timeout=ADMIN_OTP_TTL_SECONDS,
    )

    # Email yuborish (email backend sozlanmagan bo'lsa exception bo'lishi mumkin)
    try:
        subject = "CRM Suv — Admin tasdiqlash kodi"
        message = f"Admin tiklash kodi: {code}\nKod {ADMIN_OTP_TTL_SECONDS//60} daqiqa amal qiladi."
        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None)
        send_mail(subject, message, from_email, [email], fail_silently=False)
    except Exception as e:
        # kod cache'da turadi, lekin email ketmagan bo'lishi mumkin
        return Response({"detail": "EMAIL_SEND_FAILED", "error": str(e)}, status=500)

    return Response({"status": "ok", "request_id": request_id})


@api_view(["POST"])
@permission_classes([AllowAny])
def admin_recovery_verify_view(request):
    data = request.data or {}
    request_id = (data.get("request_id") or "").strip()
    code = (data.get("code") or "").strip()

    if not request_id or not code:
        return Response({"detail": "REQUEST_ID_AND_CODE_REQUIRED"}, status=400)

    cache_key = f"{ADMIN_RESET_CACHE_PREFIX}{request_id}"
    payload = cache.get(cache_key)
    if not payload:
        return Response({"detail": "REQUEST_EXPIRED_OR_NOT_FOUND"}, status=400)

    if str(payload.get("code")) != str(code):
        return Response({"detail": "INVALID_CODE"}, status=400)

    # verify_token: imzolangan token (15 min)
    signer = TimestampSigner(salt="admin-recovery")
    verify_token = signer.sign(request_id)

    verified_key = f"{ADMIN_RESET_VERIFIED_PREFIX}{request_id}"
    cache.set(verified_key, True, timeout=ADMIN_VERIFY_TTL_SECONDS)

    return Response({"status": "ok", "verify_token": verify_token})


@api_view(["POST"])
@permission_classes([AllowAny])
def admin_recovery_set_credentials_view(request):
    data = request.data or {}
    verify_token = (data.get("verify_token") or "").strip()
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "")

    if not verify_token or not username or not password:
        return Response({"detail": "VERIFY_TOKEN_USERNAME_PASSWORD_REQUIRED"}, status=400)

    # tokenni tekshiramiz (15 min ichida)
    signer = TimestampSigner(salt="admin-recovery")
    try:
        request_id = signer.unsign(verify_token, max_age=ADMIN_VERIFY_TTL_SECONDS)
    except SignatureExpired:
        return Response({"detail": "VERIFY_TOKEN_EXPIRED"}, status=400)
    except BadSignature:
        return Response({"detail": "VERIFY_TOKEN_INVALID"}, status=400)

    verified_key = f"{ADMIN_RESET_VERIFIED_PREFIX}{request_id}"
    if not cache.get(verified_key):
        return Response({"detail": "NOT_VERIFIED"}, status=400)

    cache_key = f"{ADMIN_RESET_CACHE_PREFIX}{request_id}"
    payload = cache.get(cache_key)
    if not payload:
        return Response({"detail": "REQUEST_EXPIRED_OR_NOT_FOUND"}, status=400)

    email = payload.get("email")
    full_name = payload.get("full_name") or ""
    phone = payload.get("phone") or ""

    # username band bo'lsa — 409
    existing_u = User.objects.filter(username=username).first()
    if existing_u and (not email or existing_u.email.lower() != str(email).lower()):
        return Response({"detail": "USERNAME_ALREADY_TAKEN"}, status=409)

    # user topamiz: email bo'yicha (agar bor bo'lsa)
    user = None
    if email:
        user = User.objects.filter(email__iexact=email).first()

    if user is None:
        # yangi user yaratamiz
        user = User(username=username, email=email)
    else:
        # mavjud userni adminga aylantiramiz + username yangilaymiz
        user.username = username
        if email:
            user.email = email

    user.set_password(password)
    user.is_staff = True
    user.save()

    # admin group
    try:
        g, _ = Group.objects.get_or_create(name="admin")
        user.groups.add(g)
    except Exception:
        pass

    # AdminProfile bo'lsa to'ldirib qo'yamiz (ixtiyoriy)
    try:
        ap, _ = AdminProfile.objects.get_or_create(user=user)
        if hasattr(ap, "full_name") and full_name:
            ap.full_name = full_name
        if hasattr(ap, "phone") and phone:
            ap.phone = phone
        if hasattr(ap, "email") and email:
            ap.email = email
        ap.save()
    except Exception:
        pass

    # bir martalik: tokenlarni o'chiramiz
    cache.delete(verified_key)
    cache.delete(cache_key)

    return Response({"status": "ok"})

# ================= OLD COURIER CLASSES (optional) =================
class CourierOrderListView(generics.ListAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Order.objects.all().order_by("-created_at")


class UpdateOrderStatusView(generics.UpdateAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def patch(self, request, *args, **kwargs):
        order = self.get_object()
        order.status = "done"
        order.save(update_fields=["status"])
        return Response({"message": "Buyurtma yakunlandi!"}, status=status.HTTP_200_OK)


# ================= ADMIN =================
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def admin_dashboard_view(request):
    forbidden = _require_admin(request)
    if forbidden:
        return forbidden
    my_business = _get_my_business(request.user)
    if not my_business:
        return Response({"detail": "Siz hech qanday biznesga biriktirilmagansiz!"}, status=403)
    today = timezone.localdate()

    today_orders = Order.objects.filter(business=my_business, created_at__date=today).count()
    pending_count = Order.objects.filter(
        business=my_business, 
        status__in=["assigned", "delivering"]
    ).count()

    active = Courier.objects.filter(business=my_business, is_active=True).count()
    total = Courier.objects.filter(business=my_business).count()

    revenue_qs = Order.objects.filter(
            business=my_business,  # 👈 FILTR
            status="done",
            created_at__date=today
    )
    agg = revenue_qs.aggregate(total=Sum("payment_amount"))
    today_revenue = _to_int_amount(agg.get("total"), 0)

    recent = Order.objects.filter(business=my_business).select_related("client").order_by("-created_at")[:8]
    recent_orders = []
    for o in recent:
        client_name = getattr(getattr(o, "client", None), "full_name", None) or "Mijoz"
        amount = _to_int_amount(getattr(o, "payment_amount", 0), 0)
        recent_orders.append({
            "id": o.id,
            "client_name": client_name,
            "status": getattr(o, "status", "") or "",
            "total": amount,
            "total_display": f"{amount} UZS",
        })

    return Response({
        "business_name": my_business.name,
        "today_orders": today_orders,
        "pending_count": pending_count,
        "active_couriers": {"active": active, "total": total},
        "today_revenue": today_revenue,
        "recent_orders": recent_orders,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def admin_orders_view(request):
    forbidden = _require_admin(request)
    if forbidden:
        return forbidden
    my_business = _get_my_business(request.user)
    q = (request.GET.get("q") or "").strip()
    st = (request.GET.get("status") or "").strip().lower()

    qs = Order.objects.filter(business=my_business).select_related("client", "courier").order_by("-created_at")

    if st:
        qs = qs.filter(status=st)

    if q:
        qs = qs.filter(
            Q(client__full_name__icontains=q) |
            Q(client__phone__icontains=q) |
            Q(id__icontains=q)
        )

    items = []
    for o in qs[:200]:
        client_name = getattr(o.client, "full_name", "Mijoz") if o.client else "Mijoz"
        phone = getattr(o.client, "phone", "") if o.client else ""
        courier_name = getattr(o.courier, "full_name", "") if o.courier else ""

        amount = _to_int_amount(getattr(o, "payment_amount", 0), 0)

        items.append({
            "id": o.id,
            "order_label": f"ORDER-{o.id}",
            "client_name": client_name,
            "client_phone": phone,
            "courier_name": courier_name,
            "status": getattr(o, "status", "") or "",
            "bottle_count": getattr(o, "bottle_count", 0),
            "amount": amount,
            "amount_display": f"{amount} UZS",
            "payment_type": (getattr(o, "payment_type", "") or "").strip(),
            "address": (getattr(o, "client_note", "") or "").strip(),
            "created_at": o.created_at.isoformat() if getattr(o, "created_at", None) else None,
        })

    return Response({"results": items})


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def admin_order_done_view(request, pk: int):
    forbidden = _require_admin(request)
    if forbidden:
        return forbidden

    o = get_object_or_404(Order, pk=pk)
    o.status = "done"
    o.save(update_fields=["status"])
    return Response({"ok": True, "id": o.id, "status": o.status})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def admin_couriers_view(request):
    forbidden = _require_admin(request)
    if forbidden:
        return forbidden
    my_business = _get_my_business(request.user)
    qs = Courier.objects.filter(business=my_business).select_related("region").all().order_by("full_name")
    items = []
    for c in qs:
        items.append({
            "id": c.id,
            "full_name": c.full_name,
            "phone": getattr(c, "phone", "") or "",
            "is_active": bool(getattr(c, "is_active", False)),
            "region": getattr(getattr(c, "region", None), "name", "") or "",
        })
    return Response({"results": items})


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def admin_courier_toggle_view(request, pk: int):
    forbidden = _require_admin(request)
    if forbidden:
        return forbidden

    c = get_object_or_404(Courier, pk=pk)
    c.is_active = not bool(getattr(c, "is_active", False))
    c.save(update_fields=["is_active"])
    return Response({"ok": True, "id": c.id, "is_active": c.is_active})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def admin_debtors_view(request):
    forbidden = _require_admin(request)
    if forbidden:
        return forbidden
    my_business = _get_my_business(request.user)
    qs = Client.objects.filter(business=my_business, debt__gt=0).order_by("-debt")
    items = []
    for c in qs:
        debt_int = _to_int_amount(getattr(c, "debt", 0), 0)
        items.append({
            "id": c.id,
            "full_name": getattr(c, "full_name", "") or "",
            "phone": getattr(c, "phone", "") or "",
            "region": getattr(getattr(c, "region", None), "name", "") or "",
            "debt": debt_int,
            "debt_display": f"-{debt_int} UZS",
        })

    total_debt = sum(i["debt"] for i in items)
    return Response({"total_debt": total_debt, "results": items})


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def admin_debtor_paid_view(request, pk: int):
    forbidden = _require_admin(request)
    if forbidden:
        return forbidden

    c = get_object_or_404(Client, pk=pk)
    c.debt = 0
    c.save(update_fields=["debt"])
    return Response({"ok": True, "id": c.id, "debt": 0})


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def admin_profile_view(request):
    forbidden = _require_admin(request)
    if forbidden:
        return forbidden

    user = request.user
    profile, _ = AdminProfile.objects.get_or_create(user=user, defaults={"phone": ""})

    if request.method == "GET":
        return Response({
            "id": user.id,
            "username": user.username,
            "email": user.email or "",
            "full_name": user.get_full_name() or user.username,
            "phone": getattr(profile, "phone", "") or "",
            "role": "Administrator",
        })

    data = request.data or {}

    new_username = (data.get("username") or "").strip()
    if new_username and new_username != user.username:
        if User.objects.filter(username=new_username).exclude(id=user.id).exists():
            return Response({"detail": "USERNAME_TAKEN"}, status=status.HTTP_400_BAD_REQUEST)
        user.username = new_username

    new_email = (data.get("email") or "").strip()
    if new_email:
        user.email = new_email

    new_password = (data.get("password") or "").strip()
    if new_password:
        if len(new_password) < 8:
            return Response({"detail": "PASSWORD_TOO_SHORT"}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(new_password)

    user.save()

    profile.phone = (data.get("phone") or "").strip()
    profile.save(update_fields=["phone"])

    return Response({"ok": True})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def admin_notifications_view(request):
    forbidden = _require_admin(request)
    if forbidden:
        return forbidden

    base_qs = Notification.objects.all().order_by("-created_at")
    unseen = base_qs.filter(seen=False).count()
    qs = base_qs[:50]

    items = []
    for n in qs:
        items.append({
            "id": n.id,
            "title": (getattr(n, "title", "") or "Notification"),
            "message": getattr(n, "message", "") or "",
            "seen": bool(getattr(n, "seen", False)),
            "created_at": n.created_at.isoformat() if getattr(n, "created_at", None) else None,
        })

    return Response({"unseen_count": unseen, "results": items})


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def admin_notification_seen_view(request, pk: int):
    forbidden = _require_admin(request)
    if forbidden:
        return forbidden

    n = get_object_or_404(Notification, pk=pk)
    n.seen = True
    n.save(update_fields=["seen"])
    return Response({"ok": True, "id": n.id, "seen": True})


# ================= COURIER HELPERS + ENDPOINTS =================
def _get_courier_linked(user):
    if not user or not getattr(user, "is_authenticated", False):
        return None
    return Courier.objects.filter(user=user).first()



from django.db.models import Q

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def courier_today_orders_view(request):
    forbidden = _require_courier(request)
    if forbidden:
        return forbidden

    courier = _get_courier_linked(request.user)
    if not courier:
        return Response({"detail": "COURIER_PROFILE_NOT_LINKED"}, status=404)

    today = timezone.localdate()

    qs = Order.objects.select_related("client").filter(
        created_at__date=today
    ).filter(
        Q(courier=courier) | Q(courier__isnull=True, status="pending")
    ).order_by("-created_at")[:200]

    grouped = {k: [] for k in ORDER_STATUSES}

    for o in qs:
        item = {
            "id": o.id,
            "client": o.client.full_name if o.client else "Mijoz",
            "phone": o.client.phone if o.client else "",
            "status": o.status,
            "bottles": o.bottles,
            "payment_type": o.payment_type or "",
            "payment_amount": int(o.payment_amount or 0),
        }
        grouped[item["status"]].append(item)

    return Response({"status": "ok", "data": grouped})

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def courier_position_view(request):
    forbidden = _require_courier(request)
    if forbidden:
        return forbidden

    courier = _get_courier_linked(request.user)
    if not courier:
        return Response({"detail": "COURIER_PROFILE_NOT_LINKED"}, status=404)

    return Response({"status": "ok", "data": {
        "lat": getattr(courier, "lat", None),
        "lon": getattr(courier, "lon", None),
    }})
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def courier_order_track_view(request, pk: int):
    forbidden = _require_courier(request)
    if forbidden:
        return forbidden

    courier = _get_courier_linked(request.user)
    if not courier:
        return Response({"detail": "COURIER_PROFILE_NOT_LINKED"}, status=404)

    # faqat shu courierga tegishli order
    o = get_object_or_404(Order.objects.select_related("client"), pk=pk, courier=courier)

    # client coords (orderdan bo'lmasa client profildan)
    c_lat = getattr(o, "lat", None)
    c_lon = getattr(o, "lon", None)
    if c_lat is None or c_lon is None:
        cl = o.client
        c_lat = getattr(cl, "location_lat", None) if cl else None
        c_lon = getattr(cl, "location_lon", None) if cl else None

    # courier coords (courier profilidan)
    k_lat = getattr(courier, "lat", None)
    k_lon = getattr(courier, "lon", None)

    distance_km = None
    eta_seconds = None
    if c_lat is not None and c_lon is not None and k_lat is not None and k_lon is not None:
        try:
            distance_km = _haversine_km(float(c_lat), float(c_lon), float(k_lat), float(k_lon))
            eta_seconds = _eta_from_distance(distance_km, speed_kmh=25.0)
        except Exception:
            distance_km = None
            eta_seconds = None

    return Response({
        "status": "ok",
        "order_id": o.id,
        "order_status": o.status,
        "client": {"lat": c_lat, "lon": c_lon},
        "courier": {
            "id": courier.id,
            "full_name": getattr(courier, "full_name", None),
            "phone": getattr(courier, "phone", None),
            "lat": k_lat,
            "lon": k_lon,
        },
        "eta_seconds": eta_seconds,
        "eta_text": _fmt_eta(eta_seconds or 0),
        "distance_km": round(distance_km, 2) if distance_km is not None else None,
        "distance_text": (f"{distance_km:.1f} km" if distance_km is not None else ""),
    })

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def courier_update_position_view(request):
    """AssertionError bergan funksiya shu yerda tuzatildi"""
    forbidden = _require_courier(request)
    if forbidden:
        return forbidden

    courier = Courier.objects.filter(user=request.user).first()
    if not courier:
        return Response({"detail": "COURIER_PROFILE_NOT_LINKED"}, status=404)

    try:
        courier.lat = float(request.data.get("lat"))
        courier.lon = float(request.data.get("lon"))
        courier.save(update_fields=["lat", "lon"])
        return Response({"status": "ok"})
    except (TypeError, ValueError):
        return Response({"detail": "INVALID_LAT_LON"}, status=400)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def courier_accept_order_view(request):
    forbidden = _require_courier(request)
    if forbidden:
        return forbidden

    courier = _get_courier_linked(request.user)
    if not courier:
        return Response({"detail": "COURIER_PROFILE_NOT_LINKED"}, status=404)

    oid = request.data.get("order_id")
    if not oid:
        return Response({"detail": "ORDER_ID_REQUIRED"}, status=400)

    o = get_object_or_404(Order, pk=oid)
    o.courier = courier
    o.status = "assigned"
    o.save(update_fields=["courier", "status"])
    return Response({"status": "ok", "order_id": o.id})

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def courier_start_delivery_view(request):
    forbidden = _require_courier(request)
    if forbidden:
        return forbidden

    courier = _get_courier_linked(request.user)
    if not courier:
        return Response({"detail": "COURIER_PROFILE_NOT_LINKED"}, status=404)

    oid = request.data.get("order_id")
    if not oid:
        return Response({"detail": "ORDER_ID_REQUIRED"}, status=400)

    o = get_object_or_404(Order, pk=oid, courier=courier)

    # faqat assigned bo‘lsa delivering ga o‘tkazamiz
    if o.status not in ("assigned", "delivering"):
        return Response({"detail": f"INVALID_STATUS:{o.status}"}, status=400)

    o.status = "delivering"
    o.save(update_fields=["status"])
    return Response({"status": "ok", "order_id": o.id, "order_status": o.status})
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def courier_confirm_delivery_view(request):
    forbidden = _require_courier(request)
    if forbidden:
        return forbidden

    courier = _get_courier_linked(request.user)
    if not courier:
        return Response({"detail": "COURIER_PROFILE_NOT_LINKED"}, status=404)

    oid = request.data.get("order_id")
    if not oid:
        return Response({"detail": "ORDER_ID_REQUIRED"}, status=400)

    o = get_object_or_404(Order, pk=oid, courier=courier)

    o.payment_type = (request.data.get("payment_type") or "").strip()
    o.payment_amount = _to_int_amount(request.data.get("payment_amount") or 0, 0)
    o.status = "done"
    o.delivered_at = timezone.now()
    o.save(update_fields=["payment_amount", "payment_type", "status", "delivered_at"])

    return Response({"status": "ok", "order_id": o.id})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def courier_history_view(request):
    forbidden = _require_courier(request)
    if forbidden:
        return forbidden

    courier = _get_courier_linked(request.user)
    if not courier:
        return Response({"detail": "COURIER_PROFILE_NOT_LINKED"}, status=404)

    qs = Order.objects.select_related("client").filter(
        courier=courier,
        status="done"
    ).order_by("-delivered_at")[:500]

    data = []
    for o in qs:
        dt = getattr(o, "delivered_at", None) or getattr(o, "created_at", None)
        data.append({
            "order_id": o.id,
            "client": getattr(o.client, "full_name", "Mijoz") if o.client else "Mijoz",
            "amount": _to_int_amount(getattr(o, "payment_amount", 0), 0),
            "payment_type": (getattr(o, "payment_type", "") or ""),
            "date": dt.strftime("%Y-%m-%d %H:%M") if dt else None,
        })

    return Response({"status": "ok", "data": data})


# ================= CLIENT (DRF TOKEN) =================

def _get_client_linked(user):
    """
    JWT client endpointlar uchun:
    Agar Client userga bog'lanmagan bo‘lsa,
    avtomatik yaratadi yoki bog‘lab beradi.
    """
    if not user or not getattr(user, "is_authenticated", False):
        return None

    # 1) userga bog‘langan Client bormi?
    c = Client.objects.filter(user=user).first()
    if c:
        return c

    # 2) username phone bo‘lsa, phone orqali topamiz
    phone_guess = (getattr(user, "username", "") or "").strip()
    if phone_guess:
        by_phone = Client.objects.filter(phone=phone_guess).first()
        if by_phone and not getattr(by_phone, "user_id", None):
            try:
                by_phone.user = user
                by_phone.save(update_fields=["user"])
                return by_phone
            except Exception:
                pass

    # 3) umuman yo‘q bo‘lsa — yangi Client yaratamiz
    try:
        full_name = (user.get_full_name() or user.username or "").strip()
        c = Client.objects.create(
            user=user,
            full_name=full_name,
            phone=phone_guess or "",
        )
        return c
    except Exception:
        return None


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def client_me_view(request):
    forbidden = _require_client(request)
    if forbidden:
        return forbidden

    c = _get_client_linked(request.user)
    if not c:
        return Response({"detail": "CLIENT_PROFILE_NOT_LINKED"}, status=404)

    full_name = (getattr(c, "full_name", "") or request.user.get_full_name() or request.user.username).strip()
    parts = full_name.split(" ", 1)

    return Response({
        "id": c.id,
        "customer_id": getattr(c, "customer_id", None),
        "full_name": full_name,
        "first_name": getattr(c, "first_name", "") or (parts[0] if parts else ""),
        "last_name": getattr(c, "last_name", "") or (parts[1] if len(parts) > 1 else ""),
        "phone": getattr(c, "phone", "") or "",
        "email": getattr(request.user, "email", "") or "",
        "region": getattr(getattr(c, "region", None), "name", None),
        "location": {
            "lat": getattr(c, "location_lat", None),
            "lon": getattr(c, "location_lon", None),
        },
        "bottle_balance": getattr(c, "bottle_balance", 0),
        "bottles_count": getattr(c, "bottles_count", 0),
        "debt": str(getattr(c, "debt", "0")),
        "last_order": getattr(c, "last_order", None),
        "note": getattr(c, "note", None),
        "agreed_to_contract": getattr(c, "agreed_to_contract", False),
        "must_change_password": getattr(c, "must_change_password", True),
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def client_metrics_view(request):
    forbidden = _require_client(request)
    if forbidden:
        return forbidden

    c = _get_client_linked(request.user)
    if not c:
        return Response({"detail": "CLIENT_PROFILE_NOT_LINKED"}, status=404)

    return Response({
        "bottle_balance": _to_int_amount(getattr(c, "bottle_balance", 0), 0),
        "debt": _to_int_amount(getattr(c, "debt", 0), 0),
        "recent_orders_count": Order.objects.filter(client=c).count(),
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def client_recent_orders_view(request):
    forbidden = _require_client(request)
    if forbidden:
        return forbidden

    c = _get_client_linked(request.user)
    if not c:
        return Response({"detail": "CLIENT_PROFILE_NOT_LINKED"}, status=404)

    qs = Order.objects.select_related("courier").filter(client=c).order_by("-created_at")[:10]

    items = []
    for o in qs:
        courier = None
        if o.courier:
            courier = {
                "id": o.courier.id,
                "full_name": o.courier.full_name,
                "phone": o.courier.phone,
                "lat": getattr(o.courier, "lat", None),
                "lon": getattr(o.courier, "lon", None),
            }

        items.append({
            "id": o.id,
            "status": o.status,
            "bottles": o.bottles,
            "created_at": o.created_at.isoformat() if o.created_at else None,
            "courier": courier,   # 🔥 MUHIM
        })

    return Response(items)


# ================= CLIENT PANEL (SESSION JSON) =================
# Bu endpointlar TOKEN emas, SESSION bilan ishlaydi.
# Ular client_panel html/js uchun qulay.

def _session_client(request):
    cid = request.session.get("client_id")
    if not cid:
        return None
    return Client.objects.filter(id=cid).first()


@csrf_exempt
def api_client_orders(request):
    client = _session_client(request)
    if not client:
        return JsonResponse({"status": "error", "message": "Not authenticated"}, status=403)

    qs = Order.objects.filter(client=client).order_by("-created_at")[:100]
    items = []
    for o in qs:
        items.append({
            "id": o.id,
            "created_at": o.created_at.isoformat() if getattr(o, "created_at", None) else "",
            "status": getattr(o, "status", ""),
            "bottles": getattr(o, "bottle_count", 0),
            "note": getattr(o, "client_note", "") or "",
            "amount": int(getattr(o, "debt_change", 0) or 0),
        })
    return JsonResponse({"status": "ok", "data": items})


@csrf_exempt
def api_update_profile(request):
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "POST required"}, status=405)

    client = _session_client(request)
    if not client:
        return JsonResponse({"status": "error", "message": "Not authenticated"}, status=403)

    data = {}
    try:
        if request.content_type == "application/json":
            data = json.loads(request.body.decode("utf-8"))
        else:
            data = request.POST
    except Exception:
        data = request.POST

    first = (data.get("first_name") or "").strip()
    last = (data.get("last_name") or "").strip()
    phone = (data.get("phone") or data.get("client_phone") or "").strip()
    address = (data.get("address") or "").strip()
    lat = data.get("lat")
    lon = data.get("lon")

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
        region_obj = Region.objects.filter(name=address).first()
        if not region_obj:
            region_obj, _ = Region.objects.get_or_create(name=address)
        client.region = region_obj
        updated = True

    if updated:
        client.save()

    # session sync
    try:
        request.session["client_name"] = client.first_name or client.full_name or ""
        request.session["client_phone"] = client.phone or ""
    except Exception:
        pass

    # notify admin
    try:
        Notification.objects.create(
            title="Mijoz profili yangilandi",
            message=f"Client {client.id} ({client.phone}) profili yangilandi"
        )
    except Exception:
        pass

    return JsonResponse({"status": "ok"})


@csrf_exempt
def api_contact_admin(request):
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "POST required"}, status=405)

    client = _session_client(request)
    if not client:
        return JsonResponse({"status": "error", "message": "Not authenticated"}, status=403)

    msg = request.POST.get("message") or request.POST.get("text") or ""
    msg = msg.strip()
    if not msg:
        return JsonResponse({"status": "error", "message": "message required"}, status=400)

    try:
        Notification.objects.create(
            title="Client yordam xabari",
            message=f"Client {client.id} ({client.phone}): {msg}"
        )
    except Exception:
        pass

    return JsonResponse({"status": "ok"})


@csrf_exempt
def api_create_order(request):
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "POST required"}, status=405)

    client = _session_client(request)
    if not client:
        return JsonResponse({"status": "error", "message": "Not authenticated"}, status=403)

    # accept JSON or form
    data = {}
    try:
        if request.content_type == "application/json":
            data = json.loads(request.body.decode("utf-8"))
        else:
            data = request.POST
    except Exception:
        data = request.POST

    bottles = data.get("bottles") or data.get("bottle") or 1
    note = (data.get("note") or "").strip()
    lat = data.get("lat") or data.get("location_lat")
    lon = data.get("lon") or data.get("location_lon")

    try:
        bottle_count = int(bottles)
    except Exception:
        bottle_count = 1

    # duplicate protect (10 sec)
    try:
        recent_cutoff = timezone.now() - timedelta(seconds=10)
        existing = Order.objects.filter(
            client=client,
            status="pending",
            bottle_count=bottle_count,
            client_note=note,
            created_at__gte=recent_cutoff
        ).order_by("-created_at").first()
        if existing:
            return JsonResponse({"status": "ok", "order_id": existing.id, "duplicate": True})
    except Exception:
        pass

    o = Order.objects.create(
        client=client,
        bottle_count=bottle_count,
        status="pending",
        client_note=note,
    )

    # price calc
    try:
        unit_price = 12000
        o.debt_change = Decimal(bottle_count * unit_price)
        o.save(update_fields=["debt_change"])
    except Exception:
        pass

    # save client location
    try:
        if lat and lon:
            client.location_lat = float(lat)
            client.location_lon = float(lon)
            client.save(update_fields=["location_lat", "location_lon"])
    except Exception:
        pass

    # notify admin
    try:
        cname = client.first_name or client.full_name or ""
        cphone = client.phone or ""
        try:
            amt = int(getattr(o, "debt_change", 0) or 0)
        except Exception:
            amt = bottle_count * 12000
        msg = f"Client {client.id} ({cname} {cphone}) buyurtma berdi #{o.id} — {bottle_count} ta — {amt} UZS"
        if note:
            msg += f" — Note: {note}"
        Notification.objects.create(title="Yangi buyurtma", message=msg)
    except Exception:
        pass

    return JsonResponse({"status": "ok", "order_id": o.id})
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
import math

import math

def _haversine_km(lat1, lon1, lat2, lon2):
    R = 6371  # Yer radiusi (km)
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2

    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def estimate_eta_minutes(km: float) -> int:
    AVG_SPEED_KMH = 30  # shahar ichida
    return max(3, int((km / AVG_SPEED_KMH) * 60))
def _eta_from_distance(distance_km: float, speed_kmh: float = 25.0) -> int:
    # return seconds
    if not distance_km or distance_km <= 0:
        return 0
    hours = distance_km / max(speed_kmh, 1.0)
    return int(hours * 3600)

def _fmt_eta(seconds: int) -> str:
    if seconds <= 0: return ""
    m = int(round(seconds / 60))
    if m < 60: return f"{m} daqiqa"
    return f"{m // 60} soat {m % 60} daqiqa"
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def client_order_track_view(request, pk: int):
    forbidden = _require_client(request)
    if forbidden:
        return forbidden

    c = _get_client_linked(request.user)
    if not c:
        return Response({"detail": "CLIENT_PROFILE_NOT_LINKED"}, status=404)

    # faqat shu clientniki bo'lgan order
    o = get_object_or_404(Order.objects.select_related("courier"), pk=pk, client=c)

    # client coords (orderdan bo'lmasa profildan)
    c_lat = getattr(o, "lat", None)
    c_lon = getattr(o, "lon", None)
    if c_lat is None or c_lon is None:
        c_lat = getattr(c, "location_lat", None)
        c_lon = getattr(c, "location_lon", None)

    # courier coords
    k_lat = getattr(o.courier, "lat", None) if o.courier else None
    k_lon = getattr(o.courier, "lon", None) if o.courier else None

    distance_km = None
    eta_seconds = None
    if c_lat is not None and c_lon is not None and k_lat is not None and k_lon is not None:
        try:
            distance_km = _haversine_km(float(c_lat), float(c_lon), float(k_lat), float(k_lon))
            eta_seconds = _eta_from_distance(distance_km, speed_kmh=25.0)
        except Exception:
            distance_km = None
            eta_seconds = None

    courier = None
    if o.courier:
        courier = {
            "id": o.courier.id,
            "full_name": getattr(o.courier, "full_name", None),
            "phone": getattr(o.courier, "phone", None),
            "lat": getattr(o.courier, "lat", None),
            "lon": getattr(o.courier, "lon", None),
        }

    return Response({
        "status": "ok",
        "order_id": o.id,
        "order_status": o.status,
        "client": {"lat": c_lat, "lon": c_lon},
        "courier": courier,
        "eta_seconds": eta_seconds,
        "eta_text": _fmt_eta(eta_seconds or 0),
        "distance_km": round(distance_km, 2) if distance_km is not None else None,
        "distance_text": (f"{distance_km:.1f} km" if distance_km is not None else ""),
    })
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def client_update_location_view(request):
    forbidden = _require_client(request)
    if forbidden:
        return forbidden

    c = _get_client_linked(request.user)
    if not c:
        return Response({"detail": "CLIENT_PROFILE_NOT_LINKED"}, status=404)

    try:
        lat = float(request.data.get("lat"))
        lon = float(request.data.get("lon"))
    except Exception:
        return Response({"detail": "INVALID_LAT_LON"}, status=400)

    c.location_lat = lat
    c.location_lon = lon
    c.save(update_fields=["location_lat", "location_lon"])

    return Response({"status": "ok", "lat": c.location_lat, "lon": c.location_lon})
# api/views.py
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

class MeAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        u = request.user
        return Response({
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "is_staff": u.is_staff,
            "is_superuser": u.is_superuser,
        })
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def courier_metrics_view(request):
    forbidden = _require_courier(request)
    if forbidden:
        return forbidden

    courier = _get_courier_linked(request.user)
    if not courier:
        return Response({"detail": "COURIER_PROFILE_NOT_LINKED"}, status=status.HTTP_404_NOT_FOUND)

    return Response({"ok": True})
from django.conf import settings
from django.contrib.auth.models import User, Group
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

def _norm_phone(p: str) -> str:
    s = (p or "").strip().replace(" ", "").replace("-", "")
    if s.endswith(".0"): s = s[:-2]
    if s.startswith("+998"): return s
    if s.startswith("998"): return "+" + s
    if len(s) == 9 and s.startswith("9"): return "+998" + s
    return s

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def admin_courier_create_view(request):
    """Kuryer yaratish va parolni Flutterga qaytarish"""
    forbidden = _require_admin(request)
    if forbidden: return forbidden
    my_business = _get_my_business(request.user)
    data = request.data or {}
    full_name = (data.get("full_name") or "").strip()
    phone_raw = (data.get("phone") or "").strip()
    
    if not full_name or not phone_raw:
        return Response({"detail": "FULL_NAME_AND_PHONE_REQUIRED"}, status=400)

    phone = _norm_phone(phone_raw)
    username = phone
    default_password = (data.get("default_password") or "Suv2026").strip()

    user, created_user = User.objects.get_or_create(username=username)
    if created_user:
        user.set_password(default_password)
        user.save()
    
    g, _ = Group.objects.get_or_create(name="courier")
    user.groups.add(g)

    courier, _ = Courier.objects.get_or_create(
        phone=phone,
        defaults={"full_name": full_name, "user": user, "is_active": True,"business": my_business}
    )
    
    return Response({
        "ok": True,
        "username": user.username,
        "default_password": default_password
    }, status=201)




@api_view(["POST"])
@permission_classes([IsAuthenticated])
def client_create_order_view(request):
    """Client order yaratish (lat/lon bilan, to'g'ri indentatsiya)"""

    forbidden = _require_client(request)
    if forbidden:
        return forbidden

    c = _get_client_linked(request.user)
    if not c:
        return Response(
            {"detail": "CLIENT_PROFILE_NOT_LINKED"},
            status=status.HTTP_404_NOT_FOUND,
        )

    # --- client location (lat/lon) ---
    lat = request.data.get("lat")
    lon = request.data.get("lon")
    try:
        lat = float(lat) if lat not in (None, "") else None
        lon = float(lon) if lon not in (None, "") else None
    except Exception:
        lat = None
        lon = None

    bottles_raw = (
        request.data.get("bottles")
        or request.data.get("bottle")
        or request.data.get("bottles_count")
        or 1
    )
    note = (request.data.get("note") or request.data.get("client_note") or "").strip()

    try:
        bottle_count = int(bottles_raw)
    except Exception:
        bottle_count = 1

    # model field detection
    bottle_field = next((f for f in ["bottle_count", "bottles", "bottles_count"] if _has_field(Order, f)), None)
    note_field = next((f for f in ["client_note", "note", "address", "comment"] if _has_field(Order, f)), None)
    status_field = "status" if _has_field(Order, "status") else None

    create_kwargs = {"client": c}
    if status_field:
        create_kwargs[status_field] = "pending"
    if bottle_field:
        create_kwargs[bottle_field] = bottle_count
    if note_field:
        create_kwargs[note_field] = note

    # attach lat/lon to order if fields exist
    if lat is not None and lon is not None and _has_field(Order, "lat") and _has_field(Order, "lon"):
        create_kwargs["lat"] = lat
        create_kwargs["lon"] = lon

    o = Order.objects.create(**create_kwargs,business=c.business,)

    # save client fallback location
    if lat is not None and lon is not None:
        try:
            c.location_lat = lat
            c.location_lon = lon
            c.save(update_fields=["location_lat", "location_lon"])
        except Exception:
            pass

    return Response({"ok": True, "order_id": o.id}, status=status.HTTP_201_CREATED)

def _get_my_business(user):
    # 1. Agar Admin bo'lsa
    if hasattr(user, 'admin_panel_profile') and user.admin_panel_profile.business:
        return user.admin_panel_profile.business
    # 2. Agar Kuryer bo'lsa
    if hasattr(user, 'courier_profile') and user.courier_profile.business:
        return user.courier_profile.business
    # 3. Agar Klient bo'lsa
    # (Klient modelida related_name='client_profile' bo'lsa yoki shunga o'xshash)
    # ...
    return None


