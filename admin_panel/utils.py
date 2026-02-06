import os, csv
from django.conf import settings
from django.utils import timezone

CSV_HEADERS = ["created_at", "full_name", "phone", "address"]

def _csv_safe(value: str) -> str:
    """
    Excel/Sheets CSV injectiondan himoya:
    qiymat '=', '+', '-', '@' bilan boshlansa oldiga apostrof qo'yamiz.
    """
    if value is None:
        return ""
    s = str(value).strip()
    if s and s[0] in ("=", "+", "-", "@"):
        return "'" + s
    return s

def append_client_to_csv(full_name: str, phone: str, address: str) -> str:
    # CSV qayerga saqlansin:
    folder = os.path.join(settings.BASE_DIR, "data")
    os.makedirs(folder, exist_ok=True)

    csv_path = os.path.join(folder, "clients.csv")

    file_exists = os.path.exists(csv_path)
    is_empty = (not file_exists) or (os.path.getsize(csv_path) == 0)

    # utf-8-sig -> Excelda Uzbek/Rus harflari buzilmasligi uchun yaxshi
    with open(csv_path, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)

        if is_empty:
            writer.writerow(CSV_HEADERS)

        writer.writerow([
            timezone.localtime().isoformat(timespec="seconds"),
            _csv_safe(full_name),
            _csv_safe(phone),
            _csv_safe(address),
        ])

    return csv_path
