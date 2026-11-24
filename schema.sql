-- Library Management System: schema
-- Database: Oracle Database XE 11g
-- Run as CAMPUS_DB in a fresh schema.
-- This file creates the core tables and the availability view.
-- Run routines.sql after this file.

CREATE TABLE book_categories (
    category_id   NUMBER PRIMARY KEY,
    category_name VARCHAR2(50) NOT NULL UNIQUE
);

CREATE TABLE authors (
    author_id   NUMBER PRIMARY KEY,
    author_name VARCHAR2(100) NOT NULL
);

CREATE TABLE books (
    book_id          NUMBER PRIMARY KEY,
    title            VARCHAR2(200) NOT NULL,
    isbn             VARCHAR2(20) UNIQUE,
    category_id      NUMBER NOT NULL,
    publisher        VARCHAR2(100),
    publication_year NUMBER(4),
    CONSTRAINT fk_books_category
        FOREIGN KEY (category_id) REFERENCES book_categories(category_id)
);

CREATE TABLE book_authors (
    book_id   NUMBER NOT NULL,
    author_id NUMBER NOT NULL,
    CONSTRAINT pk_book_authors PRIMARY KEY (book_id, author_id),
    CONSTRAINT fk_book_authors_book
        FOREIGN KEY (book_id) REFERENCES books(book_id),
    CONSTRAINT fk_book_authors_author
        FOREIGN KEY (author_id) REFERENCES authors(author_id)
);

CREATE TABLE book_copies (
    copy_id     NUMBER PRIMARY KEY,
    book_id     NUMBER NOT NULL,
    copy_status VARCHAR2(20) DEFAULT 'AVAILABLE' NOT NULL,
    CONSTRAINT fk_book_copies_book
        FOREIGN KEY (book_id) REFERENCES books(book_id),
    CONSTRAINT chk_book_copy_status
        CHECK (copy_status IN ('AVAILABLE', 'BORROWED', 'DAMAGED', 'LOST'))
);

CREATE TABLE members (
    member_id   NUMBER PRIMARY KEY,
    member_name VARCHAR2(100) NOT NULL,
    email       VARCHAR2(150) NOT NULL UNIQUE,
    member_type VARCHAR2(20) DEFAULT 'STUDENT' NOT NULL,
    CONSTRAINT chk_member_type
        CHECK (member_type IN ('STUDENT', 'FACULTY'))
);

CREATE TABLE book_loans (
    loan_id     NUMBER PRIMARY KEY,
    copy_id     NUMBER NOT NULL,
    member_id   NUMBER NOT NULL,
    loan_date   DATE DEFAULT SYSDATE NOT NULL,
    due_date    DATE NOT NULL,
    return_date DATE,
    loan_status VARCHAR2(20) DEFAULT 'BORROWED' NOT NULL,
    CONSTRAINT fk_book_loans_copy
        FOREIGN KEY (copy_id) REFERENCES book_copies(copy_id),
    CONSTRAINT fk_book_loans_member
        FOREIGN KEY (member_id) REFERENCES members(member_id),
    CONSTRAINT chk_book_loan_status
        CHECK (loan_status IN ('BORROWED', 'RETURNED', 'OVERDUE')),
    CONSTRAINT chk_book_loan_due_date
        CHECK (due_date >= loan_date),
    CONSTRAINT chk_book_loan_return_date
        CHECK (return_date IS NULL OR return_date >= loan_date)
);

CREATE TABLE loan_audit (
    audit_id   NUMBER PRIMARY KEY,
    loan_id    NUMBER NOT NULL,
    old_status VARCHAR2(20),
    new_status VARCHAR2(20),
    changed_at DATE DEFAULT SYSDATE NOT NULL
);

-- A book may have multiple physical copies. This view summarizes available
-- copies for each title. The app performs additional checks for active loans.
CREATE OR REPLACE VIEW available_books_view AS
SELECT b.book_id,
       b.title,
       c.category_name,
       (SELECT COUNT(*)
          FROM book_copies bc
         WHERE bc.book_id = b.book_id
           AND bc.copy_status = 'AVAILABLE') AS available_copies
  FROM books b
  JOIN book_categories c ON c.category_id = b.category_id;
