-- Library Management System: PL/SQL routines and audit trigger
-- Run as CAMPUS_DB after schema.sql.
-- Do not recreate LOAN_AUDIT_SEQ if it already exists.

CREATE OR REPLACE PROCEDURE borrow_book (
    p_loan_id   IN NUMBER,
    p_copy_id   IN NUMBER,
    p_member_id IN NUMBER,
    p_due_date  IN DATE
) AS
BEGIN
    SAVEPOINT borrow_book_start;

    UPDATE book_copies
       SET copy_status = 'BORROWED'
     WHERE copy_id = p_copy_id
       AND copy_status = 'AVAILABLE'
       AND NOT EXISTS (
           SELECT 1
             FROM book_loans bl
            WHERE bl.copy_id = p_copy_id
              AND bl.loan_status IN ('BORROWED', 'OVERDUE')
              AND bl.return_date IS NULL
       );

    IF SQL%ROWCOUNT = 0 THEN
        RAISE_APPLICATION_ERROR(-20001, 'Book copy does not exist or is not available.');
    END IF;

    INSERT INTO book_loans (
        loan_id, copy_id, member_id, loan_date, due_date, return_date, loan_status
    ) VALUES (
        p_loan_id, p_copy_id, p_member_id, SYSDATE, p_due_date, NULL, 'BORROWED'
    );

EXCEPTION
    WHEN OTHERS THEN
        ROLLBACK TO borrow_book_start;
        RAISE;
END;
/

CREATE OR REPLACE PROCEDURE return_book (
    p_loan_id IN NUMBER
) AS
    v_copy_id book_copies.copy_id%TYPE;
BEGIN
    SAVEPOINT return_book_start;

    SELECT copy_id
      INTO v_copy_id
      FROM book_loans
     WHERE loan_id = p_loan_id
       AND loan_status IN ('BORROWED', 'OVERDUE')
       AND return_date IS NULL
       FOR UPDATE;

    UPDATE book_loans
       SET return_date = SYSDATE,
           loan_status = 'RETURNED'
     WHERE loan_id = p_loan_id;

    UPDATE book_copies
       SET copy_status = 'AVAILABLE'
     WHERE copy_id = v_copy_id;

EXCEPTION
    WHEN NO_DATA_FOUND THEN
        ROLLBACK TO return_book_start;
        RAISE_APPLICATION_ERROR(-20002, 'Loan not found or book has already been returned.');
    WHEN OTHERS THEN
        ROLLBACK TO return_book_start;
        RAISE;
END;
/

-- Existing audit sequence: create only if it is not already present.
DECLARE
    v_count NUMBER;
BEGIN
    SELECT COUNT(*)
      INTO v_count
      FROM user_sequences
     WHERE sequence_name = 'LOAN_AUDIT_SEQ';

    IF v_count = 0 THEN
        EXECUTE IMMEDIATE 'CREATE SEQUENCE loan_audit_seq START WITH 1 INCREMENT BY 1 NOCACHE';
    END IF;
END;
/

CREATE OR REPLACE TRIGGER trg_loan_status_audit
AFTER UPDATE OF loan_status ON book_loans
FOR EACH ROW
WHEN (OLD.loan_status <> NEW.loan_status)
BEGIN
    INSERT INTO loan_audit (
        audit_id, loan_id, old_status, new_status, changed_at
    ) VALUES (
        loan_audit_seq.NEXTVAL,
        :NEW.loan_id,
        :OLD.loan_status,
        :NEW.loan_status,
        SYSDATE
    );
END;
/
