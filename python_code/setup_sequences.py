import os
import oracledb

ORACLE_CLIENT_DIR = r"C:\oracle\instantclient_23_26"
DB_USER = "CAMPUS_DB"
DB_DSN = "localhost:1521/XE"

SEQUENCES = {
    "BOOK_ID_SEQ": ("BOOKS", "BOOK_ID"),
    "COPY_ID_SEQ": ("BOOK_COPIES", "COPY_ID"),
    "MEMBER_ID_SEQ": ("MEMBERS", "MEMBER_ID"),
    "LOAN_ID_SEQ": ("BOOK_LOANS", "LOAN_ID"),
}


def main():
    password = os.environ.get("ORACLE_PASSWORD")
    if not password:
        raise SystemExit(
            "ORACLE_PASSWORD is not set. In PowerShell, run: "
            "$env:ORACLE_PASSWORD='your_actual_database_password'"
        )

    oracledb.init_oracle_client(lib_dir=ORACLE_CLIENT_DIR)

    with oracledb.connect(user=DB_USER, password=password, dsn=DB_DSN) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT sequence_name FROM user_sequences")
            existing = {row[0].upper() for row in cursor.fetchall()}

            for sequence_name, (table_name, id_column) in SEQUENCES.items():
                if sequence_name in existing:
                    print(f"Already exists: {sequence_name} (leaving unchanged)")
                    continue

                cursor.execute(
                    f"SELECT NVL(MAX({id_column}), 0) + 1 FROM {table_name}"
                )
                start_value = int(cursor.fetchone()[0])
                cursor.execute(
                    f"CREATE SEQUENCE {sequence_name} "
                    f"START WITH {start_value} INCREMENT BY 1 NOCACHE"
                )
                print(f"Created {sequence_name}, starting at {start_value}")

    print("Sequence setup completed. Existing LOAN_AUDIT_SEQ was not changed.")


if __name__ == "__main__":
    main()
