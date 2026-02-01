import sqlite3
from pathlib import Path

DB_FILE = Path(__file__).with_name("flight_management.db")

# 1) DATABASE CONNECTION

def connect_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


# 2) PRINTING HELPER

def print_rows(rows):
    rows = list(rows)
    if len(rows) == 0:
        print("(no results)")
        return

    headers = rows[0].keys()
    print(" | ".join(headers))
    print("-" * 80)

    for row in rows:
        line = []
        for h in headers:
            line.append(str(row[h]))
        print(" | ".join(line))


# 3) ONE SHARED QUERY BUILDER

def run_flight_query(conn, dest="", status="", date=""):
    sql = """
    SELECT f.flight_id, f.flight_no,
           o.iata_code AS origin,
           d.iata_code AS destination,
           f.departure_dt,
           f.status
    FROM flight f
    JOIN destination o ON o.destination_id = f.origin_id
    JOIN destination d ON d.destination_id = f.destination_id
    """

    conditions = []
    params = []

    if dest != "":
        conditions.append("d.iata_code = ?")
        params.append(dest)

    if status != "":
        conditions.append("f.status = ?")
        params.append(status)

    if date != "":
        # departure_dt is stored as "YYYY-MM-DD HH:MM"
        # substr(...,1,10) gives "YYYY-MM-DD"
        conditions.append("substr(f.departure_dt,1,10) = ?")
        params.append(date)

    if len(conditions) > 0:
        sql = sql + " WHERE " + " AND ".join(conditions)

    sql = sql + " ORDER BY f.departure_dt;"

    rows = conn.execute(sql, params)
    print_rows(rows)


# 4) READ OPTIONS (MENU)

def view_all_flights(conn):
    run_flight_query(conn)


def view_flights_by_destination(conn):
    dest = input("Destination IATA (e.g., CDG): ").strip().upper()
    if dest == "":
        print("You did not type a destination.")
        return
    run_flight_query(conn, dest=dest)


def view_flights_by_destination_and_status(conn):
    dest = input("Destination IATA (blank = all): ").strip().upper()
    status = input("Status (blank = all): ").strip()
    run_flight_query(conn, dest=dest, status=status)


def view_flights_by_dest_status_date(conn):
    dest = input("Destination IATA (blank = all): ").strip().upper()
    status = input("Status (blank = all): ").strip()
    date = input("Departure date YYYY-MM-DD (blank = all): ").strip()
    run_flight_query(conn, dest=dest, status=status, date=date)


# MAIN MENU LOOP

def main():
    if not DB_FILE.exists():
        print("Database not found:", DB_FILE)
        print("Run: python populate_db.py")
        return

    conn = connect_db()

    while True:
        print("\n=== MENU ===")
        print("1) View all flights")
        print("2) View flights by destination")
        print("3) View flights by destination and status")
        print("4) View flights by destination, status, and date")
        print("0) Exit")
        choice = input("Select: ").strip()

        if choice == "1":
            view_all_flights(conn)
        elif choice == "2":
            view_flights_by_destination(conn)
        elif choice == "3":
            view_flights_by_destination_and_status(conn)
        elif choice == "4":
            view_flights_by_dest_status_date(conn)
        elif choice == "0":
            break
        else:
            print("Please choose 1, 2, 3, 4 or 0.")

    conn.close()
    print("Goodbye!")


if __name__ == "__main__":
    main()