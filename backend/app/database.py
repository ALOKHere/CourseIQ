import os
import sqlite3
from typing import Any


BACKEND_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

DB_NAME = os.path.join(
    BACKEND_DIR,
    "courseiq.db",
)


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(
        DB_NAME,
        timeout=30,
    )

    connection.row_factory = sqlite3.Row

    connection.execute(
        "PRAGMA foreign_keys = ON"
    )

    return connection


def create_table() -> None:
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS uploads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_name TEXT NOT NULL,
                source_kind TEXT NOT NULL,
                source_file TEXT NOT NULL UNIQUE,
                original_filename TEXT,
                google_sheet TEXT,
                uploaded_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS content (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                upload_id INTEGER,
                course TEXT NOT NULL,
                sheet_name TEXT,
                module TEXT,
                lesson TEXT,
                type TEXT NOT NULL,
                title TEXT NOT NULL,
                source_file TEXT,
                google_sheet TEXT,
                FOREIGN KEY (upload_id)
                    REFERENCES uploads(id)
                    ON DELETE CASCADE
            )
            """
        )

        cursor.execute(
            "PRAGMA table_info(content)"
        )

        content_columns = {
            row["name"]
            for row in cursor.fetchall()
        }

        required_content_columns = {
            "upload_id": "INTEGER",
            "sheet_name": "TEXT",
            "module": "TEXT",
            "lesson": "TEXT",
            "source_file": "TEXT",
            "google_sheet": "TEXT",
        }

        for column_name, column_type in (
            required_content_columns.items()
        ):
            if column_name not in content_columns:
                cursor.execute(
                    f"""
                    ALTER TABLE content
                    ADD COLUMN {column_name} {column_type}
                    """
                )

        cursor.execute(
            "PRAGMA table_info(content)"
        )

        updated_content_columns = {
            row["name"]
            for row in cursor.fetchall()
        }

        if "source_link" in updated_content_columns:
            cursor.execute(
                """
                UPDATE content
                SET source_file = source_link
                WHERE (
                    source_file IS NULL
                    OR TRIM(source_file) = ''
                )
                AND source_link IS NOT NULL
                AND TRIM(source_link) <> ''
                """
            )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_content_upload_id
            ON content(upload_id)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_content_course
            ON content(course)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_content_source_file
            ON content(source_file)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_content_type
            ON content(type)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_uploads_course_name
            ON uploads(course_name)
            """
        )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def create_upload(
    course_name: str,
    source_kind: str,
    source_file: str,
    original_filename: str = "",
    google_sheet: str = "",
) -> int:
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO uploads (
                course_name,
                source_kind,
                source_file,
                original_filename,
                google_sheet
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                course_name.strip(),
                source_kind.strip(),
                source_file.strip(),
                original_filename.strip(),
                google_sheet.strip(),
            ),
        )

        upload_id = cursor.lastrowid

        connection.commit()

        if upload_id is None:
            raise RuntimeError(
                "Could not create upload record."
            )

        return int(upload_id)

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def get_upload(upload_id: int):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT
                id,
                course_name,
                source_kind,
                source_file,
                original_filename,
                google_sheet,
                uploaded_at
            FROM uploads
            WHERE id = ?
            """,
            (upload_id,),
        )

        return cursor.fetchone()

    finally:
        connection.close()


def get_upload_by_source_file(
    source_file: str,
):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT
                id,
                course_name,
                source_kind,
                source_file,
                original_filename,
                google_sheet,
                uploaded_at
            FROM uploads
            WHERE LOWER(source_file) = LOWER(?)
            LIMIT 1
            """,
            (source_file.strip(),),
        )

        return cursor.fetchone()

    finally:
        connection.close()


def get_all_uploads():
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT
                uploads.id,
                uploads.course_name,
                uploads.source_kind,
                uploads.source_file,
                uploads.original_filename,
                uploads.google_sheet,
                uploads.uploaded_at,
                COUNT(content.id) AS content_count
            FROM uploads
            LEFT JOIN content
                ON content.upload_id = uploads.id
            GROUP BY
                uploads.id,
                uploads.course_name,
                uploads.source_kind,
                uploads.source_file,
                uploads.original_filename,
                uploads.google_sheet,
                uploads.uploaded_at
            ORDER BY
                uploads.uploaded_at DESC,
                uploads.id DESC
            """
        )

        return cursor.fetchall()

    finally:
        connection.close()


def upload_exists(upload_id: int) -> bool:
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT 1
            FROM uploads
            WHERE id = ?
            LIMIT 1
            """,
            (upload_id,),
        )

        return cursor.fetchone() is not None

    finally:
        connection.close()


def source_file_exists(
    source_file: str,
) -> bool:
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT 1
            FROM uploads
            WHERE LOWER(source_file) = LOWER(?)
            LIMIT 1
            """,
            (source_file.strip(),),
        )

        return cursor.fetchone() is not None

    finally:
        connection.close()


def insert_upload_content(
    upload_id: int,
    records: list[dict[str, Any]],
) -> int:
    if not records:
        return 0

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT 1
            FROM uploads
            WHERE id = ?
            LIMIT 1
            """,
            (upload_id,),
        )

        if cursor.fetchone() is None:
            raise ValueError(
                f"Upload with ID {upload_id} does not exist."
            )

        cursor.executemany(
            """
            INSERT INTO content (
                upload_id,
                course,
                sheet_name,
                module,
                lesson,
                type,
                title,
                source_file,
                google_sheet
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    upload_id,
                    str(
                        record.get(
                            "course",
                            "",
                        )
                    ).strip(),
                    str(
                        record.get(
                            "sheet_name",
                            "",
                        )
                    ).strip(),
                    str(
                        record.get(
                            "module",
                            "",
                        )
                    ).strip(),
                    str(
                        record.get(
                            "lesson",
                            "",
                        )
                    ).strip(),
                    str(
                        record.get(
                            "type",
                            "",
                        )
                    ).strip(),
                    str(
                        record.get(
                            "title",
                            "",
                        )
                    ).strip(),
                    str(
                        record.get(
                            "source_file",
                            "",
                        )
                    ).strip(),
                    str(
                        record.get(
                            "google_sheet",
                            "",
                        )
                    ).strip(),
                )
                for record in records
            ],
        )

        inserted_rows = cursor.rowcount

        connection.commit()

        return max(
            inserted_rows,
            len(records),
        )

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def replace_upload_content(
    upload_id: int,
    records: list[dict[str, Any]],
) -> int:
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT 1
            FROM uploads
            WHERE id = ?
            LIMIT 1
            """,
            (upload_id,),
        )

        if cursor.fetchone() is None:
            raise ValueError(
                f"Upload with ID {upload_id} does not exist."
            )

        cursor.execute(
            """
            DELETE FROM content
            WHERE upload_id = ?
            """,
            (upload_id,),
        )

        if records:
            cursor.executemany(
                """
                INSERT INTO content (
                    upload_id,
                    course,
                    sheet_name,
                    module,
                    lesson,
                    type,
                    title,
                    source_file,
                    google_sheet
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        upload_id,
                        str(
                            record.get(
                                "course",
                                "",
                            )
                        ).strip(),
                        str(
                            record.get(
                                "sheet_name",
                                "",
                            )
                        ).strip(),
                        str(
                            record.get(
                                "module",
                                "",
                            )
                        ).strip(),
                        str(
                            record.get(
                                "lesson",
                                "",
                            )
                        ).strip(),
                        str(
                            record.get(
                                "type",
                                "",
                            )
                        ).strip(),
                        str(
                            record.get(
                                "title",
                                "",
                            )
                        ).strip(),
                        str(
                            record.get(
                                "source_file",
                                "",
                            )
                        ).strip(),
                        str(
                            record.get(
                                "google_sheet",
                                "",
                            )
                        ).strip(),
                    )
                    for record in records
                ],
            )

        connection.commit()

        return len(records)

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def delete_upload(
    upload_id: int,
) -> dict[str, Any] | None:
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT
                id,
                course_name,
                source_kind,
                source_file,
                original_filename,
                google_sheet,
                uploaded_at
            FROM uploads
            WHERE id = ?
            """,
            (upload_id,),
        )

        upload = cursor.fetchone()

        if upload is None:
            return None

        upload_data = dict(upload)

        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM content
            WHERE upload_id = ?
            """,
            (upload_id,),
        )

        count_row = cursor.fetchone()

        deleted_content_rows = (
            int(count_row["total"])
            if count_row is not None
            else 0
        )

        cursor.execute(
            """
            DELETE FROM uploads
            WHERE id = ?
            """,
            (upload_id,),
        )

        connection.commit()

        upload_data[
            "deleted_content_rows"
        ] = deleted_content_rows

        return upload_data

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def delete_upload_by_source_file(
    source_file: str,
) -> dict[str, Any] | None:
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT
                id,
                course_name,
                source_kind,
                source_file,
                original_filename,
                google_sheet,
                uploaded_at
            FROM uploads
            WHERE LOWER(source_file) = LOWER(?)
            LIMIT 1
            """,
            (source_file.strip(),),
        )

        upload = cursor.fetchone()

        if upload is None:
            return None

        upload_id = int(upload["id"])
        upload_data = dict(upload)

        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM content
            WHERE upload_id = ?
            """,
            (upload_id,),
        )

        count_row = cursor.fetchone()

        deleted_content_rows = (
            int(count_row["total"])
            if count_row is not None
            else 0
        )

        cursor.execute(
            """
            DELETE FROM uploads
            WHERE id = ?
            """,
            (upload_id,),
        )

        connection.commit()

        upload_data[
            "deleted_content_rows"
        ] = deleted_content_rows

        return upload_data

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def get_all_content():
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT
                content.id,
                content.upload_id,
                content.course,
                content.sheet_name,
                content.module,
                content.lesson,
                content.type,
                content.title,
                content.source_file,
                content.google_sheet,
                uploads.uploaded_at
            FROM content
            LEFT JOIN uploads
                ON uploads.id = content.upload_id
            ORDER BY
                content.course,
                content.module,
                content.lesson,
                content.sheet_name,
                content.title
            """
        )

        return cursor.fetchall()

    finally:
        connection.close()


def get_searchable_content():
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT
                content.id,
                content.upload_id,
                content.course,
                content.sheet_name,
                content.module,
                content.lesson,
                content.type,
                content.title,
                content.source_file,
                content.google_sheet
            FROM content
            """
        )

        return cursor.fetchall()

    finally:
        connection.close()


def get_content_by_upload(
    upload_id: int,
):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT
                id,
                upload_id,
                course,
                sheet_name,
                module,
                lesson,
                type,
                title,
                source_file,
                google_sheet
            FROM content
            WHERE upload_id = ?
            ORDER BY
                module,
                lesson,
                sheet_name,
                title
            """,
            (upload_id,),
        )

        return cursor.fetchall()

    finally:
        connection.close()


def migrate_existing_content_to_uploads() -> int:
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT DISTINCT
                course,
                source_file,
                google_sheet
            FROM content
            WHERE upload_id IS NULL
            AND source_file IS NOT NULL
            AND TRIM(source_file) <> ''
            """
        )

        existing_sources = cursor.fetchall()
        migrated_rows = 0

        for source in existing_sources:
            course_name = (
                source["course"] or "Imported Course"
            ).strip()

            source_file = (
                source["source_file"] or ""
            ).strip()

            google_sheet = (
                source["google_sheet"] or ""
            ).strip()

            if not source_file:
                continue

            source_kind = (
                "google_sheet"
                if google_sheet
                else "excel"
            )

            cursor.execute(
                """
                SELECT id
                FROM uploads
                WHERE LOWER(source_file) = LOWER(?)
                LIMIT 1
                """,
                (source_file,),
            )

            upload = cursor.fetchone()

            if upload is None:
                cursor.execute(
                    """
                    INSERT INTO uploads (
                        course_name,
                        source_kind,
                        source_file,
                        original_filename,
                        google_sheet
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        course_name,
                        source_kind,
                        source_file,
                        source_file,
                        google_sheet,
                    ),
                )

                upload_id = cursor.lastrowid

            else:
                upload_id = upload["id"]

            cursor.execute(
                """
                UPDATE content
                SET upload_id = ?
                WHERE upload_id IS NULL
                AND LOWER(source_file) = LOWER(?)
                """,
                (
                    upload_id,
                    source_file,
                ),
            )

            migrated_rows += cursor.rowcount

        connection.commit()

        return migrated_rows

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()