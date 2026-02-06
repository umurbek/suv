import csv
import io
import re
import secrets
import string

from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from suv_tashish_crm.models import Client, Region

User = get_user_model()

def _normalize_phone(raw: str):
    if not raw:
        return None
    digits = re.sub(r"\D", "", raw)
    if not digits:
        return None

    if len(digits) == 9:
        return "+998" + digits
    if len(digits) == 12 and digits.startswith("998"):
        return "+" + digits
    return "+" + digits

def _gen_password(length: int = 10):
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))

def _slug_base(full_name: str):
    base = (full_name.split()[0] if full_name.split() else "user").lower()
    base = re.sub(r"[^a-z0-9]", "", base)
    return base[:10] or "user"

def _gen_unique_username(base: str):
    for _ in range(50):
        candidate = f"{base}{secrets.randbelow(9000) + 1000}"
        if not User.objects.filter(username=candidate).exists():
            return candidate
    return f"user{secrets.randbelow(900000) + 100000}"

@login_required
@require_http_methods(["GET", "POST"])
def import_clients_ui(request):
    if request.method == "GET":
        return render(request, "admin/clients_import.html")

    f = request.FILES.get("file")
    if not f:
        return render(request, "admin/clients_import.html", {"error": "CSV fayl tanlanmadi."})

    content = f.read().decode("utf-8", errors="ignore")
    reader = csv.reader(io.StringIO(content))

    out_rows = [["full_name", "bottles", "address", "phone", "username", "temp_password"]]

    for row in reader:
        if not row or all(not (c or "").strip() for c in row):
            continue

        full_name = (row[0] if len(row) > 0 else "").strip()
        bottles_raw = (row[1] if len(row) > 1 else "").strip()
        address = (row[2] if len(row) > 2 else "").strip()
        phone_raw = (row[3] if len(row) > 3 else "").strip()

        if not full_name or not address:
            continue

        try:
            bottles = int(bottles_raw) if bottles_raw else 1
            if bottles <= 0:
                bottles = 1
        except ValueError:
            bottles = 1

        phone = _normalize_phone(phone_raw)

        # Region: location bo‘yicha Region yaratamiz yoki topamiz
        region_obj, _ = Region.objects.get_or_create(name=address)

        username = _gen_unique_username(_slug_base(full_name))
        temp_password = _gen_password(10)

        user = User.objects.create_user(username=username, password=temp_password)

        # Sizning Client modelingizda fieldlar boshqacha bo‘lishi mumkin.
        # Minimal: full_name + phone + region + default bottles/balance.
        Client.objects.create(
            user=user,
            full_name=full_name,
            phone=phone,
            region=region_obj,
            bottle_balance=0,
            debt=0,
        )

        out_rows.append([full_name, bottles, location, phone or "", username, temp_password])

    out = io.StringIO()
    csv.writer(out).writerows(out_rows)

    resp = HttpResponse(out.getvalue(), content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = 'attachment; filename="clients_credentials.csv"'
    return resp
