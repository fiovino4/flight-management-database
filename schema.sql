-- Defines the database schema, constraints, triggers and indexes for the Flight Management system.

-- Enforce foreign key constraints (SQLite does not enforce them unless enabled per connection)
PRAGMA foreign_keys = ON;

-- Drop tables in dependency order so we can rebuild cleanly during development/testing.
DROP TABLE IF EXISTS pilot_assignment;
DROP TABLE IF EXISTS flight;
DROP TABLE IF EXISTS pilot;
DROP TABLE IF EXISTS aircraft;
DROP TABLE IF EXISTS destination;

-- 1) DESTINATION
CREATE TABLE destination (
  destination_id INTEGER PRIMARY KEY AUTOINCREMENT,
  iata_code TEXT NOT NULL UNIQUE CHECK (length(iata_code) = 3), -- basic IATA format check (e.g., LHR)
  city TEXT NOT NULL,
  country TEXT NOT NULL,
  timezone TEXT NOT NULL, -- stored as IANA TZ string (e.g., Europe/London)
  active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0,1)) -- boolean-style flag
);

-- 2) AIRCRAFT
CREATE TABLE aircraft (
  aircraft_id INTEGER PRIMARY KEY AUTOINCREMENT, -- unique aircraft registration (e.g., G-AX01)
  registration TEXT NOT NULL UNIQUE,
  model TEXT NOT NULL,
  seat_capacity INTEGER NOT NULL CHECK (seat_capacity > 0), -- must be a positive capacity
  active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0,1))
);

-- 3) PILOT
CREATE TABLE pilot (
  pilot_id INTEGER PRIMARY KEY AUTOINCREMENT,
  first_name TEXT NOT NULL,
  last_name TEXT NOT NULL,
  license_no TEXT NOT NULL UNIQUE, -- unique license ID (e.g., LIC-UK-1001)
  rank TEXT NOT NULL CHECK (rank IN ('Captain','First Officer')),
  base_destination_id INTEGER, -- optional FK to destination (pilot base airport)
  active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0,1)),
  FOREIGN KEY (base_destination_id) REFERENCES destination(destination_id)
);

-- 4) FLIGHT
CREATE TABLE flight (
  flight_id INTEGER PRIMARY KEY AUTOINCREMENT,  -- e.g., AX200
  flight_no TEXT NOT NULL, -- FK to destination (origin airport)
  origin_id INTEGER NOT NULL, -- FK to destination (arrival airport)
  destination_id INTEGER NOT NULL, -- FK to aircraft operating the flight
  aircraft_id INTEGER NOT NULL,
  departure_dt TEXT NOT NULL,   -- 'YYYY-MM-DD HH:MM'
  arrival_dt TEXT NOT NULL,   -- 'YYYY-MM-DD HH:MM'
  status TEXT NOT NULL DEFAULT 'Scheduled'
    CHECK (status IN ('Scheduled','Boarding','Departed','Delayed','Cancelled','Arrived')),
  terminal TEXT,
  gate TEXT,
  tickets_sold INTEGER NOT NULL DEFAULT 0 CHECK (tickets_sold >= 0),
  notes TEXT,

-- Foreign keys ensure referenced records exist
  FOREIGN KEY (origin_id) REFERENCES destination(destination_id),
  FOREIGN KEY (destination_id) REFERENCES destination(destination_id),
  FOREIGN KEY (aircraft_id) REFERENCES aircraft(aircraft_id),

  -- Business rules enforced at the data layer
  CHECK (origin_id <> destination_id),  -- cannot fly to same airport
  CHECK (arrival_dt > departure_dt), -- arrival must be after departure

  -- Gate format like A1, B12 (blank allowed)
  CHECK (gate IS NULL OR gate = '' OR gate GLOB '[A-Z][0-9]*')
);

-- flight number unique per departure day (dep_date derived from departure_dt)
CREATE UNIQUE INDEX ux_flightno_day
ON flight (flight_no, substr(departure_dt,1,10));

-- 5) PILOT_ASSIGNMENT links pilots to flights with a role. ON DELETE CASCADE removes assignments automatically if a flight is deleted.
CREATE TABLE pilot_assignment (
  assignment_id INTEGER PRIMARY KEY AUTOINCREMENT,
  flight_id INTEGER NOT NULL,
  pilot_id INTEGER NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('Captain','First Officer')),
  assigned_at TEXT NOT NULL DEFAULT (datetime('now')),

  -- Prevent duplicate assignment of the same pilot to the same flight
  UNIQUE (flight_id, pilot_id),
  FOREIGN KEY (flight_id) REFERENCES flight(flight_id) ON DELETE CASCADE,
  FOREIGN KEY (pilot_id) REFERENCES pilot(pilot_id)
);

-- Only ONE Captain per flight
CREATE UNIQUE INDEX ux_one_captain_per_flight
ON pilot_assignment(flight_id)
WHERE role = 'Captain';

-- Tickets_sold must not exceed aircraft seat_capacity
CREATE TRIGGER trg_ticket_capacity_ins
BEFORE INSERT ON flight
BEGIN
  SELECT CASE
    WHEN NEW.tickets_sold >
         (SELECT seat_capacity FROM aircraft WHERE aircraft_id = NEW.aircraft_id)
    THEN RAISE(ABORT, 'tickets_sold exceeds aircraft capacity')
  END;
END;

CREATE TRIGGER trg_ticket_capacity_upd
BEFORE UPDATE OF tickets_sold, aircraft_id ON flight
BEGIN
  SELECT CASE
    WHEN NEW.tickets_sold >
         (SELECT seat_capacity FROM aircraft WHERE aircraft_id = NEW.aircraft_id)
    THEN RAISE(ABORT, 'tickets_sold exceeds aircraft capacity')
  END;
END;

-- Aircraft cannot be scheduled for overlapping flights
CREATE TRIGGER trg_no_overlap_aircraft_ins
BEFORE INSERT ON flight
BEGIN
  SELECT CASE
    WHEN EXISTS (
      SELECT 1
      FROM flight f
      WHERE f.aircraft_id = NEW.aircraft_id
        AND NOT (NEW.arrival_dt <= f.departure_dt OR NEW.departure_dt >= f.arrival_dt)
    )
    THEN RAISE(ABORT, 'Aircraft has an overlapping flight schedule')
  END;
END;

CREATE TRIGGER trg_no_overlap_aircraft_upd
BEFORE UPDATE OF aircraft_id, departure_dt, arrival_dt ON flight
BEGIN
  SELECT CASE
    WHEN EXISTS (
      SELECT 1
      FROM flight f
      WHERE f.aircraft_id = NEW.aircraft_id
        AND f.flight_id <> NEW.flight_id
        AND NOT (NEW.arrival_dt <= f.departure_dt OR NEW.departure_dt >= f.arrival_dt)
    )
    THEN RAISE(ABORT, 'Aircraft has an overlapping flight schedule')
  END;
END;

-- Cannot assign pilots to Cancelled flights
CREATE TRIGGER trg_no_assign_cancelled
BEFORE INSERT ON pilot_assignment
BEGIN
  SELECT CASE
    WHEN (SELECT status FROM flight WHERE flight_id = NEW.flight_id) = 'Cancelled'
    THEN RAISE(ABORT, 'Cannot assign pilots to a Cancelled flight')
  END;
END;

-- Helpful indexes
CREATE INDEX idx_flight_dest ON flight(destination_id); -- filtering/grouping by destination
CREATE INDEX idx_flight_dep  ON flight(departure_dt); -- ordering and date filtering
CREATE INDEX idx_assign_pilot ON pilot_assignment(pilot_id); -- pilot schedule lookups