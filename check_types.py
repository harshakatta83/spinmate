import sqlite3

conn = sqlite3.connect('instance/spinmate.db')
cursor = conn.cursor()

cursor.execute('SELECT id, created_at, updated_at FROM "order"')
for row in cursor.fetchall():
    id_, created_at, updated_at = row
    print(f"ID: {id_}, created_at: {created_at} ({type(created_at)}), updated_at: {updated_at} ({type(updated_at)})")