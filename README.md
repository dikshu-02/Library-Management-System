# Library Management System

A database-driven Library Management System built with **Python, Streamlit, Oracle Database, SQL, and PL/SQL**. It provides a web interface for managing books, physical copies, members, borrowing and returns, loan history, and loan-status audit records.

## Features

- **Dashboard** — overview of titles, physical copies, members, available copies, active loans, overdue loans, copy status, and recent loans.
- **Books & Copies** — browse and search the catalogue; add, edit, and delete eligible book records; add physical copies; update copy condition.
- **Members** — register, search, edit, and delete members who have no loan history.
- **Borrow Book** — select an available physical copy and a member; create a loan through the `BORROW_BOOK` stored procedure.
- **Return Book** — return an active loan through the `RETURN_BOOK` stored procedure.
- **Loan History** — filter and search loan records and export filtered results to CSV.
- **Audit Log** — review status transitions recorded by the `TRG_LOAN_STATUS_AUDIT` trigger and export results to CSV.

## Technology stack

- Python 3
- Streamlit
- pandas
- `python-oracledb` in Thick mode
- Oracle Database XE 11g
- Oracle Instant Client (configured locally)
- SQL and PL/SQL

## Project files

| File | Purpose |
|---|---|
| `app.py` | Streamlit user interface and database operations |
| `schema.sql` | Creates the database tables, constraints, and availability view |
| `routines.sql` | Creates the borrow/return procedures, audit sequence, and audit trigger |
| `sample_data.sql` | Inserts sample categories, authors, books, copies, members, and loan records |
| `setup_sequences.py` | Creates the four application ID sequences if they do not already exist |
| `requirements.txt` | Python package dependencies |

> **Important:** Run `sample_data.sql` only against a fresh/empty schema. Do not rerun it against a database that already contains these IDs. It is sample data, not a migration script.

## Database design

The project uses these core tables:

- `BOOK_CATEGORIES` — book categories.
- `AUTHORS` — author records.
- `BOOKS` — book metadata and category reference.
- `BOOK_AUTHORS` — many-to-many relationship between books and authors.
- `BOOK_COPIES` — individual physical copies and their condition/availability status.
- `MEMBERS` — library members.
- `BOOK_LOANS` — borrowing and return transactions.
- `LOAN_AUDIT` — history of loan-status transitions.

The schema uses primary keys, foreign keys, unique constraints, and check constraints to protect data integrity. A book title represents a catalogue entry; each physical item is represented separately in `BOOK_COPIES`.

### Borrowing and returning

The Streamlit app calls `BORROW_BOOK` to create a loan and mark its copy as borrowed. It calls `RETURN_BOOK` to mark the loan returned and make the copy available again. These operations should be performed through the procedures rather than by manually editing the related loan/copy status fields.

The `TRG_LOAN_STATUS_AUDIT` trigger inserts a row into `LOAN_AUDIT` when a loan's `LOAN_STATUS` changes. The audit sequence `LOAN_AUDIT_SEQ` generates audit IDs.

### ID generation

`setup_sequences.py` creates these sequences if missing:

- `BOOK_ID_SEQ`
- `COPY_ID_SEQ`
- `MEMBER_ID_SEQ`
- `LOAN_ID_SEQ`

Sequences generate unique ID values; gaps are normal. They do not guarantee gapless numbering. The existing `LOAN_AUDIT_SEQ` is used by the audit trigger and is not recreated by the setup script.

## Prerequisites

1. Oracle Database XE 11g is installed and running.
2. A database user named `CAMPUS_DB` has been created and has permission to create the project's tables, sequences, procedures, triggers, and view.
3. Python is installed.
4. Oracle Instant Client is installed. The current `app.py` expects it at:
   `C:\oracle\instantclient_23_26`
5. The Oracle service is reachable at:
   `localhost:1521/XE`

If Instant Client is installed in a different directory, update `ORACLE_CLIENT_DIR` in `app.py` and the corresponding path in `setup_sequences.py` if that script uses it.

## Installation and setup

### 1. Install Python dependencies

Open PowerShell or Command Prompt in the project folder and run:

```powershell
python -m pip install -r requirements.txt
```

### 2. Create the database objects

Connect to the Oracle database as `CAMPUS_DB` using an Oracle SQL execution tool available in your environment, then run these scripts in order:

1. `schema.sql`
2. `routines.sql`
3. `sample_data.sql` — only for a fresh schema

The scripts are provided separately so the schema, PL/SQL logic, and seed records are easy to inspect. If you do not have SQL Developer or SQL*Plus installed, you can execute SQL through a Python script using `python-oracledb`; SQL scripts containing SQL*Plus commands such as `/` delimiters may need to be split and executed statement by statement.

### 3. Create application ID sequences

From the project folder, set the database password and run the sequence setup script:

```powershell
$env:ORACLE_PASSWORD = "your_actual_database_password"
python setup_sequences.py
```

In Command Prompt (`cmd.exe`), use:

```bat
set ORACLE_PASSWORD=your_actual_database_password
python setup_sequences.py
```

The sequence setup script checks for existing application sequences and leaves them unchanged. Run it as `CAMPUS_DB`.

### 4. Start Streamlit

PowerShell:

```powershell
$env:ORACLE_PASSWORD = "your_actual_database_password"
python -m streamlit run app.py
```

Command Prompt:

```bat
set ORACLE_PASSWORD=your_actual_database_password
python -m streamlit run app.py
```

Open the local URL printed by Streamlit, typically `http://localhost:8501`.

Keep your database password private. The commands above set it for the current terminal session only.

## Suggested test workflow

1. Open the Dashboard and confirm the metrics load.
2. Search for a book in Books & Copies.
3. Register a test member.
4. Borrow an available copy.
5. Confirm the loan appears in Loan History.
6. Return the loan and confirm the copy becomes available.
7. Check Audit Log for the loan-status transition.
8. Try searching and downloading the filtered loan history/audit log as CSV.

Use a test member and an available copy when testing borrow/return functionality.

## Data integrity notes

- A copy with an active, unreturned loan should not be borrowed again.
- A member with loan history should not be deleted because historical loans reference that member.
- A book with copies or historical loan dependencies should not be deleted.
- Do not manually change loan statuses or copy statuses for normal borrowing/return workflows; use the stored procedures.
- If existing test data was modified manually during development, check for inconsistent copy and loan statuses before demonstrating the application.

## Troubleshooting

- **Missing `ORACLE_PASSWORD`:** Set the environment variable in the same terminal before running the app.
- **Oracle client initialization error:** Confirm that the Instant Client path exists and matches `ORACLE_CLIENT_DIR`.
- **Connection refused / listener error:** Check that Oracle XE and its listener are running and that `localhost:1521/XE` is correct.
- **Sequence not found:** Run `setup_sequences.py` as `CAMPUS_DB`.
- **Missing table, procedure, view, or trigger:** Run the corresponding SQL script as `CAMPUS_DB` and review any Oracle errors.
- **Duplicate ISBN or email:** ISBN and member email values are unique in the schema.
- **Sample data duplicate-key errors:** The sample data was already inserted. Do not run `sample_data.sql` again without intentionally resetting the schema.

## Notes

This is an educational project. The sample data is fictional and intended for local development and demonstration. Before using this as a production library system, add authentication and authorization, stronger input validation, deployment secrets management, backups, and more comprehensive transaction/concurrency testing.
