import os
from datetime import date, timedelta

import oracledb
import pandas as pd
import streamlit as st


# ---------------------------------------------------------------------------
# Configuration and Oracle connection
# ---------------------------------------------------------------------------
ORACLE_CLIENT_DIR = r"C:\oracle\instantclient_23_26"
DB_USER = "CAMPUS_DB"
DB_DSN = "localhost:1521/XE"


st.set_page_config(
    page_title="Library Management System",
    page_icon="📚",
    layout="wide",
)


@st.cache_resource
def get_connection_pool():
    """Create one reusable Oracle connection pool for the Streamlit app."""
    oracledb.init_oracle_client(lib_dir=ORACLE_CLIENT_DIR)
    return oracledb.create_pool(
        user=DB_USER,
        password=os.environ["ORACLE_PASSWORD"],
        dsn=DB_DSN,
        min=1,
        max=5,
        increment=1,
    )


def fetch_all(query, params=None):
    """Run a SELECT query and return its results as a DataFrame."""
    pool = get_connection_pool()
    with pool.acquire() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, params or {})
            rows = cursor.fetchall()
            columns = [column[0] for column in cursor.description] if cursor.description else []
    return pd.DataFrame(rows, columns=columns)


def fetch_one(query, params=None):
    """Run a SELECT query and return one row as a tuple, or None."""
    pool = get_connection_pool()
    with pool.acquire() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, params or {})
            return cursor.fetchone()


def execute_transaction(operation):
    """Run a database operation atomically."""
    pool = get_connection_pool()
    with pool.acquire() as connection:
        try:
            with connection.cursor() as cursor:
                result = operation(cursor)
            connection.commit()
            return result
        except Exception:
            connection.rollback()
            raise


def next_sequence_value(cursor, sequence_name):
    # sequence_name is always one of the hard-coded names used in this app.
    cursor.execute(f"SELECT {sequence_name}.NEXTVAL FROM dual")
    return cursor.fetchone()[0]


def show_db_error(error, action="Database operation"):
    st.error(f"{action} failed.")
    st.exception(error)


# ---------------------------------------------------------------------------
# Data access helpers
# ---------------------------------------------------------------------------
def load_categories():
    return fetch_all(
        "SELECT category_id, category_name FROM book_categories ORDER BY category_name"
    )


def load_authors():
    return fetch_all("SELECT author_id, author_name FROM authors ORDER BY author_name")


def load_books():
    return fetch_all(
        """
        SELECT b.book_id, b.title, b.isbn, c.category_name, b.publisher,
               b.publication_year,
               (SELECT COUNT(*) FROM book_copies bc WHERE bc.book_id = b.book_id) AS total_copies,
               (SELECT COUNT(*)
                  FROM book_copies bc
                 WHERE bc.book_id = b.book_id
                   AND bc.copy_status = 'AVAILABLE'
                   AND NOT EXISTS (
                       SELECT 1 FROM book_loans bl
                        WHERE bl.copy_id = bc.copy_id
                          AND bl.loan_status IN ('BORROWED', 'OVERDUE')
                          AND bl.return_date IS NULL
                   )) AS available_copies
          FROM books b
          JOIN book_categories c ON c.category_id = b.category_id
         ORDER BY b.title
        """
    )


def load_members():
    return fetch_all(
        """
        SELECT member_id, member_name, email, member_type
          FROM members
         ORDER BY member_name
        """
    )


def load_available_copies():
    return fetch_all(
        """
        SELECT bc.copy_id, b.title, bc.book_id
          FROM book_copies bc
          JOIN books b ON b.book_id = bc.book_id
         WHERE bc.copy_status = 'AVAILABLE'
           AND NOT EXISTS (
               SELECT 1 FROM book_loans bl
                WHERE bl.copy_id = bc.copy_id
                  AND bl.loan_status IN ('BORROWED', 'OVERDUE')
                  AND bl.return_date IS NULL
           )
         ORDER BY b.title, bc.copy_id
        """
    )


def load_active_loans():
    return fetch_all(
        """
        SELECT bl.loan_id, bl.copy_id, b.title, m.member_name, m.member_id,
               bl.loan_date, bl.due_date, bl.loan_status
          FROM book_loans bl
          JOIN book_copies bc ON bc.copy_id = bl.copy_id
          JOIN books b ON b.book_id = bc.book_id
          JOIN members m ON m.member_id = bl.member_id
         WHERE bl.loan_status IN ('BORROWED', 'OVERDUE')
           AND bl.return_date IS NULL
         ORDER BY bl.due_date, bl.loan_id
        """
    )


def load_loan_history():
    return fetch_all(
        """
        SELECT bl.loan_id, b.title, bc.copy_id, m.member_name, m.member_id,
               bl.loan_date, bl.due_date, bl.return_date, bl.loan_status,
               CASE
                 WHEN bl.return_date IS NOT NULL
                   THEN GREATEST(TRUNC(bl.return_date) - TRUNC(bl.due_date), 0)
                 WHEN TRUNC(SYSDATE) > TRUNC(bl.due_date)
                   THEN TRUNC(SYSDATE) - TRUNC(bl.due_date)
                 ELSE 0
               END AS overdue_days
          FROM book_loans bl
          JOIN book_copies bc ON bc.copy_id = bl.copy_id
          JOIN books b ON b.book_id = bc.book_id
          JOIN members m ON m.member_id = bl.member_id
         ORDER BY bl.loan_date DESC, bl.loan_id DESC
        """
    )


# ---------------------------------------------------------------------------
# Page header
# ---------------------------------------------------------------------------
st.title("📚 Library Management System")
st.caption("Manage books, physical copies, members, borrowing, returns, and loan records.")

# Load shared lookup data. Errors are handled here so the app can explain setup issues.
try:
    categories_df = load_categories()
    authors_df = load_authors()
except Exception as error:
    st.error("Could not load the library database. Check your Oracle connection and schema.")
    st.exception(error)
    st.stop()

if categories_df.empty:
    st.warning("No book categories were found. Add categories to BOOK_CATEGORIES before managing books.")
    st.stop()

category_options = {
    str(row["CATEGORY_NAME"]): int(row["CATEGORY_ID"])
    for _, row in categories_df.iterrows()
}
category_names = list(category_options.keys())

author_options = {
    str(row["AUTHOR_NAME"]): int(row["AUTHOR_ID"])
    for _, row in authors_df.iterrows()
}
author_names = list(author_options.keys())


# ---------------------------------------------------------------------------
# Main navigation
# ---------------------------------------------------------------------------
tabs = st.tabs(
    [
        "📊 Dashboard",
        "📚 Books & Copies",
        "👥 Members",
        "📤 Borrow Book",
        "📥 Return Book",
        "🧾 Loan History",
        "🔎 Audit Log",
    ]
)


# ---------------------------------------------------------------------------
# 1. Dashboard
# ---------------------------------------------------------------------------
with tabs[0]:
    st.subheader("Library Overview")
    try:
        metrics = fetch_one(
            """
            SELECT
              (SELECT COUNT(*) FROM books) AS titles,
              (SELECT COUNT(*) FROM book_copies) AS copies,
              (SELECT COUNT(*) FROM members) AS members,
              (SELECT COUNT(*) FROM book_copies bc
                WHERE bc.copy_status = 'AVAILABLE'
                  AND NOT EXISTS (
                    SELECT 1 FROM book_loans bl
                     WHERE bl.copy_id = bc.copy_id
                       AND bl.loan_status IN ('BORROWED', 'OVERDUE')
                       AND bl.return_date IS NULL
                  )) AS available_copies,
              (SELECT COUNT(*) FROM book_loans
                WHERE loan_status IN ('BORROWED', 'OVERDUE')
                  AND return_date IS NULL) AS active_loans,
              (SELECT COUNT(*) FROM book_loans
                WHERE return_date IS NULL
                  AND loan_status IN ('BORROWED', 'OVERDUE')
                  AND TRUNC(due_date) < TRUNC(SYSDATE)) AS overdue_loans
            FROM dual
            """
        )
        titles, copies, members, available_copies, active_loans, overdue_loans = metrics
        metric_cols = st.columns(6)
        metric_cols[0].metric("Book Titles", titles)
        metric_cols[1].metric("Physical Copies", copies)
        metric_cols[2].metric("Members", members)
        metric_cols[3].metric("Available Copies", available_copies)
        metric_cols[4].metric("Active Loans", active_loans)
        metric_cols[5].metric("Overdue Loans", overdue_loans)

        left, right = st.columns(2)
        with left:
            st.markdown("#### Copies by Status")
            status_df = fetch_all(
                """
                SELECT copy_status AS status, COUNT(*) AS copies
                  FROM book_copies
                 GROUP BY copy_status
                 ORDER BY copy_status
                """
            )
            if not status_df.empty:
                st.bar_chart(status_df.set_index("STATUS")["COPIES"])
            else:
                st.info("No physical copies have been added yet.")
        with right:
            st.markdown("#### Most Borrowed Books")
            # Use ROWNUM for compatibility with Oracle XE 11g.
            popular_df = fetch_all(
                """
                SELECT title, loan_count
                  FROM (
                    SELECT b.title AS title, COUNT(*) AS loan_count
                      FROM book_loans bl
                      JOIN book_copies bc ON bc.copy_id = bl.copy_id
                      JOIN books b ON b.book_id = bc.book_id
                     GROUP BY b.title
                     ORDER BY loan_count DESC, b.title
                  )
                 WHERE ROWNUM <= 5
                """
            )
            if not popular_df.empty:
                st.dataframe(popular_df, use_container_width=True, hide_index=True)
            else:
                st.info("No loan records are available yet.")

        st.markdown("#### Recently Recorded Loans")
        recent_df = fetch_all(
            """
            SELECT loan_id, title, member_name, loan_date, due_date, loan_status
              FROM (
                SELECT bl.loan_id, b.title, m.member_name, bl.loan_date,
                       bl.due_date, bl.loan_status
                  FROM book_loans bl
                  JOIN book_copies bc ON bc.copy_id = bl.copy_id
                  JOIN books b ON b.book_id = bc.book_id
                  JOIN members m ON m.member_id = bl.member_id
                 ORDER BY bl.loan_date DESC, bl.loan_id DESC
              )
             WHERE ROWNUM <= 10
            """
        )
        st.dataframe(recent_df, use_container_width=True, hide_index=True)
    except Exception as error:
        show_db_error(error, "Loading dashboard")


# ---------------------------------------------------------------------------
# 2. Books & Copies
# ---------------------------------------------------------------------------
with tabs[1]:
    book_subtabs = st.tabs(["Catalogue", "Add Book", "Edit Book", "Delete Book", "Manage Copies"])

    with book_subtabs[0]:
        st.markdown("#### Book Catalogue")
        search_text = st.text_input("Search by title, ISBN, or publisher", key="book_search")
        try:
            books_df = load_books()
            if search_text.strip():
                mask = (
                    books_df["TITLE"].astype(str).str.contains(search_text, case=False, na=False)
                    | books_df["ISBN"].astype(str).str.contains(search_text, case=False, na=False)
                    | books_df["PUBLISHER"].astype(str).str.contains(search_text, case=False, na=False)
                )
                books_df = books_df[mask]
            st.dataframe(books_df, use_container_width=True, hide_index=True)
        except Exception as error:
            show_db_error(error, "Loading catalogue")

    with book_subtabs[1]:
        st.markdown("#### Add a Book")
        with st.form("add_book_form", clear_on_submit=True):
            new_title = st.text_input("Title", max_chars=200)
            new_isbn = st.text_input("ISBN (optional)", max_chars=20)
            new_category = st.selectbox("Category", category_names)
            new_publisher = st.text_input("Publisher (optional)", max_chars=100)
            new_year = st.number_input(
                "Publication year (optional; enter 0 if unknown)",
                min_value=0, max_value=9999, value=0, step=1
            )
            new_authors = st.multiselect("Authors", author_names)
            add_book_clicked = st.form_submit_button("Add Book", type="primary")

        if add_book_clicked:
            if not new_title.strip():
                st.warning("Please enter a book title.")
            else:
                try:
                    def add_book(cursor):
                        book_id = next_sequence_value(cursor, "BOOK_ID_SEQ")
                        cursor.execute(
                            """
                            INSERT INTO books
                                (book_id, title, isbn, category_id, publisher, publication_year)
                            VALUES
                                (:book_id, :title, :isbn, :category_id, :publisher, :publication_year)
                            """,
                            {
                                "book_id": book_id,
                                "title": new_title.strip(),
                                "isbn": new_isbn.strip() or None,
                                "category_id": category_options[new_category],
                                "publisher": new_publisher.strip() or None,
                                "publication_year": new_year or None,
                            },
                        )
                        for author_name in new_authors:
                            cursor.execute(
                                "INSERT INTO book_authors (book_id, author_id) VALUES (:book_id, :author_id)",
                                {"book_id": book_id, "author_id": author_options[author_name]},
                            )
                        return book_id

                    created_id = execute_transaction(add_book)
                    st.success(f"Book added successfully. Book ID: {created_id}")
                    st.rerun()
                except Exception as error:
                    show_db_error(error, "Adding book")

    with book_subtabs[2]:
        st.markdown("#### Edit Book Details")
        try:
            editable_books = fetch_all(
                "SELECT book_id, title FROM books ORDER BY title"
            )
            if editable_books.empty:
                st.info("Add a book before trying to edit one.")
            else:
                book_labels = {
                    f'{row["TITLE"]} (ID: {int(row["BOOK_ID"])})': int(row["BOOK_ID"])
                    for _, row in editable_books.iterrows()
                }
                selected_book_label = st.selectbox("Select a book", list(book_labels.keys()), key="edit_book_select")
                selected_book_id = book_labels[selected_book_label]
                selected_book = fetch_one(
                    """
                    SELECT title, isbn, category_id, publisher, publication_year
                      FROM books WHERE book_id = :book_id
                    """,
                    {"book_id": selected_book_id},
                )
                selected_author_ids = fetch_all(
                    "SELECT author_id FROM book_authors WHERE book_id = :book_id",
                    {"book_id": selected_book_id},
                )["AUTHOR_ID"].astype(int).tolist()
                category_label_by_id = {value: key for key, value in category_options.items()}
                author_names_by_id = {value: key for key, value in author_options.items()}

                with st.form("edit_book_form"):
                    edit_title = st.text_input("Title", value=selected_book[0] or "", max_chars=200)
                    edit_isbn = st.text_input("ISBN (optional)", value=selected_book[1] or "", max_chars=20)
                    default_category = category_label_by_id.get(int(selected_book[2]), category_names[0])
                    edit_category = st.selectbox(
                        "Category", category_names, index=category_names.index(default_category)
                    )
                    edit_publisher = st.text_input("Publisher (optional)", value=selected_book[3] or "", max_chars=100)
                    edit_year = st.number_input(
                        "Publication year (0 if unknown)",
                        min_value=0, max_value=9999,
                        value=int(selected_book[4] or 0), step=1
                    )
                    default_author_names = [
                        author_names_by_id[author_id]
                        for author_id in selected_author_ids
                        if author_id in author_names_by_id
                    ]
                    edit_authors = st.multiselect(
                        "Authors", author_names, default=default_author_names
                    )
                    edit_clicked = st.form_submit_button("Save Changes", type="primary")

                if edit_clicked:
                    if not edit_title.strip():
                        st.warning("The title cannot be empty.")
                    else:
                        def update_book(cursor):
                            cursor.execute(
                                """
                                UPDATE books
                                   SET title = :title, isbn = :isbn, category_id = :category_id,
                                       publisher = :publisher, publication_year = :publication_year
                                 WHERE book_id = :book_id
                                """,
                                {
                                    "title": edit_title.strip(),
                                    "isbn": edit_isbn.strip() or None,
                                    "category_id": category_options[edit_category],
                                    "publisher": edit_publisher.strip() or None,
                                    "publication_year": edit_year or None,
                                    "book_id": selected_book_id,
                                },
                            )
                            cursor.execute(
                                "DELETE FROM book_authors WHERE book_id = :book_id",
                                {"book_id": selected_book_id},
                            )
                            for author_name in edit_authors:
                                cursor.execute(
                                    "INSERT INTO book_authors (book_id, author_id) VALUES (:book_id, :author_id)",
                                    {"book_id": selected_book_id, "author_id": author_options[author_name]},
                                )

                        execute_transaction(update_book)
                        st.success("Book details updated.")
                        st.rerun()
        except Exception as error:
            show_db_error(error, "Editing book")

    with book_subtabs[3]:
        st.markdown("#### Delete a Book")
        st.warning("A book can only be deleted when it has no physical copies or loan records.")
        try:
            deletable_books = fetch_all(
                """
                SELECT b.book_id, b.title
                  FROM books b
                 WHERE NOT EXISTS (SELECT 1 FROM book_copies bc WHERE bc.book_id = b.book_id)
                 ORDER BY b.title
                """
            )
            if deletable_books.empty:
                st.info("There are currently no books eligible for deletion. Remove copies only when it is safe and there are no loan records.")
            else:
                delete_labels = {
                    f'{row["TITLE"]} (ID: {int(row["BOOK_ID"])})': int(row["BOOK_ID"])
                    for _, row in deletable_books.iterrows()
                }
                delete_label = st.selectbox("Select a book to delete", list(delete_labels.keys()), key="delete_book_select")
                confirm_delete_book = st.checkbox("I understand this permanently deletes the selected book.", key="confirm_delete_book")
                if st.button("Delete Book", type="primary", disabled=not confirm_delete_book):
                    delete_book_id = delete_labels[delete_label]

                    def delete_book(cursor):
                        cursor.execute(
                            "DELETE FROM book_authors WHERE book_id = :book_id",
                            {"book_id": delete_book_id},
                        )
                        cursor.execute(
                            "DELETE FROM books WHERE book_id = :book_id",
                            {"book_id": delete_book_id},
                        )

                    execute_transaction(delete_book)
                    st.success("Book deleted.")
                    st.rerun()
        except Exception as error:
            show_db_error(error, "Deleting book")

    with book_subtabs[4]:
        st.markdown("#### Manage Physical Copies")
        copy_left, copy_right = st.columns(2)
        with copy_left:
            st.markdown("##### Add Copies")
            try:
                all_books = fetch_all("SELECT book_id, title FROM books ORDER BY title")
                if all_books.empty:
                    st.info("Add a book first.")
                else:
                    copy_book_labels = {
                        f'{row["TITLE"]} (ID: {int(row["BOOK_ID"])})': int(row["BOOK_ID"])
                        for _, row in all_books.iterrows()
                    }
                    with st.form("add_copies_form", clear_on_submit=True):
                        copy_book_label = st.selectbox("Book", list(copy_book_labels.keys()))
                        copies_to_add = st.number_input("Number of copies", min_value=1, max_value=100, value=1, step=1)
                        add_copies_clicked = st.form_submit_button("Add Copies", type="primary")
                    if add_copies_clicked:
                        def add_copies(cursor):
                            book_id = copy_book_labels[copy_book_label]
                            new_ids = []
                            for _ in range(int(copies_to_add)):
                                copy_id = next_sequence_value(cursor, "COPY_ID_SEQ")
                                cursor.execute(
                                    """
                                    INSERT INTO book_copies (copy_id, book_id, copy_status)
                                    VALUES (:copy_id, :book_id, 'AVAILABLE')
                                    """,
                                    {"copy_id": copy_id, "book_id": book_id},
                                )
                                new_ids.append(copy_id)
                            return new_ids

                        new_copy_ids = execute_transaction(add_copies)
                        st.success(f"Added {len(new_copy_ids)} copies. Copy IDs: {', '.join(map(str, new_copy_ids))}")
                        st.rerun()
            except Exception as error:
                show_db_error(error, "Adding copies")

        with copy_right:
            st.markdown("##### Update Copy Condition")
            st.caption("Use this only for AVAILABLE, DAMAGED, or LOST copies. Borrowed copies must be returned through the Return Book tab.")
            try:
                copies_df = fetch_all(
                    """
                    SELECT bc.copy_id, b.title, bc.copy_status,
                           CASE WHEN EXISTS (
                             SELECT 1 FROM book_loans bl
                              WHERE bl.copy_id = bc.copy_id
                                AND bl.loan_status IN ('BORROWED', 'OVERDUE')
                                AND bl.return_date IS NULL
                           ) THEN 'YES' ELSE 'NO' END AS has_active_loan
                      FROM book_copies bc
                      JOIN books b ON b.book_id = bc.book_id
                     ORDER BY b.title, bc.copy_id
                    """
                )
                if copies_df.empty:
                    st.info("No physical copies found.")
                else:
                    copy_labels = {
                        f'Copy {int(row["COPY_ID"])} · {row["TITLE"]} · {row["COPY_STATUS"]}': int(row["COPY_ID"])
                        for _, row in copies_df.iterrows()
                    }
                    chosen_copy_label = st.selectbox("Select a copy", list(copy_labels.keys()), key="copy_status_select")
                    chosen_copy_id = copy_labels[chosen_copy_label]
                    chosen_copy = copies_df[copies_df["COPY_ID"].astype(int) == chosen_copy_id].iloc[0]
                    if chosen_copy["HAS_ACTIVE_LOAN"] == "YES":
                        st.warning("This copy has an active loan. Return it before changing its condition.")
                    else:
                        status_choices = ["AVAILABLE", "DAMAGED", "LOST"]
                        current_status = str(chosen_copy["COPY_STATUS"])
                        default_status = current_status if current_status in status_choices else "AVAILABLE"
                        new_status = st.selectbox(
                            "New status", status_choices,
                            index=status_choices.index(default_status),
                            key=f"copy_status_value_{chosen_copy_id}"
                        )
                        if st.button("Update Copy Status", type="primary", key="update_copy_status"):
                            execute_transaction(
                                lambda cursor: cursor.execute(
                                    "UPDATE book_copies SET copy_status = :status WHERE copy_id = :copy_id",
                                    {"status": new_status, "copy_id": chosen_copy_id},
                                )
                            )
                            st.success("Copy status updated.")
                            st.rerun()
                st.markdown("##### All Copies")
                st.dataframe(copies_df, use_container_width=True, hide_index=True)
            except Exception as error:
                show_db_error(error, "Managing copies")


# ---------------------------------------------------------------------------
# 3. Members
# ---------------------------------------------------------------------------
with tabs[2]:
    member_subtabs = st.tabs(["Member Directory", "Register Member", "Edit Member", "Delete Member"])

    with member_subtabs[0]:
        st.markdown("#### Member Directory")
        try:
            members_df = load_members()
            member_search = st.text_input("Search members by name or email", key="member_search")
            if member_search.strip():
                member_mask = (
                    members_df["MEMBER_NAME"].astype(str).str.contains(member_search, case=False, na=False)
                    | members_df["EMAIL"].astype(str).str.contains(member_search, case=False, na=False)
                )
                members_df = members_df[member_mask]
            st.dataframe(members_df, use_container_width=True, hide_index=True)
        except Exception as error:
            show_db_error(error, "Loading members")

    with member_subtabs[1]:
        st.markdown("#### Register a Member")
        with st.form("register_member_form", clear_on_submit=True):
            member_name = st.text_input("Full name", max_chars=100)
            member_email = st.text_input("Email", max_chars=150)
            member_type = st.selectbox("Member type", ["STUDENT", "FACULTY"])
            register_clicked = st.form_submit_button("Register Member", type="primary")
        if register_clicked:
            if not member_name.strip() or not member_email.strip():
                st.warning("Name and email are required.")
            else:
                try:
                    def register_member(cursor):
                        member_id = next_sequence_value(cursor, "MEMBER_ID_SEQ")
                        cursor.execute(
                            """
                            INSERT INTO members (member_id, member_name, email, member_type)
                            VALUES (:member_id, :member_name, :email, :member_type)
                            """,
                            {
                                "member_id": member_id,
                                "member_name": member_name.strip(),
                                "email": member_email.strip(),
                                "member_type": member_type,
                            },
                        )
                        return member_id

                    new_member_id = execute_transaction(register_member)
                    st.success(f"Member registered. Member ID: {new_member_id}")
                    st.rerun()
                except Exception as error:
                    show_db_error(error, "Registering member")

    with member_subtabs[2]:
        st.markdown("#### Edit Member Details")
        try:
            member_df = load_members()
            if member_df.empty:
                st.info("No members to edit.")
            else:
                member_labels = {
                    f'{row["MEMBER_NAME"]} · {row["EMAIL"]} (ID: {int(row["MEMBER_ID"])})': int(row["MEMBER_ID"])
                    for _, row in member_df.iterrows()
                }
                selected_member_label = st.selectbox("Select member", list(member_labels.keys()), key="edit_member_select")
                selected_member_id = member_labels[selected_member_label]
                selected_member = fetch_one(
                    "SELECT member_name, email, member_type FROM members WHERE member_id = :member_id",
                    {"member_id": selected_member_id},
                )
                with st.form("edit_member_form"):
                    edit_member_name = st.text_input("Full name", value=selected_member[0], max_chars=100)
                    edit_member_email = st.text_input("Email", value=selected_member[1], max_chars=150)
                    edit_member_type = st.selectbox(
                        "Member type", ["STUDENT", "FACULTY"],
                        index=["STUDENT", "FACULTY"].index(selected_member[2]),
                    )
                    save_member_clicked = st.form_submit_button("Save Member Changes", type="primary")
                if save_member_clicked:
                    if not edit_member_name.strip() or not edit_member_email.strip():
                        st.warning("Name and email are required.")
                    else:
                        execute_transaction(
                            lambda cursor: cursor.execute(
                                """
                                UPDATE members
                                   SET member_name = :member_name, email = :email, member_type = :member_type
                                 WHERE member_id = :member_id
                                """,
                                {
                                    "member_name": edit_member_name.strip(),
                                    "email": edit_member_email.strip(),
                                    "member_type": edit_member_type,
                                    "member_id": selected_member_id,
                                },
                            )
                        )
                        st.success("Member details updated.")
                        st.rerun()
        except Exception as error:
            show_db_error(error, "Editing member")

    with member_subtabs[3]:
        st.markdown("#### Delete a Member")
        st.warning("Members with any loan history cannot be deleted, so historical records remain intact.")
        try:
            deletable_members = fetch_all(
                """
                SELECT m.member_id, m.member_name, m.email
                  FROM members m
                 WHERE NOT EXISTS (
                   SELECT 1 FROM book_loans bl WHERE bl.member_id = m.member_id
                 )
                 ORDER BY m.member_name
                """
            )
            if deletable_members.empty:
                st.info("No members without loan history are eligible for deletion.")
            else:
                delete_member_labels = {
                    f'{row["MEMBER_NAME"]} · {row["EMAIL"]} (ID: {int(row["MEMBER_ID"])})': int(row["MEMBER_ID"])
                    for _, row in deletable_members.iterrows()
                }
                selected_delete_member = st.selectbox(
                    "Select member to delete", list(delete_member_labels.keys()), key="delete_member_select"
                )
                confirm_delete_member = st.checkbox("I understand this permanently deletes the selected member.", key="confirm_delete_member")
                if st.button("Delete Member", type="primary", disabled=not confirm_delete_member):
                    execute_transaction(
                        lambda cursor: cursor.execute(
                            "DELETE FROM members WHERE member_id = :member_id",
                            {"member_id": delete_member_labels[selected_delete_member]},
                        )
                    )
                    st.success("Member deleted.")
                    st.rerun()
        except Exception as error:
            show_db_error(error, "Deleting member")


# ---------------------------------------------------------------------------
# 4. Borrow Book
# ---------------------------------------------------------------------------
with tabs[3]:
    st.subheader("Borrow a Book")
    st.write("Choose an available physical copy and a registered member. The BORROW_BOOK stored procedure updates the copy and creates the loan.")
    try:
        available_df = load_available_copies()
        members_df = load_members()
        if available_df.empty:
            st.info("There are no available copies to borrow.")
        elif members_df.empty:
            st.info("Register a member before creating a loan.")
        else:
            available_labels = {
                f'{row["TITLE"]} · Copy ID {int(row["COPY_ID"])}': int(row["COPY_ID"])
                for _, row in available_df.iterrows()
            }
            member_labels = {
                f'{row["MEMBER_NAME"]} · {row["MEMBER_TYPE"]} · ID {int(row["MEMBER_ID"])}': int(row["MEMBER_ID"])
                for _, row in members_df.iterrows()
            }
            with st.form("borrow_book_form"):
                chosen_available_label = st.selectbox("Available book copy", list(available_labels.keys()))
                chosen_member_label = st.selectbox("Member", list(member_labels.keys()))
                borrow_date = st.date_input("Loan date", value=date.today(), disabled=True)
                due_date = st.date_input("Due date", value=date.today() + timedelta(days=14), min_value=date.today())
                borrow_clicked = st.form_submit_button("Borrow Book", type="primary")
            if borrow_clicked:
                if due_date < date.today():
                    st.warning("The due date must not be in the past.")
                else:
                    def borrow_copy(cursor):
                        loan_id = next_sequence_value(cursor, "LOAN_ID_SEQ")
                        cursor.execute(
                            """
                            BEGIN
                                BORROW_BOOK(
                                    p_loan_id => :loan_id,
                                    p_copy_id => :copy_id,
                                    p_member_id => :member_id,
                                    p_due_date => :due_date
                                );
                            END;
                            """,
                            {
                                "loan_id": loan_id,
                                "copy_id": available_labels[chosen_available_label],
                                "member_id": member_labels[chosen_member_label],
                                "due_date": due_date,
                            },
                        )
                        return loan_id

                    try:
                        new_loan_id = execute_transaction(borrow_copy)
                        st.success(f"Book borrowed successfully. Loan ID: {new_loan_id}")
                        st.rerun()
                    except Exception as error:
                        show_db_error(error, "Borrowing book")
    except Exception as error:
        show_db_error(error, "Loading borrow form")


# ---------------------------------------------------------------------------
# 5. Return Book
# ---------------------------------------------------------------------------
with tabs[4]:
    st.subheader("Return a Book")
    st.write("Select an active loan. The RETURN_BOOK stored procedure records the return and makes the physical copy available again.")
    try:
        active_df = load_active_loans()
        if active_df.empty:
            st.info("There are no active loans to return.")
        else:
            active_labels = {
                f'Loan {int(row["LOAN_ID"])} · {row["TITLE"]} · Copy {int(row["COPY_ID"])} · {row["MEMBER_NAME"]} · Due {pd.to_datetime(row["DUE_DATE"]).date()}': int(row["LOAN_ID"])
                for _, row in active_df.iterrows()
            }
            selected_active_label = st.selectbox("Active loan", list(active_labels.keys()))
            selected_active_loan_id = active_labels[selected_active_label]
            if st.button("Confirm Return", type="primary"):
                def return_copy(cursor):
                    cursor.execute(
                        """
                        BEGIN
                            RETURN_BOOK(p_loan_id => :loan_id);
                        END;
                        """,
                        {"loan_id": selected_active_loan_id},
                    )
                try:
                    execute_transaction(return_copy)
                    st.success(f"Loan {selected_active_loan_id} returned successfully.")
                    st.rerun()
                except Exception as error:
                    show_db_error(error, "Returning book")
        st.markdown("#### Active Loans")
        st.dataframe(active_df, use_container_width=True, hide_index=True)
    except Exception as error:
        show_db_error(error, "Loading active loans")


# ---------------------------------------------------------------------------
# 6. Loan History
# ---------------------------------------------------------------------------
with tabs[5]:
    st.subheader("Loan History")
    try:
        history_df = load_loan_history()
        filter_col1, filter_col2 = st.columns(2)
        with filter_col1:
            status_filter = st.multiselect(
                "Filter by loan status",
                options=["BORROWED", "OVERDUE", "RETURNED"],
                default=["BORROWED", "OVERDUE", "RETURNED"],
            )
        with filter_col2:
            history_search = st.text_input("Search by book, member, or loan ID", key="history_search")

        filtered_history = history_df[history_df["LOAN_STATUS"].isin(status_filter)]
        if history_search.strip():
            search_mask = (
                filtered_history["TITLE"].astype(str).str.contains(history_search, case=False, na=False)
                | filtered_history["MEMBER_NAME"].astype(str).str.contains(history_search, case=False, na=False)
                | filtered_history["LOAN_ID"].astype(str).str.contains(history_search, case=False, na=False)
            )
            filtered_history = filtered_history[search_mask]
        st.dataframe(filtered_history, use_container_width=True, hide_index=True)
        st.caption(f"Showing {len(filtered_history)} of {len(history_df)} loan records.")
        csv_data = filtered_history.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download filtered loan history as CSV",
            data=csv_data,
            file_name="library_loan_history.csv",
            mime="text/csv",
        )
    except Exception as error:
        show_db_error(error, "Loading loan history")


# ---------------------------------------------------------------------------
# 7. Audit Log
# ---------------------------------------------------------------------------
with tabs[6]:
    st.subheader("Loan Status Audit Log")
    st.write("This log is populated by the TRG_LOAN_STATUS_AUDIT trigger when a loan's status changes.")
    try:
        audit_df = fetch_all(
            """
            SELECT audit_id, loan_id, old_status, new_status, changed_at
              FROM loan_audit
             ORDER BY changed_at DESC, audit_id DESC
            """
        )
        if audit_df.empty:
            st.info("No loan status changes have been recorded yet.")
        else:
            audit_col1, audit_col2 = st.columns(2)
            with audit_col1:
                audit_search = st.text_input("Search by loan or audit ID", key="audit_search")
            with audit_col2:
                audit_statuses = st.multiselect(
                    "Filter by new status",
                    options=sorted(audit_df["NEW_STATUS"].dropna().astype(str).unique().tolist()),
                    default=sorted(audit_df["NEW_STATUS"].dropna().astype(str).unique().tolist()),
                )
            filtered_audit = audit_df[audit_df["NEW_STATUS"].isin(audit_statuses)]
            if audit_search.strip():
                audit_mask = (
                    filtered_audit["LOAN_ID"].astype(str).str.contains(audit_search, case=False, na=False)
                    | filtered_audit["AUDIT_ID"].astype(str).str.contains(audit_search, case=False, na=False)
                )
                filtered_audit = filtered_audit[audit_mask]
            st.dataframe(filtered_audit, use_container_width=True, hide_index=True)
            st.caption(f"Showing {len(filtered_audit)} of {len(audit_df)} audit records.")
            st.download_button(
                "Download audit log as CSV",
                data=filtered_audit.to_csv(index=False).encode("utf-8"),
                file_name="library_audit_log.csv",
                mime="text/csv",
            )
    except Exception as error:
        st.error("Could not load LOAN_AUDIT. Confirm the table, sequence, and trigger exist in CAMPUS_DB.")
        st.exception(error)
