# courier_panel/utils.py
import csv
from django.conf import settings
from pathlib import Path
from django.utils import timezone

def append_client_to_csv(full_name, phone, address):
    """
    Client ma'lumotlarini data/clients.csv ga qo‘shadi
    """
    base_dir = Path(settings.BASE_DIR)
    data_dir = base_dir / "data"
    data_dir.mkdir(exist_ok=True)

    csv_path = data_dir / "clients.csv"

    file_exists = csv_path.exists() and csv_path.stat().st_size > 0

    with csv_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["created_at", "full_name", "phone", "address"])
        writer.writerow([
            timezone.now().isoformat(),
            full_name,
            phone,
            address
        ])

    return str(csv_path)
