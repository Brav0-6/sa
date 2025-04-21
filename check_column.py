import sqlite3
import os

# Direct connection to the database
db_path = "db.sqlite3"
print(f"Connecting to database: {db_path}")
print(f"Database exists: {os.path.exists(db_path)}")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# List all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print("Tables in database:")
for table in tables:
    print(table[0])

print("\nChecking for store_review table...")
# Get table info if store_review exists
if ('store_review',) in tables:
    cursor.execute("PRAGMA table_info(store_review)")
    columns = cursor.fetchall()
    print("Columns in store_review table:")
    for column in columns:
        print(column)
else:
    print("store_review table does not exist!")

conn.close() 