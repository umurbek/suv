import sqlite3
import os

db_path = 'db.sqlite3'

def inspect_values():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("Inspecting suv_tashish_crm_order...")
    cursor.execute("SELECT id, payment_amount, debt_change FROM suv_tashish_crm_order")
    rows = cursor.fetchall()
    for r in rows:
        pid, pa, dc = r
        print(f"Order {pid}: payment_amount={repr(pa)} type={type(pa)}, debt_change={repr(dc)} type={type(dc)}")

    conn.close()

if __name__ == '__main__':
    inspect_values()
