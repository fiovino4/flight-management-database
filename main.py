#!/usr/bin/env python3
import sqlite3
from pathlib import Path

DB_FILE = Path(__file__).with_name("flight_management.db")

def connect():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def main():
    if not DB_FILE.exists():
        print("flight_management.db not found.")
        print("Run: python populate_db.py")
        return

    conn = connect()
    conn.close()
    print("Connected to database successfully.")

if __name__ == "__main__":
    main()