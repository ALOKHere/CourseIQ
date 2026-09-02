from __future__ import annotations

import re
from typing import Any, Iterable

import pandas as pd


TYPE_ALIASES = {
    "presentation video": "Video",
    "video": "Video",
    "lecture": "Video",

    "reading": "Reading",
    "article": "Reading",

    "demonstration video": "Demo",
    "demonstration": "Demo",
    "demo": "Demo",
    "lab": "Demo",

    "ungraded assignment": "Assignment",
    "graded assignment": "Assignment",
    "practice assignment": "Assignment",
    "practice project": "Assignment",
    "knowledge check": "Assignment",
    "practice quiz": "Assignment",
    "graded quiz": "Assignment",
    "discussion prompt": "Assignment",
    "peer review": "Assignment",
    "assignment": "Assignment",
    "quiz": "Assignment",
    "project": "Assignment",
}


TYPE_HEADERS = {
    "artifact",
    "artifact type",
    "type",
    "content type",
    "activity type",
    "item type",
    "step",
}


TITLE_HEADERS = {
    "artifact title",
    "video name",
    "title",
    "content title",
    "activity name",
    "item name",
    "item / video name",
    "item/video name",
    "resource title",
    "topic title",
}


TOPIC_HEADERS = {
    "topic",
    "topics",
    "content",
    "contents",
    "course content",
    "learning content",
    "concept",
    "concepts",
    "subject",
    "subjects",
}


HANDS_ON_HEADERS = {
    "hands-on",
    "hands on",
    "hands-on activity",
    "hands on activity",
    "hands-on activities",
    "hands on activities",
    "practical",
    "practical activity",
    "practical activities",
    "exercise",
    "exercises",
    "lab",
    "labs",
    "demo",
    "demonstration",
}


COURSE_HEADERS = {
    "course",
    "course name",
}


MODULE_HEADERS = {
    "module",
    "module name",
}


LESSON_HEADERS = {
    "lesson",
    "lesson name",
}


HEADER_SEARCH_LIMIT = 15


TITLE_PREFIXES = (
    "presentation video:",
    "demonstration video:",
    "ungraded assignment:",
    "graded assignment:",
    "practice assignment:",
    "practice project:",
    "practice quiz:",
    "graded quiz:",
    "knowledge check:",
    "discussion prompt:",
    "peer review:",
    "demonstration:",
    "assignment:",
    "reading:",
    "article:",
    "video:",
    "demo:",
    "quiz:",
    "project:",
    "lecture:",
)


def clean_cell(value: Any) -> str:
    if value is None:
        return ""

    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass

    text = str(value).strip()

    if text.lower() in {
        "nan",
        "none",
        "nat",
    }:
        return ""

    return re.sub(
        r"\s+",
        " ",
        text,
    ).strip()


def normalize_header(value: Any) -> str:
    text = clean_cell(value).lower()

    text = text.replace(
        "_",
        " ",
    )

    text = re.sub(
        r"\s*/\s*",
        " / ",
        text,
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def clean_title(value: Any) -> str:
    title = clean_cell(value)

    if not title:
        return ""

    changed = True

    while changed:
        changed = False
        lowered = title.lower()

        for prefix in TITLE_PREFIXES:
            if lowered.startswith(
                prefix.lower()
            ):
                title = title[
                    len(prefix):
                ].strip()

                changed = True
                break

    return title


def normalize_artifact_type(
    value: Any,
) -> str | None:
    artifact_type = clean_cell(
        value
    ).lower()

    if not artifact_type:
        return None

    artifact_type = re.sub(
        r"\s+",
        " ",
        artifact_type,
    ).strip()

    artifact_type = artifact_type.rstrip(
        ":"
    ).strip()

    for alias, normalized in (
        TYPE_ALIASES.items()
    ):
        if artifact_type.startswith(
            alias
        ):
            return normalized

    return None


def starts_with_context(
    text: str,
    context_name: str,
) -> bool:
    normalized = clean_cell(
        text
    ).lower()

    if not normalized:
        return False

    pattern = (
        rf"^{re.escape(context_name.lower())}"
        r"(?:\s|\d|:|\.|-)"
    )

    return bool(
        re.match(
            pattern,
            normalized,
        )
    )


def detect_context_type(
    value: Any,
) -> str | None:
    text = clean_cell(value)

    if not text:
        return None

    if starts_with_context(
        text,
        "course",
    ):
        return "course"

    if starts_with_context(
        text,
        "module",
    ):
        return "module"

    if starts_with_context(
        text,
        "lesson",
    ):
        return "lesson"

    if starts_with_context(
        text,
        "week",
    ):
        return "module"

    if starts_with_context(
        text,
        "activity",
    ):
        return "lesson"

    return None


def find_exact_column(
    headers: Iterable[Any],
    possible_names: set[str],
) -> int | None:
    for index, value in enumerate(
        headers
    ):
        if normalize_header(
            value
        ) in possible_names:
            return index

    return None


def find_contains_column(
    headers: Iterable[Any],
    possible_names: set[str],
) -> int | None:
    normalized_headers = [
        normalize_header(value)
        for value in headers
    ]

    for index, header in enumerate(
        normalized_headers
    ):
        if not header:
            continue

        for possible_name in possible_names:
            if (
                header == possible_name
                or possible_name in header
            ):
                return index

    return None


def looks_like_header_row(
    row: Iterable[Any],
) -> bool:
    normalized = {
        normalize_header(value)
        for value in row
        if clean_cell(value)
    }

    if not normalized:
        return False

    has_type = bool(
        normalized.intersection(
            TYPE_HEADERS
        )
    )

    has_title = bool(
        normalized.intersection(
            TITLE_HEADERS
        )
    )

    has_topic = bool(
        normalized.intersection(
            TOPIC_HEADERS
        )
    )

    has_hands_on = bool(
        normalized.intersection(
            HANDS_ON_HEADERS
        )
    )

    has_context = bool(
        normalized.intersection(
            COURSE_HEADERS
            | MODULE_HEADERS
            | LESSON_HEADERS
        )
    )

    if has_type and has_title:
        return True

    if has_topic:
        return True

    if has_hands_on:
        return True

    if has_title and has_context:
        return True

    return False


def find_header_row(
    dataframe: pd.DataFrame,
) -> int | None:
    search_limit = min(
        len(dataframe),
        HEADER_SEARCH_LIMIT,
    )

    for row_index in range(
        search_limit
    ):
        if looks_like_header_row(
            dataframe.iloc[row_index]
        ):
            return row_index

    return None


def get_cell(
    row: pd.Series,
    column_index: int | None,
) -> str:
    if column_index is None:
        return ""

    if (
        column_index < 0
        or column_index >= len(row)
    ):
        return ""

    return clean_cell(
        row.iloc[column_index]
    )


def row_values(
    row: Iterable[Any],
) -> list[str]:
    return [
        clean_cell(value)
        for value in row
    ]


def non_empty_values(
    row: Iterable[Any],
) -> list[str]:
    return [
        value
        for value in row_values(row)
        if value
    ]


def detect_fallback_columns(
    dataframe: pd.DataFrame,
    start_row: int = 0,
) -> tuple[int, int]:
    if dataframe.empty:
        return 0, 1

    column_count = len(
        dataframe.columns
    )

    if column_count == 1:
        return 0, 0

    search_end = min(
        len(dataframe),
        start_row + 80,
    )

    best_type_column = 0
    best_type_score = -1

    for column_index in range(
        column_count
    ):
        score = 0

        for row_index in range(
            start_row,
            search_end,
        ):
            value = clean_cell(
                dataframe.iloc[
                    row_index,
                    column_index,
                ]
            )

            if normalize_artifact_type(
                value
            ):
                score += 4

            elif detect_context_type(
                value
            ):
                score += 1

        if score > best_type_score:
            best_type_score = score
            best_type_column = (
                column_index
            )

    best_title_column = (
        best_type_column + 1
        if best_type_column + 1
        < column_count
        else best_type_column
    )

    best_title_score = -1

    for column_index in range(
        column_count
    ):
        if (
            column_index
            == best_type_column
        ):
            continue

        score = 0

        for row_index in range(
            start_row,
            search_end,
        ):
            artifact_value = clean_cell(
                dataframe.iloc[
                    row_index,
                    best_type_column,
                ]
            )

            title_value = clean_cell(
                dataframe.iloc[
                    row_index,
                    column_index,
                ]
            )

            if (
                normalize_artifact_type(
                    artifact_value
                )
                and title_value
            ):
                score += 3

            if (
                title_value
                and not normalize_artifact_type(
                    title_value
                )
                and not detect_context_type(
                    title_value
                )
            ):
                score += 1

        if score > best_title_score:
            best_title_score = score
            best_title_column = (
                column_index
            )

    return (
        best_type_column,
        best_title_column,
    )


def extract_context_from_row(
    row: pd.Series,
    current_course: str,
    current_module: str,
    current_lesson: str,
) -> tuple[str, str, str, bool]:
    values = non_empty_values(
        row
    )

    if not values:
        return (
            current_course,
            current_module,
            current_lesson,
            False,
        )

    context_updated = False

    for value in values:
        context_type = (
            detect_context_type(
                value
            )
        )

        if context_type == "course":
            current_course = value
            current_module = ""
            current_lesson = ""
            context_updated = True

        elif context_type == "module":
            current_module = value
            current_lesson = ""
            context_updated = True

        elif context_type == "lesson":
            current_lesson = value
            context_updated = True

    return (
        current_course,
        current_module,
        current_lesson,
        context_updated,
    )


def append_record(
    records: list[dict[str, str]],
    *,
    course: str,
    sheet_name: str,
    module: str,
    lesson: str,
    artifact_type: str,
    title: str,
    source_file: str,
    google_sheet: str,
) -> None:
    cleaned_title = clean_title(
        title
    )

    if not cleaned_title:
        return

    records.append(
        {
            "course": course,
            "sheet_name": (
                lesson
                or sheet_name
            ),
            "module": module,
            "lesson": lesson,
            "type": artifact_type,
            "title": cleaned_title,
            "source_file": (
                source_file
            ),
            "google_sheet": (
                google_sheet
            ),
        }
    )


def parse_artifact_layout(
    dataframe: pd.DataFrame,
    *,
    header_row: int | None,
    course_name: str,
    sheet_name: str,
    source_file: str,
    google_sheet: str,
) -> list[dict[str, str]]:
    records: list[
        dict[str, str]
    ] = []

    course_col: int | None = None
    module_col: int | None = None
    lesson_col: int | None = None
    artifact_col: int | None = None
    title_col: int | None = None

    data_start_row = 0

    if header_row is not None:
        headers = dataframe.iloc[
            header_row
        ]

        course_col = find_contains_column(
            headers,
            COURSE_HEADERS,
        )

        module_col = find_contains_column(
            headers,
            MODULE_HEADERS,
        )

        lesson_col = find_contains_column(
            headers,
            LESSON_HEADERS,
        )

        artifact_col = find_contains_column(
            headers,
            TYPE_HEADERS,
        )

        title_col = find_contains_column(
            headers,
            TITLE_HEADERS,
        )

        data_start_row = (
            header_row + 1
        )

    if (
        artifact_col is None
        or title_col is None
    ):
        (
            fallback_type_col,
            fallback_title_col,
        ) = detect_fallback_columns(
            dataframe,
            start_row=data_start_row,
        )

        if artifact_col is None:
            artifact_col = (
                fallback_type_col
            )

        if title_col is None:
            title_col = (
                fallback_title_col
            )

    current_course = clean_cell(
        course_name
    )

    current_module = ""
    current_lesson = ""

    for row_index in range(
        data_start_row,
        len(dataframe),
    ):
        row = dataframe.iloc[
            row_index
        ]

        if not any(
            clean_cell(value)
            for value in row
        ):
            continue

        explicit_course = get_cell(
            row,
            course_col,
        )

        explicit_module = get_cell(
            row,
            module_col,
        )

        explicit_lesson = get_cell(
            row,
            lesson_col,
        )

        if explicit_course:
            current_course = (
                explicit_course
            )

        if explicit_module:
            current_module = (
                explicit_module
            )

        if explicit_lesson:
            current_lesson = (
                explicit_lesson
            )

        artifact = get_cell(
            row,
            artifact_col,
        )

        title = get_cell(
            row,
            title_col,
        )

        normalized_type = (
            normalize_artifact_type(
                artifact
            )
        )

        if normalized_type is None:
            (
                current_course,
                current_module,
                current_lesson,
                context_updated,
            ) = extract_context_from_row(
                row,
                current_course,
                current_module,
                current_lesson,
            )

            if context_updated:
                continue

            continue

        append_record(
            records,
            course=(
                current_course
                or course_name
            ),
            sheet_name=sheet_name,
            module=current_module,
            lesson=current_lesson,
            artifact_type=(
                normalized_type
            ),
            title=title,
            source_file=source_file,
            google_sheet=google_sheet,
        )

    return records


def parse_topic_layout(
    dataframe: pd.DataFrame,
    *,
    header_row: int,
    course_name: str,
    sheet_name: str,
    source_file: str,
    google_sheet: str,
) -> list[dict[str, str]]:
    records: list[
        dict[str, str]
    ] = []

    headers = dataframe.iloc[
        header_row
    ]

    course_col = find_contains_column(
        headers,
        COURSE_HEADERS,
    )

    module_col = find_contains_column(
        headers,
        MODULE_HEADERS,
    )

    lesson_col = find_contains_column(
        headers,
        LESSON_HEADERS,
    )

    topic_col = find_contains_column(
        headers,
        TOPIC_HEADERS
        | TITLE_HEADERS,
    )

    hands_on_col = find_contains_column(
        headers,
        HANDS_ON_HEADERS,
    )

    if (
        topic_col is None
        and hands_on_col is None
    ):
        return []

    current_course = clean_cell(
        course_name
    )

    current_module = ""
    current_lesson = ""

    for row_index in range(
        header_row + 1,
        len(dataframe),
    ):
        row = dataframe.iloc[
            row_index
        ]

        if not any(
            clean_cell(value)
            for value in row
        ):
            continue

        explicit_course = get_cell(
            row,
            course_col,
        )

        explicit_module = get_cell(
            row,
            module_col,
        )

        explicit_lesson = get_cell(
            row,
            lesson_col,
        )

        if explicit_course:
            current_course = (
                explicit_course
            )

        if explicit_module:
            current_module = (
                explicit_module
            )

        if explicit_lesson:
            current_lesson = (
                explicit_lesson
            )

        (
            current_course,
            current_module,
            current_lesson,
            _,
        ) = extract_context_from_row(
            row,
            current_course,
            current_module,
            current_lesson,
        )

        topic_title = get_cell(
            row,
            topic_col,
        )

        hands_on_title = get_cell(
            row,
            hands_on_col,
        )

        if topic_title:
            append_record(
                records,
                course=(
                    current_course
                    or course_name
                ),
                sheet_name=sheet_name,
                module=current_module,
                lesson=current_lesson,
                artifact_type="Video",
                title=topic_title,
                source_file=source_file,
                google_sheet=google_sheet,
            )

        if hands_on_title:
            append_record(
                records,
                course=(
                    current_course
                    or course_name
                ),
                sheet_name=sheet_name,
                module=current_module,
                lesson=current_lesson,
                artifact_type="Demo",
                title=hands_on_title,
                source_file=source_file,
                google_sheet=google_sheet,
            )

    return records


def parse_sheet(
    dataframe: pd.DataFrame,
    *,
    course_name: str,
    sheet_name: str,
    source_file: str,
    google_sheet: str,
) -> list[dict[str, str]]:
    if (
        dataframe is None
        or dataframe.empty
    ):
        return []

    dataframe = (
        dataframe
        .fillna("")
        .reset_index(
            drop=True
        )
    )

    header_row = find_header_row(
        dataframe
    )

    if header_row is not None:
        headers = dataframe.iloc[
            header_row
        ]

        topic_col = find_contains_column(
            headers,
            TOPIC_HEADERS,
        )

        hands_on_col = (
            find_contains_column(
                headers,
                HANDS_ON_HEADERS,
            )
        )

        artifact_col = (
            find_contains_column(
                headers,
                TYPE_HEADERS,
            )
        )

        title_col = (
            find_contains_column(
                headers,
                TITLE_HEADERS,
            )
        )

        if (
            artifact_col is not None
            and title_col is not None
        ):
            return parse_artifact_layout(
                dataframe,
                header_row=header_row,
                course_name=course_name,
                sheet_name=sheet_name,
                source_file=source_file,
                google_sheet=google_sheet,
            )

        if (
            topic_col is not None
            or hands_on_col is not None
        ):
            return parse_topic_layout(
                dataframe,
                header_row=header_row,
                course_name=course_name,
                sheet_name=sheet_name,
                source_file=source_file,
                google_sheet=google_sheet,
            )

    return parse_artifact_layout(
        dataframe,
        header_row=header_row,
        course_name=course_name,
        sheet_name=sheet_name,
        source_file=source_file,
        google_sheet=google_sheet,
    )


def parse_old_format(
    dataframe: pd.DataFrame,
    course_name: str,
    sheet_name: str,
    source_file: str,
    google_sheet: str,
) -> list[dict[str, str]]:
    return parse_sheet(
        dataframe,
        course_name=course_name,
        sheet_name=sheet_name,
        source_file=source_file,
        google_sheet=google_sheet,
    )


def parse_new_format(
    dataframe: pd.DataFrame,
    source_file: str,
    google_sheet: str,
    course_name: str = "",
    sheet_name: str = "",
) -> list[dict[str, str]]:
    return parse_sheet(
        dataframe,
        course_name=course_name,
        sheet_name=sheet_name,
        source_file=source_file,
        google_sheet=google_sheet,
    )


def parse_workbook(
    file_path: str,
    course_name: str,
    source_file: str,
    google_sheet: str = "",
) -> list[dict[str, str]]:
    workbook = pd.read_excel(
        file_path,
        sheet_name=None,
        header=None,
        dtype=object,
    )

    records: list[
        dict[str, str]
    ] = []

    for sheet_name, dataframe in (
        workbook.items()
    ):
        try:
            sheet_records = parse_sheet(
                dataframe,
                course_name=course_name,
                sheet_name=str(
                    sheet_name
                ),
                source_file=source_file,
                google_sheet=google_sheet,
            )

            records.extend(
                sheet_records
            )

        except Exception:
            continue

    return records