# Library Management System

A database-driven Library Management System built using Oracle Database, SQL, PL/SQL, Python, and Streamlit. The project models books, authors, categories, physical copies, members, and borrowing records, with a browser-based interface for viewing and managing book information.

## 1. Technology Stack

- **Database:** Oracle Database XE 11g
- **Database programming:** SQL and PL/SQL
- **Backend:** Python
- **Database connectivity:** `python-oracledb` in Thick mode
- **Frontend:** Streamlit
- **Data handling:** Pandas
- **Oracle client:** Oracle Instant Client 23

## 2. Project Structure

```text
python_code/
├── app.py
├── test_connection.py
└── README.md
```

- `app.py`: Streamlit application containing the dashboard, book catalogue, and book management operations.
- `test_connection.py`: Verifies that Python can connect to Oracle and execute a query.
- `README.md`: Project documentation and setup instructions.

Additional files, such as `requirements.txt`, can be added to make the project easier to install and reproduce.

## 3. Database Schema

The database contains seven main tables.

### 3.1 BOOK_CATEGORIES

Stores the categories to which books belong.

| Column          | Description          |
| --------------- | -------------------- |
| `category_id`   | Primary key          |
| `category_name` | Name of the category |

Example categories include Fiction, Non-Fiction, Biography, Children, and Science and Technology.

### 3.2 AUTHORS

Stores author information.

| Column        | Description   |
| ------------- | ------------- |
| `author_id`   | Primary key   |
| `author_name` | Author's name |

### 3.3 BOOKS

Stores bibliographic details for each book title.

| Column             | Description                               |
| ------------------ | ----------------------------------------- |
| `book_id`          | Primary key                               |
| `title`            | Book title                                |
| `isbn`             | ISBN identifier                           |
| `category_id`      | Foreign key referencing `BOOK_CATEGORIES` |
| `publisher`        | Publisher name                            |
| `publication_year` | Year of publication                       |

### 3.4 BOOK_AUTHORS

Implements the many-to-many relationship between books and authors. A book can have multiple authors, and an author can contribute to multiple books.

| Column      | Description                       |
| ----------- | --------------------------------- |
| `book_id`   | Foreign key referencing `BOOKS`   |
| `author_id` | Foreign key referencing `AUTHORS` |

### 3.5 BOOK_COPIES

Represents individual physical copies of a book title.

| Column        | Description                             |
| ------------- | --------------------------------------- |
| `copy_id`     | Primary key identifying a physical copy |
| `book_id`     | Foreign key referencing `BOOKS`         |
| `copy_status` | Availability or condition of the copy   |

Copy statuses used in the project include `AVAILABLE`, `BORROWED`, `DAMAGED`, and `LOST`.

### 3.6 MEMBERS

Stores library member information.

| Column        | Description                                 |
| ------------- | ------------------------------------------- |
| `member_id`   | Primary key                                 |
| `member_name` | Member's name                               |
| `email`       | Email address                               |
| `member_type` | Member category, such as STUDENT or FACULTY |

### 3.7 BOOK_LOANS

Stores borrowing and return records.

| Column        | Description                           |
| ------------- | ------------------------------------- |
| `loan_id`     | Primary key                           |
| `copy_id`     | Foreign key referencing `BOOK_COPIES` |
| `member_id`   | Foreign key referencing `MEMBERS`     |
| `loan_date`   | Date the book was borrowed            |
| `due_date`    | Expected return date                  |
| `return_date` | Actual return date, if returned       |
| `loan_status` | Status of the loan                    |

Loan statuses used in the project include `BORROWED`, `RETURNED`, and `OVERDUE`.

### Entity relationships

```text
BOOK_CATEGORIES  1 ───── N  BOOKS

BOOKS            N ───── N  AUTHORS
                 through BOOK_AUTHORS

BOOKS            1 ───── N  BOOK_COPIES

BOOK_COPIES      1 ───── N  BOOK_LOANS
MEMBERS          1 ───── N  BOOK_LOANS
```

A book title and a physical copy are represented separately. This allows multiple physical copies of the same title to have independent availability and borrowing records.

## 4. SQL Queries Implemented

### 4.1 Retrieve books with their categories and authors

This query uses joins across four tables to retrieve book titles, their categories, and associated authors.

```sql
SELECT b.book_id,
       b.title,
       c.category_name,
       a.author_name
FROM books b
JOIN book_categories c
    ON b.category_id = c.category_id
JOIN book_authors ba
    ON b.book_id = ba.book_id
JOIN authors a
    ON ba.author_id = a.author_id
ORDER BY b.title;
```

### 4.2 Find available copies of books

```sql
SELECT b.title,
       COUNT(bc.copy_id) AS available_copies
FROM books b
JOIN book_copies bc
    ON b.book_id = bc.book_id
WHERE bc.copy_status = 'AVAILABLE'
GROUP BY b.title
ORDER BY b.title;
```

### 4.3 Identify overdue loans

```sql
SELECT bl.loan_id,
       m.member_name,
       b.title,
       bl.loan_date,
       bl.due_date,
       bl.loan_status
FROM book_loans bl
JOIN members m
    ON bl.member_id = m.member_id
JOIN book_copies bc
    ON bl.copy_id = bc.copy_id
JOIN books b
    ON bc.book_id = b.book_id
WHERE bl.due_date < SYSDATE
  AND bl.return_date IS NULL
ORDER BY bl.due_date;
```

This query identifies loans that have passed their due date and have not been returned. It does not automatically change the stored loan status to `OVERDUE`.

### 4.4 Find members who have borrowed books

Uses a correlated `EXISTS` subquery to identify members with at least one borrowing record.

```sql
SELECT m.member_id,
       m.member_name
FROM members m
WHERE EXISTS (
    SELECT 1
    FROM book_loans bl
    WHERE bl.member_id = m.member_id
);
```

### 4.5 Count books by category

```sql
SELECT c.category_name,
       COUNT(b.book_id) AS book_count
FROM book_categories c
LEFT JOIN books b
    ON c.category_id = b.category_id
GROUP BY c.category_id, c.category_name
ORDER BY c.category_name;
```

The `LEFT JOIN` includes categories that currently have no books.

### 4.6 Book catalogue with copy counts

The Streamlit application uses a query that combines book details, categories, and physical copies to display total and available copy counts.

```sql
SELECT b.book_id,
       b.title,
       c.category_name,
       COUNT(bc.copy_id) AS total_copies,
       NVL(
           SUM(
               CASE
                   WHEN bc.copy_status = 'AVAILABLE'
                   THEN 1
                   ELSE 0
               END
           ), 0
       ) AS available_copies
FROM books b
JOIN book_categories c
    ON b.category_id = c.category_id
LEFT JOIN book_copies bc
    ON b.book_id = bc.book_id
GROUP BY b.book_id, b.title, c.category_name
ORDER BY b.title;
```

## 5. PL/SQL Business Logic

### 5.1 BORROW_BOOK

The `BORROW_BOOK` stored procedure accepts a loan ID, physical copy ID, member ID, and due date.

Its implemented behavior includes:

- Checking whether the requested physical copy exists and is available.
- Updating the copy status to `BORROWED`.
- Inserting a new record into `BOOK_LOANS`.
- Using a savepoint and rollback to undo the operation if an error occurs.
- Raising an application error when the copy cannot be borrowed.

The procedure has been tested with both a successful borrowing operation and an unavailable-copy failure case.

### 5.2 RETURN_BOOK

The `RETURN_BOOK` stored procedure processes the return of a borrowed copy.

Its implemented behavior includes:

- Locating and locking the relevant loan record using `SELECT ... FOR UPDATE`.
- Updating the loan status to `RETURNED`.
- Recording the return date.
- Changing the physical copy's status back to `AVAILABLE`.
- Handling missing loan records with an application error.
- Rolling back changes if the operation fails.

The return workflow has been tested against the Oracle database.

### 5.3 Loan status audit

The project includes a `LOAN_AUDIT` table, `LOAN_AUDIT_SEQ` sequence, and `TRG_LOAN_STATUS_AUDIT` trigger.

The trigger records changes to `BOOK_LOANS.LOAN_STATUS`, providing a history of status transitions.

The audit mechanism has been tested by changing a loan's status and restoring its previous value, then checking the generated audit records.

## 6. Python–Oracle Connectivity

The Python application uses `python-oracledb` in Thick mode with Oracle Instant Client 23 to connect to the existing Oracle XE 11g database.

The database connection was tested successfully by executing:

```python
import oracledb

oracledb.init_oracle_client(
    lib_dir=r"C:\oracle\instantclient_23_26"
)

connection = oracledb.connect(
    user="CAMPUS_DB",
    password="YOUR_DATABASE_PASSWORD",
    dsn="localhost:1521/XE"
)

cursor = connection.cursor()
cursor.execute("SELECT USER FROM DUAL")

print(cursor.fetchone()[0])

cursor.close()
connection.close()
```

Expected output:

```text
CAMPUS_DB
```

Replace `YOUR_DATABASE_PASSWORD` with the password configured for the local database user. Do not commit credentials to source control.

## 7. Streamlit User Interface

The current interface includes the following functionality.

### Dashboard

Displays four summary metrics:

- Total book titles
- Total members
- Available physical copies
- Borrowed physical copies

### Book Catalogue

Displays book titles, categories, total physical copies, and available copies.

The catalogue includes a text-based search field for filtering books by title.

### Book Management

Provides three operations through separate tabs.

**Add Book**

- Enter a title, ISBN, category, publisher, and publication year.
- Associate one or more existing authors.
- Insert the book and its author associations into Oracle in a transaction.

**Edit Book**

- Select an existing book.
- Update its bibliographic information and category.
- Change its author associations.
- Commit changes to Oracle.

**Delete Book**

- Select a book and explicitly confirm deletion.
- Block deletion when physical copies exist.
- Remove author associations before deleting the book record.

Database changes are committed after successful transactions and rolled back if an operation raises an error.

### Current UI limitations

The following features have database support or are planned, but are not yet implemented in the Streamlit interface:

- Adding and managing physical copies
- Member registration and management
- Borrowing and returning books through the UI
- Viewing complete loan history
- Viewing audit records
- Managing categories and authors
- Automatically generating loan IDs using a database sequence

The stored borrowing and return procedures have been tested separately through Oracle, but the UI does not yet invoke them.

## 8. Setup Instructions

### Prerequisites

- Windows
- Oracle Database XE 11g with the project schema and sample data
- Python 3.14
- Oracle Instant Client 23, 64-bit
- Internet access to install Python packages

### Step 1: Install Python dependencies

Open Command Prompt and navigate to the project folder:

```cmd
cd "C:\Dikshitha\Projects\DBMS\python_code"
```

Install the dependencies:

```cmd
python -m pip install oracledb streamlit pandas
```

### Step 2: Configure the database password

In the same Command Prompt window, set the environment variable:

```cmd
set ORACLE_PASSWORD=YOUR_DATABASE_PASSWORD
```

This setting applies only to the current Command Prompt session.

### Step 3: Verify database connectivity

Run the connection test:

```cmd
python test_connection.py
```

The test should report a successful connection and identify `CAMPUS_DB` as the connected user.

### Step 4: Start the application

```cmd
python -m streamlit run app.py
```

Streamlit will provide a local URL, normally:

```text
http://localhost:8501
```

Open that URL in a browser to use the application.

## 9. Design Considerations

- **Relational modelling:** Separates book titles, physical copies, authors, categories, members, and loans into related tables.
- **Many-to-many relationships:** Uses `BOOK_AUTHORS` to represent books with multiple authors.
- **Transaction management:** Groups related changes into transactions and rolls them back when an operation fails.
- **Database-side business logic:** Implements borrowing and returning as PL/SQL stored procedures rather than duplicating their core logic in Python.
- **Auditability:** Uses a database trigger to record loan status changes.
- **Parameterized SQL:** Uses bind variables for user-provided values to reduce SQL injection risk.
- **Data integrity:** Uses foreign-key relationships and guarded deletion to preserve related records.

## 10. Future Enhancements

- Complete copy and member management.
- Integrate the existing PL/SQL borrowing and return procedures with the UI.
- Add loan history, overdue-loan views, and audit log screens.
- Use database sequences for safe ID generation.
- Add stronger validation for duplicate ISBNs and invalid loan states.
- Add automated tests for successful operations, invalid inputs, rollback behavior, and concurrent borrowing attempts.
- Improve configuration management and prepare the application for deployment.

## Project Status

The project currently has a working Oracle database, SQL queries, tested borrowing and return procedures, a loan status audit mechanism, Python connectivity, and a Streamlit interface for the dashboard, catalogue, and book-level CRUD operations.

The remaining work is to integrate the database's borrowing and return logic into the interface and add copy, member, loan history, and audit management screens.
