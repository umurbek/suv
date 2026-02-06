import csv
import os
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CSV_PATH = os.path.join(BASE_DIR, 'Volidam.csv')

def read_csv_data():
    rows = []
    if not os.path.exists(CSV_PATH):
        return rows

    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        try:
            next(reader)  # header skip
        except StopIteration:
            return rows

        for row in reader:
            rows.append({
                'name': (row[0] if len(row) > 0 else '').strip(),
                'bottle': (row[1] if len(row) > 1 else '').strip(),
                'location': (row[2] if len(row) > 2 else '').strip(),
                'phone': (row[3] if len(row) > 3 else '').strip(),
            })
    return rows

def normalize_to_998(raw: str):
    if not raw:
        return None
    d = ''.join(ch for ch in raw if ch.isdigit())
    if len(d) < 9:
        return None
    last9 = d[-9:]
    return '998' + last9  # 12 digits

def build_csv_phone_maps(csv_rows):
    phone_to_name = {}
    last6_to_name = {}
    for r in csv_rows:
        p = (r.get('phone') or '').strip()
        norm = normalize_to_998(p)
        if norm:
            phone_to_name[norm] = r.get('name')

        digits = ''.join(ch for ch in p if ch.isdigit())
        if len(digits) >= 6:
            last6_to_name[digits[-6:]] = r.get('name')

    return phone_to_name, last6_to_name
