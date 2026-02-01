#!/usr/bin/env python3
# Commit 2: read data from the database (VIEW FLIGHTS)

import sqlite3
from pathlib import Path

# Database file is in the same folder as this Python file
DB_FILE = Path(__file__).with_name("flight_management.db")


def connect_db():
    # Connect to SQLite database
    conn = sqlite3.connect(DB_FILE)

    # This lets us read columns by name, like row["flight_no"]
    conn.row_factory = sqlite3.Row

    # Make sure foreign keys are enforced
    conn.execute("PRAGMA foreign_keys = ON;")

    return conn


def print_rows(rows):
    # Convert to a list so we can check if there are any results
    rows = list(rows)

    if len(rows) == 0:
        print("(no results)")
        return

    # Print column headers
    headers = rows[0].keys()
    print(" | ".join(headers))
    print("-" * 80)

    # Print each row
    for row in rows:
        line = []
        for h in headers:
            line.append(str(row[h]))
        print(" | ".join(line))


def view_all_flights(conn):
    # This is a READ query: just show all flights
    sql = """
    SELECT f.flight_id, f.flight_no,
           o.iata_code AS origin,
           d.iata_code AS destination,
           f.departure_dt,
           f.status
    FROM flight f
    JOIN destination o ON o.destination_id = f.origin_id
    JOIN destination d ON d.destination_id = f.destination_id
    ORDER BY f.departure_dt;
    """

    rows = conn.execute(sql)
    print_rows(rows)


def main():
    # If database file is missing, tell user what to do
    if not DB_FILE.exists():
        print("Database not found:", DB_FILE)
        print("Run: python populate_db.py")
        return

    conn = connect_db()

    # Menu (just 2 options for now)
    while True:
        print("\n=== MENU ===")
        print("1) View all flights")
        print("0) Exit")
        choice = input("Select: ").strip()

        if choice == "1":
            view_all_flights(conn)
        elif choice == "0":
            break
        else:
            print("Please choose 1 or 0.")

    conn.close()
    print("Goodbye!")


if __name__ == "__main__":
    main()