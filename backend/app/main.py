import os
import re
import shutil
import uuid

import requests
from fastapi import (
    FastAPI,
    File,
    Form,
    HTTPException,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.database import (
    create_table,
    create_upload,
    delete_upload,
    get_all_content,
    get_all_uploads,
    get_upload,
    insert_upload_content,
    migrate_existing_content_to_uploads,
)
from app.parser import parse_workbook
from app.search import search_content


app = FastAPI(
    title="CourseIQ API",
    version="3.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://172.31.99.87:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


PROJECT_DIR = os.path.dirname(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)

UPLOAD_FOLDER = os.path.join(
    PROJECT_DIR,
    "uploads",
)


def safe_slug(value: str) -> str:
    slug = re.sub(
        r"[^a-zA-Z0-9_-]+",
        "_",
        value.strip(),
    )

    return slug.strip("_") or "course"


def safe_upload_path(filename: str) -> str:
    safe_filename = os.path.basename(
        filename.strip()
    )

    if not safe_filename:
        raise ValueError(
            "Invalid source filename."
        )

    upload_root = os.path.abspath(
        UPLOAD_FOLDER
    )

    file_path = os.path.abspath(
        os.path.join(
            upload_root,
            safe_filename,
        )
    )

    if os.path.commonpath(
        [upload_root, file_path]
    ) != upload_root:
        raise ValueError(
            "Invalid source filename."
        )

    return file_path


def build_stored_filename(
    course_name: str,
    original_filename: str,
    source_kind: str,
) -> str:
    course_slug = safe_slug(
        course_name
    )

    unique_suffix = uuid.uuid4().hex[:10]

    if source_kind == "excel":
        safe_original_name = os.path.basename(
            original_filename
        )

        file_stem, extension = os.path.splitext(
            safe_original_name
        )

        safe_file_stem = safe_slug(
            file_stem
        )

        extension = (
            extension.lower()
            if extension
            else ".xlsx"
        )

        return (
            f"{course_slug}_"
            f"{safe_file_stem}_"
            f"{unique_suffix}"
            f"{extension}"
        )

    return (
        f"{course_slug}_"
        f"google_sheet_"
        f"{unique_suffix}.xlsx"
    )


def extract_google_sheet_id(
    url: str,
) -> str:
    patterns = [
        r"/spreadsheets/d/([a-zA-Z0-9-_]+)",
        r"[?&]id=([a-zA-Z0-9-_]+)",
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            url,
        )

        if match:
            return match.group(1)

    raise ValueError(
        "Invalid Google Sheets URL."
    )


def download_google_workbook(
    google_sheet_url: str,
    destination_path: str,
) -> None:
    sheet_id = extract_google_sheet_id(
        google_sheet_url
    )

    export_url = (
        "https://docs.google.com/spreadsheets/d/"
        f"{sheet_id}/export?format=xlsx"
    )

    try:
        response = requests.get(
            export_url,
            timeout=60,
            allow_redirects=True,
        )

        response.raise_for_status()

    except requests.RequestException as error:
        raise ValueError(
            "Could not download the Google Sheet. "
            "Ensure that anyone with the link can view it."
        ) from error

    content_type = response.headers.get(
        "content-type",
        "",
    ).lower()

    if (
        "text/html" in content_type
        or len(response.content) < 1000
    ):
        raise ValueError(
            "Google Sheet access failed. "
            "Set sharing to anyone with the link can view."
        )

    with open(
        destination_path,
        "wb",
    ) as output_file:
        output_file.write(
            response.content
        )


def remove_file_if_present(
    file_path: str,
) -> bool:
    if not os.path.isfile(
        file_path
    ):
        return False

    try:
        os.remove(
            file_path
        )
        return True

    except OSError:
        return False


@app.on_event("startup")
def startup() -> None:
    os.makedirs(
        UPLOAD_FOLDER,
        exist_ok=True,
    )

    create_table()

    migrate_existing_content_to_uploads()


@app.get("/")
def home():
    return {
        "message": "CourseIQ Backend Running",
        "version": "3.0.0",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
    }


@app.get("/content")
def content():
    return [
        dict(row)
        for row in get_all_content()
    ]


@app.get("/uploads")
def uploads():
    return [
        dict(row)
        for row in get_all_uploads()
    ]


@app.get("/uploads/{upload_id}")
def upload_details(
    upload_id: int,
):
    upload = get_upload(
        upload_id
    )

    if upload is None:
        raise HTTPException(
            status_code=404,
            detail="Upload not found.",
        )

    return dict(upload)


@app.get("/search")
def search(
    query: str = "",
    type: str = "All",
    limit: int = 100,
):
    search_data = search_content(
        query=query,
        content_type=type,
        limit=min(
            max(limit, 1),
            500,
        ),
    )

    return {
        "query": query,
        "corrected_query": search_data[
            "corrected_query"
        ],
        "query_was_corrected": search_data[
            "query_was_corrected"
        ],
        "type": type,
        "count": len(
            search_data["results"]
        ),
        "results": search_data[
            "results"
        ],
    }


@app.post("/upload")
def upload(
    course_name: str = Form(...),
    google_sheet: str = Form(""),
    file: UploadFile | None = File(None),
):
    course_name = course_name.strip()
    google_sheet = google_sheet.strip()

    if not course_name:
        raise HTTPException(
            status_code=400,
            detail="Course name is required.",
        )

    has_excel_file = bool(
        file
        and file.filename
    )

    has_google_sheet = bool(
        google_sheet
    )

    if (
        not has_excel_file
        and not has_google_sheet
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Provide either an Excel file "
                "or a Google Sheets link."
            ),
        )

    if (
        has_excel_file
        and has_google_sheet
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Provide only one source: "
                "an Excel file or a Google Sheets link."
            ),
        )

    source_kind = (
        "excel"
        if has_excel_file
        else "google_sheet"
    )

    original_filename = (
        os.path.basename(
            file.filename or "course.xlsx"
        )
        if has_excel_file
        else ""
    )

    if (
        has_excel_file
        and not original_filename.lower().endswith(
            ".xlsx"
        )
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Only .xlsx files are supported."
            ),
        )

    stored_filename = build_stored_filename(
        course_name=course_name,
        original_filename=(
            original_filename
            or "google_sheet.xlsx"
        ),
        source_kind=source_kind,
    )

    file_path = safe_upload_path(
        stored_filename
    )

    upload_id: int | None = None
    database_record_created = False
    content_inserted = False

    try:
        if has_excel_file and file:
            with open(
                file_path,
                "wb",
            ) as buffer:
                shutil.copyfileobj(
                    file.file,
                    buffer,
                )

        else:
            download_google_workbook(
                google_sheet_url=google_sheet,
                destination_path=file_path,
            )

        records = parse_workbook(
            file_path=file_path,
            course_name=course_name,
            source_file=stored_filename,
            google_sheet=google_sheet,
        )

        if not records:
            remove_file_if_present(
                file_path
            )

            raise HTTPException(
                status_code=400,
                detail=(
                    "No valid course content was found. "
                    "Check the sheet structure and artifact names."
                ),
            )

        upload_id = create_upload(
            course_name=course_name,
            source_kind=source_kind,
            source_file=stored_filename,
            original_filename=original_filename,
            google_sheet=google_sheet,
        )

        database_record_created = True

        inserted_rows = insert_upload_content(
            upload_id=upload_id,
            records=records,
        )

        content_inserted = True

        sheet_names = sorted(
            {
                str(
                    record.get(
                        "sheet_name",
                        "",
                    )
                ).strip()
                for record in records
                if str(
                    record.get(
                        "sheet_name",
                        "",
                    )
                ).strip()
            }
        )

        return {
            "message": (
                "Course imported successfully."
            ),
            "upload_id": upload_id,
            "course": course_name,
            "source_kind": source_kind,
            "rows_imported": inserted_rows,
            "sheets_imported": len(
                sheet_names
            ),
            "sheet_names": sheet_names,
            "source_file": stored_filename,
            "original_filename": original_filename,
            "google_sheet": google_sheet,
        }

    except HTTPException:
        if (
            database_record_created
            and not content_inserted
            and upload_id is not None
        ):
            delete_upload(
                upload_id
            )

        if not content_inserted:
            remove_file_if_present(
                file_path
            )

        raise

    except ValueError as error:
        if (
            database_record_created
            and upload_id is not None
        ):
            delete_upload(
                upload_id
            )

        remove_file_if_present(
            file_path
        )

        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    except Exception as error:
        if (
            database_record_created
            and upload_id is not None
        ):
            delete_upload(
                upload_id
            )

        remove_file_if_present(
            file_path
        )

        raise HTTPException(
            status_code=500,
            detail=(
                f"Import failed: {str(error)}"
            ),
        ) from error

    finally:
        if file:
            file.file.close()


@app.get("/download/{filename}")
def download_file(
    filename: str,
):
    try:
        file_path = safe_upload_path(
            filename
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    safe_filename = os.path.basename(
        file_path
    )

    if not os.path.isfile(
        file_path
    ):
        raise HTTPException(
            status_code=404,
            detail=(
                "Source workbook not found."
            ),
        )

    return FileResponse(
        path=file_path,
        filename=safe_filename,
        media_type=(
            "application/vnd.openxmlformats-"
            "officedocument.spreadsheetml.sheet"
        ),
    )


@app.delete("/uploads/{upload_id}")
def remove_upload(
    upload_id: int,
):
    upload = get_upload(
        upload_id
    )

    if upload is None:
        raise HTTPException(
            status_code=404,
            detail="Upload not found.",
        )

    upload_data = dict(
        upload
    )

    source_file = str(
        upload_data.get(
            "source_file",
            "",
        )
    ).strip()

    try:
        deleted_upload = delete_upload(
            upload_id
        )

        if deleted_upload is None:
            raise HTTPException(
                status_code=404,
                detail="Upload not found.",
            )

        file_deleted = False

        if source_file:
            try:
                file_path = safe_upload_path(
                    source_file
                )

                file_deleted = (
                    remove_file_if_present(
                        file_path
                    )
                )

            except ValueError:
                file_deleted = False

        return {
            "message": (
                "Upload and all related course content "
                "deleted successfully."
            ),
            "upload_id": upload_id,
            "course": deleted_upload[
                "course_name"
            ],
            "source_file": source_file,
            "database_rows_deleted": (
                deleted_upload[
                    "deleted_content_rows"
                ]
            ),
            "file_deleted": file_deleted,
        }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=(
                "Upload deletion failed: "
                f"{str(error)}"
            ),
        ) from error


@app.delete("/upload/{upload_id}")
def remove_upload_legacy(
    upload_id: int,
):
    return remove_upload(
        upload_id
    )