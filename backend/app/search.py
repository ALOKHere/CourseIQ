import re
from collections import Counter

from rapidfuzz import fuzz, process

from app.database import get_searchable_content


STOP_WORDS = {
    "a",
    "an",
    "and",
    "the",
    "of",
    "for",
    "to",
    "in",
    "on",
    "with",
    "using",
    "from",
    "into",
    "by",
    "or",
    "is",
    "are",
}


ALIASES = {
    "cnn": [
        "convolutional neural network",
        "convolutional neural networks",
        "convolutional network",
        "convolutional networks",
        "image classification",
        "computer vision",
        "feature maps",
        "convolution layers",
    ],
    "rnn": [
        "recurrent neural network",
        "recurrent neural networks",
        "sequence model",
        "sequence models",
    ],
    "lstm": [
        "long short term memory",
        "recurrent neural network",
        "sequence model",
    ],
    "nlp": [
        "natural language processing",
        "text processing",
        "language models",
    ],
    "llm": [
        "large language model",
        "large language models",
        "generative ai",
    ],
    "genai": [
        "generative ai",
        "generative artificial intelligence",
    ],
    "ml": [
        "machine learning",
    ],
    "dl": [
        "deep learning",
    ],
    "cv": [
        "computer vision",
        "image recognition",
        "image classification",
    ],
    "dax": [
        "data analysis expressions",
    ],
    "bi": [
        "business intelligence",
    ],
    "etl": [
        "extract transform load",
        "data preparation",
        "data pipeline",
    ],
    "eda": [
        "exploratory data analysis",
        "data exploration",
    ],
    "api": [
        "application programming interface",
    ],
    "rag": [
        "retrieval augmented generation",
        "retrieval generation",
    ],
    "xai": [
        "explainable artificial intelligence",
        "explainable ai",
    ],
    "transformer": [
        "transformer architecture",
        "attention mechanism",
        "self attention",
        "multi head attention",
    ],
    "transformers": [
        "transformer architecture",
        "attention mechanism",
        "self attention",
        "multi head attention",
    ],
    "visualization": [
        "visualisation",
        "charts",
        "graphs",
        "matplotlib",
        "seaborn",
    ],
    "visualisation": [
        "visualization",
        "charts",
        "graphs",
        "matplotlib",
        "seaborn",
    ],
}


RELATED_TOPICS = {
    "convolutional": [
        "cnn",
        "computer vision",
        "image classification",
        "feature extraction",
        "feature maps",
        "convolution layers",
    ],
    "attention": [
        "transformer",
        "self attention",
        "multi head attention",
        "encoder",
        "decoder",
    ],
    "graphs": [
        "visualization",
        "visualisation",
        "matplotlib",
        "seaborn",
        "charts",
    ],
    "deployment": [
        "docker",
        "containerization",
        "inference",
        "model serving",
        "api",
    ],
}


def normalize(value) -> str:
    if value is None:
        return ""

    text = str(value).lower().strip()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def tokenize(value) -> list[str]:
    return [
        word
        for word in normalize(value).split()
        if word and word not in STOP_WORDS
    ]


def build_acronym(value: str) -> str:
    words = tokenize(value)

    if len(words) < 2:
        return ""

    return "".join(word[0] for word in words)


def get_search_vocabulary(rows) -> list[str]:
    vocabulary = set()

    for database_row in rows:
        row = dict(database_row)

        fields = [
            row.get("title"),
            row.get("module"),
            row.get("course"),
            row.get("sheet_name"),
        ]

        for field in fields:
            normalized_field = normalize(field)

            if not normalized_field:
                continue

            vocabulary.add(normalized_field)

            for word in tokenize(normalized_field):
                if len(word) >= 3:
                    vocabulary.add(word)

    for alias, phrases in ALIASES.items():
        vocabulary.add(alias)

        for phrase in phrases:
            vocabulary.add(normalize(phrase))

            for word in tokenize(phrase):
                if len(word) >= 3:
                    vocabulary.add(word)

    return sorted(vocabulary)


def correct_query(query: str, vocabulary: list[str]) -> tuple[str, bool]:
    normalized_query = normalize(query)

    if not normalized_query:
        return "", False

    if normalized_query in vocabulary:
        return normalized_query, False

    query_words = tokenize(normalized_query)

    if not query_words:
        return normalized_query, False

    corrected_words = []
    changed = False

    word_vocabulary = [
        item
        for item in vocabulary
        if " " not in item
    ]

    for word in query_words:
        if word in word_vocabulary:
            corrected_words.append(word)
            continue

        best_match = process.extractOne(
            word,
            word_vocabulary,
            scorer=fuzz.WRatio,
            score_cutoff=72,
        )

        if best_match:
            matched_word = best_match[0]
            match_score = best_match[1]

            if match_score >= 72:
                corrected_words.append(matched_word)
                changed = matched_word != word
                continue

        corrected_words.append(word)

    corrected_query = " ".join(corrected_words)

    return corrected_query, changed


def expand_query(query: str) -> list[str]:
    normalized_query = normalize(query)

    expansions = {
        normalized_query,
    }

    query_words = tokenize(normalized_query)

    for alias, meanings in ALIASES.items():
        if (
            normalized_query == alias
            or alias in query_words
        ):
            expansions.update(
                normalize(item)
                for item in meanings
            )

    for word in query_words:
        if word in RELATED_TOPICS:
            expansions.update(
                normalize(item)
                for item in RELATED_TOPICS[word]
            )

    return [
        item
        for item in expansions
        if item
    ]


def type_matches(
    row_type: str,
    selected_type: str,
) -> bool:
    selected = normalize(selected_type)
    row_value = normalize(row_type)

    if selected == "all":
        return True

    if selected == "assignment":
        return (
            "assignment" in row_value
            or "quiz" in row_value
            or "project" in row_value
        )

    if selected == "demo":
        return row_value in {
            "demo",
            "demonstration",
            "lab",
        }

    if selected == "reading":
        return row_value in {
            "reading",
            "article",
        }

    return row_value == selected


def score_text(
    query: str,
    text: str,
    exact_weight: float,
    fuzzy_weight: float,
) -> float:
    normalized_query = normalize(query)
    normalized_text = normalize(text)

    if not normalized_query or not normalized_text:
        return 0.0

    score = 0.0

    if normalized_query == normalized_text:
        score += exact_weight

    elif normalized_query in normalized_text:
        score += exact_weight * 0.8

    query_words = tokenize(normalized_query)
    text_words = tokenize(normalized_text)

    if query_words and text_words:
        overlap = len(
            set(query_words).intersection(text_words)
        )

        score += overlap * 18

    score += (
        fuzz.WRatio(
            normalized_query,
            normalized_text,
        )
        / 100
    ) * fuzzy_weight

    score += (
        fuzz.token_set_ratio(
            normalized_query,
            normalized_text,
        )
        / 100
    ) * (fuzzy_weight * 0.7)

    return score


def calculate_score(
    original_query: str,
    corrected_query: str,
    expansions: list[str],
    row: dict,
) -> float:
    title = normalize(row.get("title"))
    module = normalize(row.get("module"))
    course = normalize(row.get("course"))
    sheet_name = normalize(row.get("sheet_name"))

    score = 0.0

    title_acronym = build_acronym(title)
    module_acronym = build_acronym(module)
    course_acronym = build_acronym(course)

    normalized_original = normalize(original_query)
    normalized_corrected = normalize(corrected_query)

    if normalized_original and normalized_original == title_acronym:
        score += 170

    if normalized_original and normalized_original == module_acronym:
        score += 120

    if normalized_original and normalized_original == course_acronym:
        score += 100

    score += score_text(
        normalized_corrected,
        title,
        exact_weight=150,
        fuzzy_weight=80,
    )

    score += score_text(
        normalized_corrected,
        module,
        exact_weight=75,
        fuzzy_weight=35,
    )

    score += score_text(
        normalized_corrected,
        course,
        exact_weight=60,
        fuzzy_weight=25,
    )

    score += score_text(
        normalized_corrected,
        sheet_name,
        exact_weight=50,
        fuzzy_weight=20,
    )

    searchable_text = " ".join(
        [
            title,
            module,
            course,
            sheet_name,
        ]
    )

    for expansion in expansions:
        expansion_score = score_text(
            expansion,
            searchable_text,
            exact_weight=90,
            fuzzy_weight=35,
        )

        score += expansion_score * 0.75

    return round(score, 2)


def search_content(
    query: str = "",
    content_type: str = "All",
    limit: int = 100,
):
    rows = get_searchable_content()

    vocabulary = get_search_vocabulary(rows)

    corrected_query, query_was_corrected = correct_query(
        query=query,
        vocabulary=vocabulary,
    )

    expansions = expand_query(corrected_query)

    ranked_results = []

    for database_row in rows:
        row = dict(database_row)

        if not type_matches(
            row_type=row.get("type", ""),
            selected_type=content_type,
        ):
            continue

        score = calculate_score(
            original_query=query,
            corrected_query=corrected_query,
            expansions=expansions,
            row=row,
        )

        if query.strip() and score < 55:
            continue

        row["relevance_score"] = score

        ranked_results.append(row)

    ranked_results.sort(
        key=lambda item: (
            -item["relevance_score"],
            normalize(item.get("title")),
        )
    )

    return {
        "results": ranked_results[:limit],
        "corrected_query": corrected_query,
        "query_was_corrected": query_was_corrected,
    }