import sqlite3

conn = sqlite3.connect('instance/spinmate.db')
cursor = conn.cursor()

cursor.execute('PRAGMA table_info("order")')
columns = cursor.fetchall()
print("Columns in 'order' table:")
for col in columns:
    print(col)