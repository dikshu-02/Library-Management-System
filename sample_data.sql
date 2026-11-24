-- Library Management System: sample data
-- Run only once, after schema.sql and routines.sql, in a fresh schema.
-- Do not run this against a schema that already contains these IDs.
-- Dates are relative to the example dataset and can be adjusted for a demo.

INSERT INTO book_categories (category_id, category_name) VALUES (1, 'Fiction');
INSERT INTO book_categories (category_id, category_name) VALUES (2, 'Non-Fiction');
INSERT INTO book_categories (category_id, category_name) VALUES (3, 'Biography');
INSERT INTO book_categories (category_id, category_name) VALUES (4, 'Children');
INSERT INTO book_categories (category_id, category_name) VALUES (5, 'Science and Technology');

INSERT INTO authors (author_id, author_name) VALUES (1, 'George Orwell');
INSERT INTO authors (author_id, author_name) VALUES (2, 'Yuval Noah Harari');
INSERT INTO authors (author_id, author_name) VALUES (3, 'Walter Isaacson');
INSERT INTO authors (author_id, author_name) VALUES (4, 'J. K. Rowling');
INSERT INTO authors (author_id, author_name) VALUES (5, 'Robert C. Martin');
INSERT INTO authors (author_id, author_name) VALUES (6, 'Jane Austen');

INSERT INTO books (book_id, title, isbn, category_id, publisher, publication_year)
VALUES (101, 'Animal Farm', 'ISBN-1001', 1, 'Secker and Warburg', 1945);
INSERT INTO books (book_id, title, isbn, category_id, publisher, publication_year)
VALUES (102, 'Sapiens', 'ISBN-1002', 2, 'Harper', 2011);
INSERT INTO books (book_id, title, isbn, category_id, publisher, publication_year)
VALUES (103, 'Steve Jobs', 'ISBN-1003', 3, 'Simon and Schuster', 2011);
INSERT INTO books (book_id, title, isbn, category_id, publisher, publication_year)
VALUES (104, 'Harry Potter and the Philosopher''s Stone', 'ISBN-1004', 4, 'Bloomsbury', 1997);
INSERT INTO books (book_id, title, isbn, category_id, publisher, publication_year)
VALUES (105, 'Clean Code', 'ISBN-1005', 5, 'Prentice Hall', 2008);
INSERT INTO books (book_id, title, isbn, category_id, publisher, publication_year)
VALUES (106, 'Pride and Prejudice', 'ISBN-1006', 1, 'T. Egerton', 1813);

INSERT INTO book_authors (book_id, author_id) VALUES (101, 1);
INSERT INTO book_authors (book_id, author_id) VALUES (102, 2);
INSERT INTO book_authors (book_id, author_id) VALUES (103, 3);
INSERT INTO book_authors (book_id, author_id) VALUES (104, 4);
INSERT INTO book_authors (book_id, author_id) VALUES (105, 5);
INSERT INTO book_authors (book_id, author_id) VALUES (106, 6);

INSERT INTO book_copies (copy_id, book_id, copy_status) VALUES (1001, 101, 'BORROWED');
INSERT INTO book_copies (copy_id, book_id, copy_status) VALUES (1002, 101, 'AVAILABLE');
INSERT INTO book_copies (copy_id, book_id, copy_status) VALUES (1003, 102, 'BORROWED');
INSERT INTO book_copies (copy_id, book_id, copy_status) VALUES (1004, 103, 'AVAILABLE');
INSERT INTO book_copies (copy_id, book_id, copy_status) VALUES (1005, 104, 'AVAILABLE');
INSERT INTO book_copies (copy_id, book_id, copy_status) VALUES (1006, 104, 'AVAILABLE');
INSERT INTO book_copies (copy_id, book_id, copy_status) VALUES (1007, 105, 'BORROWED');
INSERT INTO book_copies (copy_id, book_id, copy_status) VALUES (1008, 106, 'AVAILABLE');

INSERT INTO members (member_id, member_name, email, member_type)
VALUES (201, 'Ananya Kumar', 'ananya@example.com', 'STUDENT');
INSERT INTO members (member_id, member_name, email, member_type)
VALUES (202, 'Rahul Sharma', 'rahul@example.com', 'STUDENT');
INSERT INTO members (member_id, member_name, email, member_type)
VALUES (203, 'Priya Nair', 'priya@example.com', 'FACULTY');
INSERT INTO members (member_id, member_name, email, member_type)
VALUES (204, 'Arjun Patel', 'arjun@example.com', 'STUDENT');

-- The sample includes two active overdue/current loans and one returned loan.
-- The copy statuses are aligned with the loan records.
INSERT INTO book_loans (loan_id, copy_id, member_id, loan_date, due_date, return_date, loan_status)
VALUES (301, 1001, 201, DATE '2026-10-01', DATE '2026-10-15', NULL, 'OVERDUE');
INSERT INTO book_loans (loan_id, copy_id, member_id, loan_date, due_date, return_date, loan_status)
VALUES (302, 1003, 202, DATE '2026-09-20', DATE '2026-10-04', NULL, 'OVERDUE');
INSERT INTO book_loans (loan_id, copy_id, member_id, loan_date, due_date, return_date, loan_status)
VALUES (303, 1004, 203, DATE '2026-09-10', DATE '2026-09-24', DATE '2026-09-22', 'RETURNED');
INSERT INTO book_loans (loan_id, copy_id, member_id, loan_date, due_date, return_date, loan_status)
VALUES (304, 1007, 204, DATE '2026-10-05', DATE '2026-10-19', NULL, 'BORROWED');

COMMIT;
