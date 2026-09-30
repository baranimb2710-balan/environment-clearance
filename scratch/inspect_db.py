import sqlite3
import os

db_name = "ec_app.db"
conn = sqlite3.connect(db_name)
cur = conn.cursor()

print("=== PRAGMA foreign_keys ===")
cur.execute("PRAGMA foreign_keys")
print(cur.fetchall())

print("\n=== TABLES & SQL ===")
cur.execute("SELECT name, sql FROM sqlite_master WHERE type='table'")
tables = cur.fetchall()
for t, sql in tables:
    print(f"\n--- Table: {t} ---")
    print(sql)

for t, _ in tables:
    print(f"\n=== PRAGMA table_info({t}) ===")
    cur.execute(f"PRAGMA table_info({t})")
    for r in cur.fetchall():
        print(r)
    print(f"=== PRAGMA foreign_key_list({t}) ===")
    cur.execute(f"PRAGMA foreign_key_list({t})")
    print(cur.fetchall())
    print(f"=== PRAGMA index_list({t}) ===")
    cur.execute(f"PRAGMA index_list({t})")
    print(cur.fetchall())

print("\n=== RECORD COUNTS ===")
for t, _ in tables:
    cur.execute(f"SELECT count(*) FROM {t}")
    print(f"{t}: {cur.fetchone()[0]} rows")
