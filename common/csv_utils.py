import os
import csv
from django.conf import settings
from django.utils import timezone

CSV_HEADERS = ["created_at", "full_name", "bottle_count","address", "phone",  "source"]

def csv_safe(value: str) -> str:
    if value is None:
        return ""
    s = str(value).strip()
    if s and s[0] in ("=", "+", "-", "@"):
        return "'" + s
    return s

def append_client_to_csv(full_name: str, phone: str, address: str, source: str) -> str:
    folder = os.path.join(settings.BASE_DIR, "data")
    os.makedirs(folder, exist_ok=True)

    csv_path = os.path.join(folder, "clients.csv")

    file_exists = os.path.exists(csv_path)
    is_empty = (not file_exists) or (os.path.getsize(csv_path) == 0)

    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if is_empty:
            writer.writerow(CSV_HEADERS)

        writer.writerow([
            timezone.now().isoformat(),
            csv_safe(full_name),
            csv_safe(phone),
            csv_safe(address),
            csv_safe(source),   # ✅ admin / courier
        ])

    return csv_path
