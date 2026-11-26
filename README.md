# Expense Tracker

A personal expense tracker. Add payments by hand or import a bank/UPI statement as CSV, then see monthly totals, a category breakdown and a month-over-month comparison. Each user has a private account.

**Stack:** Python, FastAPI, PostgreSQL, SQLAlchemy 2.0, Alembic, JWT auth, Streamlit, pytest.

## Features

- Register and log in (bcrypt-hashed passwords, JWT tokens)
- Add, list, edit and delete payments, each owned by one user
- Monthly report: total, payment count and per-category breakdown with percentages
- Daily totals and month-over-month comparison (amount and percent change)
- CSV import with duplicate skipping, per-row error reporting and keyword-based auto-categorizing
- Streamlit dashboard: login, month picker, charts, payment table with delete, add form, CSV upload

## Architecture

```
Streamlit dashboard  ->  FastAPI backend  ->  PostgreSQL
   (dashboard/)           (app/)
```

The dashboard only talks to the REST API, so it can be replaced (React, mobile) without touching the backend.

```
app/            FastAPI app: models, schemas, security, routers, CSV importer
dashboard/      Streamlit front end
migrations/     Alembic migrations
tests/          pytest suite (runs against a separate test database)
```

## Design decisions

- **Money is stored as `Numeric(12,2)` and handled as `Decimal`**, never float, so totals stay exact.
- **Reports are computed in SQL** (`SUM`, `COUNT`, `GROUP BY`) rather than by looping in Python.
- **Month filters use `date >= first day` and `date < first day of next month`**, which is correct for every month length and year boundary.
- **Schema changes go through Alembic migrations**, so existing data is kept.
- **Every payment query is filtered by the logged-in user.** Another user's payment returns 404, the same as a missing one.
- **Login errors are identical** for an unknown email and a wrong password.

## Running locally (Windows)

Requirements: Python 3.11+, PostgreSQL 16+.

1. Create two databases, `expense_tracker` and `expense_tracker_test`.
2. Create a virtual environment and install the packages:
   ```
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Create a `.env` file in the project root:
   ```
   DATABASE_URL=postgresql+psycopg2://postgres:YOUR_PASSWORD@localhost:5432/expense_tracker
   SECRET_KEY=any-long-random-string; 
   Generate a real key with: python -c "import secrets;print(secrets.token_hex(32))"
   ```
4. Create the tables:
   ```
   alembic upgrade head
   ```
5. Start the backend (API docs at http://127.0.0.1:8000/docs):
   ```
   uvicorn app.main:app --reload
   ```
6. Start the dashboard in a second terminal (opens at http://localhost:8501):
   ```
   streamlit run dashboard/app.py
   ```

## Tests

```
pytest
```

The suite covers payments, reports (including month and year boundaries and empty months), CSV import, authentication, and privacy between users. Tests run against `expense_tracker_test` and refuse to run against any database whose name does not end in `_test`.

## CSV format

```
date,description,amount,payment_method
2026-11-20,Swiggy order,420.00,UPI
```

Dates can be `YYYY-MM-DD`, `DD-MM-YYYY` or `DD/MM/YYYY`. Rows with a bad date or amount are reported, not imported. Category keywords can be edited in `app/importer.py`.

## Known limitations and next steps

- CSV import supports one simple layout so far; bank-specific statement formats still need parsers.
- Categories are shared by all users.
- Planned: Docker setup, deployment, budgets and recurring payments.