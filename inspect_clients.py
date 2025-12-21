import sqlite3

def inspect_clients():
    conn = sqlite3.connect('db.sqlite3')
    cursor = conn.cursor()
    
    print("Inspecting Client table (debt column)...")
    cursor.execute("SELECT id, debt FROM suv_tashish_crm_client")
    rows = cursor.fetchall()
    
    for row in rows:
        client_id, debt = row
        # Check if debt is a valid number and fits in Decimal(10, 2)
        # max_digits=10, decimal_places=2 means max value is 99999999.99
        
        is_valid = True
        try:
            if debt is None:
                pass # None is fine if nullable, but here default=0.0 so it shouldn't be None usually, but let's see.
                     # Actually model says default=0.0, not null=True. So it should be a number.
            else:
                val = float(debt)
                if val > 99999999.99 or val < -99999999.99:
                    is_valid = False
        except (ValueError, TypeError):
            is_valid = False
            
        if not is_valid or (isinstance(debt, str) and len(debt) > 11): # rough check for length
             print(f"Client {client_id}: debt={debt} (Type: {type(debt)})")

    conn.close()

if __name__ == "__main__":
    inspect_clients()
