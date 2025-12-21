import sqlite3
import os
from decimal import Decimal, InvalidOperation

db_path = 'db.sqlite3'

def fix_decimals():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("Checking suv_tashish_crm_order...")
    
    cursor.execute("SELECT id, payment_amount FROM suv_tashish_crm_order")
    rows = cursor.fetchall()
    for r in rows:
        pid, val = r
        if val is None: continue
        try:
            Decimal(val)
        except InvalidOperation:
            print(f"Invalid payment_amount for order {pid}: {repr(val)} type={type(val)}")
            cursor.execute("UPDATE suv_tashish_crm_order SET payment_amount = NULL WHERE id = ?", (pid,))
        except Exception as e:
            print(f"Other error for order {pid}: {e} val={repr(val)}")

    cursor.execute("SELECT id, debt_change FROM suv_tashish_crm_order")
    rows = cursor.fetchall()
    for r in rows:
        pid, val = r
        if val is None: continue
        try:
            Decimal(val)
        except InvalidOperation:
            print(f"Invalid debt_change for order {pid}: {repr(val)} type={type(val)}")
            cursor.execute("UPDATE suv_tashish_crm_order SET debt_change = 0 WHERE id = ?", (pid,))

    print("Checking suv_tashish_crm_client...")
    cursor.execute("SELECT id, debt FROM suv_tashish_crm_client")
    rows = cursor.fetchall()
    for r in rows:
        cid, val = r
        if val is None: continue
        try:
            Decimal(val)
        except InvalidOperation:
            print(f"Invalid debt for client {cid}: {repr(val)} type={type(val)}")
            cursor.execute("UPDATE suv_tashish_crm_client SET debt = 0 WHERE id = ?", (cid,))

    conn.commit()
    conn.close()
    print("Done.")

if __name__ == '__main__':
    if os.path.exists(db_path):
        fix_decimals()
    else:
        print("db.sqlite3 not found")
