# Flight Management Database (SQLite + Python CLI)

This repository contains a simple **database-driven application** for an airline.  
It demonstrates how a Python program (CLI) interacts with a relational database using **SQL queries** (SQLite).

The project covers:
- **CRUD** (Create, Read, Update, Delete)
- **Filtering** (destination / status / departure date)
- **JOIN queries** (pilot schedule, flight listing with origin/destination codes)
- **Aggregation reports** (GROUP BY)
- **Database integrity rules** enforced with **PRIMARY KEYS, FOREIGN KEYS, CHECKs, UNIQUE indexes, and TRIGGERs**

---

## Files in this repository

- `schema.sql`  
  Creates the database schema (tables, keys, constraints, indexes, triggers).

- `populate_db.py`  
  Rebuilds the database file and inserts sample data (destinations, aircraft, pilots, flights, pilot assignments).

- `main.py`  
  The command-line interface (menu) that runs SQL queries for staff users.

- `README.md`  
  This file.

> `flight_management.db` is **generated locally** by `populate_db.py` and is intentionally **not committed** to GitHub.

---

## How to run (GitHub Codespaces / local terminal)

### 1) Create / reset the database
```bash
rm -f flight_management.db
python populate_db.py