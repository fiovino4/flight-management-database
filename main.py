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

# 5) CREATE FLIGHT 

def add_flight(conn):
    print("\nADD FLIGHT (CREATE)")

    flight_no = input("Flight number (e.g., AX999): ").strip().upper()
    origin = input("Origin IATA (e.g., LHR): ").strip().upper()
    dest = input("Destination IATA (e.g., CDG): ").strip().upper()
    reg = input("Aircraft registration (e.g., G-AX01): ").strip().upper()
    dep = input("Departure datetime (YYYY-MM-DD HH:MM): ").strip()
    arr = input("Arrival datetime   (YYYY-MM-DD HH:MM): ").strip()
    status = input("Status (default Scheduled): ").strip()
    if status == "":
        status = "Scheduled"

    gate = input("Gate (optional, e.g., A1): ").strip().upper()
    if gate == "":
        gate = None

    tickets_text = input("Tickets sold (default 0): ").strip()
    if tickets_text == "":
        tickets_sold = 0
    else:
        tickets_sold = int(tickets_text)

    # Look up foreign keys (IDs) from codes typed by the user
    origin_row = conn.execute(
        "SELECT destination_id FROM destination WHERE iata_code=?",
        (origin,)
    ).fetchone()

    dest_row = conn.execute(
        "SELECT destination_id FROM destination WHERE iata_code=?",
        (dest,)
    ).fetchone()

    aircraft_row = conn.execute(
        "SELECT aircraft_id FROM aircraft WHERE registration=?",
        (reg,)
    ).fetchone()

    if not origin_row or not dest_row or not aircraft_row:
        print("ERROR: origin/destination/aircraft not found in database.")
        return

    try:
        conn.execute(
            """INSERT INTO flight(
                   flight_no, origin_id, destination_id, aircraft_id,
                   departure_dt, arrival_dt, status, gate, tickets_sold
               )
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                flight_no,
                origin_row["destination_id"],
                dest_row["destination_id"],
                aircraft_row["aircraft_id"],
                dep,
                arr,
                status,
                gate,
                tickets_sold
            )
        )
        conn.commit()
        print("OK: Flight added.")
    except sqlite3.IntegrityError as e:
        print("ERROR: Could not add flight:", e)

# 6) UPDATE FLIGHT STATUS
def update_flight_status(conn):
    print("\nUPDATE FLIGHT STATUS (UPDATE)")

    # Ask which flight to update
    flight_id = input("Flight ID: ").strip()
    new_status = input("New status (e.g., Scheduled/Delayed/Departed): ").strip()

    # Basic check for empty status
    if new_status == "":
        print("ERROR: status cannot be blank.")
        return

    try:
        # Update one column using the flight_id
        conn.execute(
            "UPDATE flight SET status=? WHERE flight_id=?",
            (new_status, flight_id)
        )
        conn.commit()
        print("OK: Status updated.")
    except sqlite3.IntegrityError as e:
        print("ERROR: Update failed:", e)

# 7) DELETE FLIGHT

def delete_flight(conn):
    print("\nDELETE FLIGHT (DELETE)")

    flight_id = input("Flight ID to delete: ").strip()

    # Simple safety check: confirm delete
    confirm = input("Type YES to confirm delete: ").strip().upper()
    if confirm != "YES":
        print("Delete cancelled.")
        return

    try:
        conn.execute("DELETE FROM flight WHERE flight_id=?", (flight_id,))
        conn.commit()
        print("OK: Flight deleted.")
    except sqlite3.IntegrityError as e:
        print("ERROR: Delete failed:", e)

# 8) ASSIGN PILOT TO FLIGHT

def assign_pilot_to_flight(conn):
    print("\nASSIGN PILOT TO FLIGHT (CREATE)")

    flight_id = input("Flight ID (number): ").strip()

    if not flight_id.isdigit():
        print("ERROR: Flight ID must be a number.")
        return

    # Show flight so user knows what they are assigning to
    flight = conn.execute(
        "SELECT flight_id, flight_no, status FROM flight WHERE flight_id=?",
        (flight_id,)
    ).fetchone()

    if not flight:
        print("ERROR: No flight found with that flight_id.")
        return

    print(f"Selected flight: ID={flight['flight_id']} | {flight['flight_no']} | status={flight['status']}")

    license_no = input("Pilot license_no (e.g., LIC-UK-1001): ").strip().upper()
    role = input("Role (Captain / First Officer): ").strip()

    # Find pilot_id from license number
    pilot = conn.execute(
        "SELECT pilot_id, first_name, last_name FROM pilot WHERE license_no=? AND active=1",
        (license_no,)
    ).fetchone()

    if not pilot:
        print("ERROR: Pilot not found (or inactive).")
        return

    print(f"Pilot found: ID={pilot['pilot_id']} | {pilot['first_name']} {pilot['last_name']}")

    # Insert assignment
    try:
        conn.execute(
            "INSERT INTO pilot_assignment(flight_id, pilot_id, role) VALUES (?,?,?)",
            (int(flight_id), int(pilot["pilot_id"]), role)
        )
        conn.commit()
        print("OK: Pilot assigned to flight.")
    except sqlite3.IntegrityError as e:
        print("ERROR: Assignment failed:", e)

# Show all flights for a pilot 
def view_pilot_schedule(conn):
    print("\nVIEW PILOT SCHEDULE (READ)")

    license_no = input("Pilot license_no (e.g., LIC-UK-1001): ").strip().upper()

    sql = """
    SELECT pa.assignment_id,
           pa.role,
           f.flight_id,
           f.flight_no,
           o.iata_code AS origin,
           d.iata_code AS destination,
           f.departure_dt,
           f.status
    FROM pilot p
    JOIN pilot_assignment pa ON pa.pilot_id = p.pilot_id
    JOIN flight f ON f.flight_id = pa.flight_id
    JOIN destination o ON o.destination_id = f.origin_id
    JOIN destination d ON d.destination_id = f.destination_id
    WHERE p.license_no = ?
    ORDER BY f.departure_dt;
    """

    rows = conn.execute(sql, (license_no,))
    print_rows(rows)

# 9) VIEW DESTINATION  

def view_destinations(conn):
    print("\nDESTINATIONS (READ)")

    sql = """
    SELECT destination_id, iata_code, city, country, timezone, active
    FROM destination
    ORDER BY iata_code;
    """

    rows = conn.execute(sql)
    print_rows(rows)

# 10) UPDATE DESTINATIONS
def update_destination_active(conn):
    print("\nUPDATE DESTINATION ACTIVE (UPDATE)")

    iata = input("Destination IATA code (e.g., CDG): ").strip().upper()
    active = input("Set active to 1 or 0: ").strip()

    # Simple input validation
    if active not in ["0", "1"]:
        print("ERROR: You must type 0 or 1.")
        return

    cur = conn.execute(
        "UPDATE destination SET active=? WHERE iata_code=?",
        (int(active), iata)
    )
    conn.commit()

    # rowcount tells us if a row was actually updated
    if cur.rowcount == 0:
        print("ERROR: Destination not found.")
    else:
        print("OK: Destination updated.")

# 11) FLIGHT PER DESTINATION 

def report_flights_per_destination(conn):
    print("\nREPORT: FLIGHTS PER DESTINATION (AGGREGATION)")

    sql = """
    SELECT d.iata_code AS destination,
           d.city,
           COUNT(*) AS flights_count
    FROM flight f
    JOIN destination d ON d.destination_id = f.destination_id
    GROUP BY d.destination_id
    ORDER BY flights_count DESC;
    """

    rows = conn.execute(sql)
    print_rows(rows)

# FLIGHT PER PILOT

def report_flights_per_pilot(conn):
    print("\nREPORT: FLIGHTS PER PILOT (AGGREGATION)")

    
    sql = """
    SELECT p.license_no,
           p.first_name || ' ' || p.last_name AS pilot_name,
           COUNT(*) AS flights_assigned
    FROM pilot p
    JOIN pilot_assignment pa ON pa.pilot_id = p.pilot_id
    GROUP BY p.pilot_id
    ORDER BY flights_assigned DESC;
    """

    rows = conn.execute(sql)
    print_rows(rows)

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
        print("5) Add a new flight (CREATE)")
        print("6) Update flight status (UPDATE)")
        print("7) Delete flight (DELETE)")
        print("8) Assign pilot to flight (CREATE)")
        print("9) View pilot schedule (READ)")
        print("10) View destinations (READ)")
        print("11) Update destination active flag (UPDATE)")
        print("12) Report: Flights per destination (AGGREGATION)")
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
        elif choice == "5":
            add_flight(conn)
        elif choice == "6":
            update_flight_status(conn)
        elif choice == "7":
            delete_flight(conn)
        elif choice == "8":
            assign_pilot_to_flight(conn)
        elif choice == "9":
            view_pilot_schedule(conn)
        elif choice == "10":
            view_destinations(conn)
        elif choice == "11":
            update_destination_active(conn)
        elif choice == "12":
            report_flights_per_destination(conn)
        elif choice == "13":
            report_flights_per_pilot(conn)
        elif choice == "0":
            break
        else:
            print("Please choose 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13 or 0.")

    conn.close()
    print("Goodbye!")


if __name__ == "__main__":
    main()