# api/views_admin_bootstrap.py
from django.conf import settings
from django.contrib.auth.models import User
from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import AdminBootstrapRequest
from .serializers_admin_bootstrap import (
    AdminBootstrapRequestSerializer,
    AdminBootstrapVerifySerializer,
    AdminBootstrapCompleteSerializer,
)
from .services import generate_6_digit_code, otp_expiry, send_admin_bootstrap_code


OTP_TTL_MIN = 5
MAX_ATTEMPTS = 5
RESEND_COOLDOWN_SECONDS = 60


def _bootstrap_key_ok(given_key: str) -> bool:
    # DEBUG da kalit bo‘sh bo‘lsa ham ishlasin (dev uchun)
    if settings.DEBUG and not settings.ADMIN_BOOTSTRAP_KEY:
        return True
    return bool(settings.ADMIN_BOOTSTRAP_KEY) and (given_key == settings.ADMIN_BOOTSTRAP_KEY)


def _too_fast(email: str) -> bool:
    last = (
        AdminBootstrapRequest.objects
        .filter(email=email)
        .order_by("-created_at")
        .first()
    )
    if not last:
        return False
    delta = (last.created_at - last.created_at)  # placeholder
    # yuqoridagini real hisoblaymiz:
    from django.utils import timezone
    seconds = (timezone.now() - last.created_at).total_seconds()
    return seconds < RESEND_COOLDOWN_SECONDS


class AdminBootstrapRequestOTP(APIView):
    permission_classes = []  # LOGIN shart emas

    def post(self, request):
        ser = AdminBootstrapRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        full_name = ser.validated_data["full_name"].strip()
        phone = ser.validated_data["phone"].strip()
        email = ser.validated_data["email"].lower().strip()
        company_key = ser.validated_data.get("company_key", "")

        if not _bootstrap_key_ok(company_key):
            return Response(
                {"detail": "Company key noto‘g‘ri. Admin yaratish mumkin emas."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if _too_fast(email):
            return Response(
                {"detail": "Kod juda tez so‘ralmoqda. 60 soniyadan keyin urinib ko‘ring."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        code = generate_6_digit_code()

        req = AdminBootstrapRequest.objects.create(
            full_name=full_name,
            phone=phone,
            email=email,
            code=code,
            expires_at=otp_expiry(OTP_TTL_MIN),
        )

        send_admin_bootstrap_code(email, code)

        return Response(
            {"detail": "Kod emailingizga yuborildi.", "request_id": req.id, "ttl_seconds": OTP_TTL_MIN * 60},
            status=status.HTTP_200_OK,
        )


class AdminBootstrapVerifyOTP(APIView):
    permission_classes = []  # LOGIN shart emas

    def post(self, request):
        ser = AdminBootstrapVerifySerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        request_id = ser.validated_data["request_id"]
        code = ser.validated_data["code"].strip()

        req = AdminBootstrapRequest.objects.filter(id=request_id).first()
        if not req:
            return Response({"detail": "So‘rov topilmadi."}, status=status.HTTP_400_BAD_REQUEST)

        if req.is_verified:
            return Response({"detail": "Allaqachon tasdiqlangan."}, status=status.HTTP_200_OK)

        if req.is_expired():
            return Response({"detail": "Kod eskirdi. Qayta so‘rov yuboring."}, status=status.HTTP_400_BAD_REQUEST)

        if req.attempts >= MAX_ATTEMPTS:
            return Response({"detail": "Juda ko‘p noto‘g‘ri urinish. Qayta so‘rov yuboring."}, status=status.HTTP_403_FORBIDDEN)

        if req.code != code:
            req.attempts += 1
            req.save(update_fields=["attempts"])
            return Response({"detail": "Kod noto‘g‘ri."}, status=status.HTTP_400_BAD_REQUEST)

        from django.utils import timezone
        req.is_verified = True
        req.verified_at = timezone.now()
        req.save(update_fields=["is_verified", "verified_at"])

        return Response({"detail": "OTP tasdiqlandi ✅", "request_id": req.id}, status=status.HTTP_200_OK)


class AdminBootstrapComplete(APIView):
    permission_classes = []  # LOGIN shart emas

    @transaction.atomic
    def post(self, request):
        ser = AdminBootstrapCompleteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        request_id = ser.validated_data["request_id"]
        username = ser.validated_data["username"].strip()
        password = ser.validated_data["password"]

        req = AdminBootstrapRequest.objects.select_for_update().filter(id=request_id).first()
        if not req:
            return Response({"detail": "So‘rov topilmadi."}, status=status.HTTP_400_BAD_REQUEST)

        if not req.is_verified:
            return Response({"detail": "Avval OTP tasdiqlang."}, status=status.HTTP_400_BAD_REQUEST)

        # username band bo‘lsa
        if User.objects.filter(username=username).exists():
            return Response({"detail": "Bu username band. Boshqasini tanlang."}, status=status.HTTP_400_BAD_REQUEST)

        # Agar shu email bilan user bor bo‘lsa — update qilamiz (xohlasangiz)
        user = User.objects.filter(email=req.email).first()
        if user is None:
            user = User(username=username, email=req.email)
        else:
            user.username = username
            user.email = req.email

        # full_name -> first_name ga (minimal)
        user.first_name = req.full_name[:150]

        # admin huquqi
        user.is_staff = True
        user.is_superuser = True  # agar superuser kerak bo‘lmasa aytasiz, False qilib qo‘yamiz
        user.set_password(password)
        user.save()

        return Response(
            {"detail": "Admin yaratildi/yangilandi ✅. Endi login qiling.", "username": user.username},
            status=status.HTTP_201_CREATED,
        )