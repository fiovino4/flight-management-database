#!/usr/bin/env python3
import sqlite3
import random
from pathlib import Path
from datetime import datetime, timedelta

DB = Path(__file__).with_name("flight_management.db")
SCHEMA = Path(__file__).with_name("schema.sql")

def main():
    # Reset DB
    if DB.exists():
        DB.unlink()

    conn = sqlite3.connect(DB)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.executescript(SCHEMA.read_text(encoding="utf-8"))

    # 1) DESTINATION (15)
    destinations = [
        ("LHR","London","United Kingdom","Europe/London",1),
        ("CDG","Paris","France","Europe/Paris",1),
        ("FCO","Rome","Italy","Europe/Rome",1),
        ("JFK","New York","United States","America/New_York",1),
        ("LAX","Los Angeles","United States","America/Los_Angeles",1),
        ("DXB","Dubai","United Arab Emirates","Asia/Dubai",1),
        ("HND","Tokyo","Japan","Asia/Tokyo",1),
        ("SIN","Singapore","Singapore","Asia/Singapore",1),
        ("AMS","Amsterdam","Netherlands","Europe/Amsterdam",1),
        ("MAD","Madrid","Spain","Europe/Madrid",1),
        ("IST","Istanbul","Türkiye","Europe/Istanbul",1),
        ("DUB","Dublin","Ireland","Europe/Dublin",1),
        ("BKK","Bangkok","Thailand","Asia/Bangkok",1),
        ("SGN","Ho Chi Minh City","Vietnam","Asia/Ho_Chi_Minh",0),  # inactive edge case
        ("MNL","Manila","Philippines","Asia/Manila",1),
    ]
    conn.executemany(
        "INSERT INTO destination(iata_code,city,country,timezone,active) VALUES(?,?,?,?,?)",
        destinations
    )

    # 2) AIRCRAFT (10)
    aircraft = [
        ("G-AX01","A320-200",180,1),
        ("G-AX02","B737-800",189,1),
        ("N-AX03","B787-9",290,1),
        ("A6-AX04","A380-800",525,1),
        ("JA-AX05","A350-900",325,1),
        ("F-AX06","A321neo",220,1),
        ("EI-AX07","B777-300ER",396,1),
        ("PH-AX08","E190",100,1),
        ("EC-AX09","A330-300",300,1),
        ("HS-AX10","B767-300",260,1),
    ]
    conn.executemany(
        "INSERT INTO aircraft(registration,model,seat_capacity,active) VALUES(?,?,?,?)",
        aircraft
    )

    # FK maps
    dmap = {iata: did for did, iata in conn.execute("SELECT destination_id,iata_code FROM destination")}
    amap = {reg: aid for aid, reg in conn.execute("SELECT aircraft_id,registration FROM aircraft")}
    regs = list(amap.keys())

    # 3) PILOT (12)
    pilots = [
        ("Amelia","Wright","LIC-UK-1001","Captain","LHR",1),
        ("Noah","Bennett","LIC-UK-1002","First Officer","LHR",1),
        ("Sofia","Marino","LIC-IT-2001","Captain","FCO",1),
        ("Luca","Rossi","LIC-IT-2002","First Officer","FCO",1),
        ("Camille","Dupont","LIC-FR-3001","Captain","CDG",1),
        ("Hugo","Martin","LIC-FR-3002","First Officer","CDG",1),
        ("Aisha","Khan","LIC-US-4001","Captain","JFK",1),
        ("Ethan","Lee","LIC-US-4002","First Officer","JFK",1),
        ("Kenji","Sato","LIC-JP-5001","Captain","HND",1),
        ("Mina","Tanaka","LIC-JP-5002","First Officer","HND",1),
        ("Omar","Haddad","LIC-AE-6001","Captain","DXB",1),
        ("Layla","Nasser","LIC-AE-6002","First Officer","DXB",1),
    ]
    conn.executemany(
        """INSERT INTO pilot(first_name,last_name,license_no,rank,base_destination_id,active)
           VALUES(?,?,?,?,?,?)""",
        [(fn, ln, lic, rk, dmap[base], act) for fn, ln, lic, rk, base, act in pilots]
    )

    # 4) FLIGHT (10) — simplest: each aircraft gets exactly ONE flight (no overlap possible)
    random.seed(7)
    airports = ["LHR","CDG","FCO","JFK","LAX","DXB","HND","SIN","AMS","MAD","IST","DUB","BKK","MNL"]
    start = datetime(2026, 2, 3, 6, 0)
    gates = ["A1","B2","C4","D7","E5","Z99",None]

    flight_rows = []
    for i, reg in enumerate(regs):  # regs has 10 aircraft
        fn = f"AX{200+i}"
        o = random.choice(airports)
        d = random.choice([x for x in airports if x != o])

        aid = amap[reg]

        # simple schedule: each aircraft flight starts 3 hours after the previous one
        dep = start + timedelta(hours=i * 3)
        arr = dep + timedelta(hours=2)

        status = "Scheduled"
        if i == 4:
            status = "Cancelled"  # keep 1 cancelled flight to demonstrate your trigger

        terminal = random.choice(["T1","T2","T3",None])
        gate = random.choice(gates)

        cap = conn.execute("SELECT seat_capacity FROM aircraft WHERE aircraft_id=?", (aid,)).fetchone()[0]
        tickets = random.randint(0, cap)
        notes = random.choice([None,"Weather watch","VIP on board",None])

        flight_rows.append((
            fn, dmap[o], dmap[d], aid,
            dep.strftime("%Y-%m-%d %H:%M"),
            arr.strftime("%Y-%m-%d %H:%M"),
            status, terminal, gate, tickets, notes
        ))

    conn.executemany(
        """INSERT INTO flight(flight_no,origin_id,destination_id,aircraft_id,departure_dt,arrival_dt,status,terminal,gate,tickets_sold,notes)
           VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
        flight_rows
    )

    # 5) PILOT_ASSIGNMENT — 1 captain + 1 FO per non-cancelled flight
    pilots_db = conn.execute(
        "SELECT pilot_id, rank FROM pilot WHERE active=1 ORDER BY pilot_id"
    ).fetchall()
    captains = [pid for pid, rk in pilots_db if rk == "Captain"]
    fos = [pid for pid, rk in pilots_db if rk == "First Officer"]

    flights_db = conn.execute(
        "SELECT flight_id, status FROM flight ORDER BY departure_dt"
    ).fetchall()

    assigns = []
    ci = 0
    fi = 0
    for fid, st in flights_db:
        if st == "Cancelled":
            continue
        assigns.append((fid, captains[ci % len(captains)], "Captain")); ci += 1
        assigns.append((fid, fos[fi % len(fos)], "First Officer")); fi += 1

    conn.executemany(
        "INSERT INTO pilot_assignment(flight_id,pilot_id,role) VALUES(?,?,?)",
        assigns
    )

    conn.commit()
    conn.close()
    print("Created and populated flight_management.db")

if __name__ == "__main__":
    main()