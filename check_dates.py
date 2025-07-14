import sqlite3

conn = sqlite3.connect('instance/spinmate.db')
cursor = conn.cursor()

tables_and_cols = [
    ("order_status_update", ["timestamp"]),
    ("feedback", ["created_at"]),
    ("complaint", ["created_at"]),
    ("user", ["created_at"]),
    ("service_location", ["created_at"]),
    ("pincode", ["created_at"]),
]

for table, cols in tables_and_cols:
    print(f"\nChecking table: {table}")
    try:
        select_cols = ", ".join(["id"] + cols)
        cursor.execute(f'SELECT {select_cols} FROM "{table}"')
        for row in cursor.fetchall():
            out = [f"ID: {row[0]}"]
            for idx, col in enumerate(cols):
                val = row[idx+1]
                out.append(f"{col}: {val} ({type(val)})")
            print(", ".join(out))
    except Exception as e:
        print(f"Error reading {table}: {e}")