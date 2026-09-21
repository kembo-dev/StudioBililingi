from __future__ import annotations

import re
from copy import deepcopy

MIN_WORDS = 12
TARGET_WORDS = 24
MAX_WORDS = 32

_SPEAKER_RE = re.compile(
    r"(?m)(?:^|\n|[.!?]\s+)([A-ZÀ-ÖØ-Þ][A-ZÀ-ÖØ-Þ0-9 _'’.-]{1,40})\s*:"
)


def words(text: str) -> list[str]:
    return [w for w in re.split(r"\s+", (text or "").strip()) if w]


def speaker_label(value: str) -> str:
    match = _SPEAKER_RE.search(value or "")
    return match.group(1).strip() if match else ""


def _sentences(text: str) -> list[str]:
    text = (text or "").strip()
    if not text:
        return []
    parts = re.split(r"(?<=[.!?…])\s+", text)
    return [p.strip() for p in parts if p.strip()]


def _hard_split(text: str, max_words: int = MAX_WORDS) -> list[str]:
    tokens = words(text)
    if not tokens:
        return []
    return [" ".join(tokens[i:i + max_words]) for i in range(0, len(tokens), max_words)]


def split_text(text: str, max_words: int = MAX_WORDS) -> list[str]:
    """Split at sentence boundaries first, hard-splitting only as a last resort."""
    if len(words(text)) <= max_words:
        return [text.strip()]

    sentences = _sentences(text)
    if len(sentences) <= 1:
        return _hard_split(text, max_words=max_words)

    chunks: list[str] = []
    current: list[str] = []
    for sentence in sentences:
        if len(words(sentence)) > max_words:
            if current:
                chunks.append(" ".join(current).strip())
                current = []
            chunks.extend(_hard_split(sentence, max_words=max_words))
            continue
        candidate = " ".join(current + [sentence]).strip()
        if current and len(words(candidate)) > max_words:
            chunks.append(" ".join(current).strip())
            current = [sentence]
        else:
            current.append(sentence)
    if current:
        chunks.append(" ".join(current).strip())
    return chunks


def _copy_for_split(row: dict, text: str, *, speaker: str = "") -> dict:
    clone = deepcopy(row)
    clone["text"] = text.strip()
    if speaker and clone.get("dialogue"):
        dialogue = str(clone.get("dialogue") or "").strip()
        if not speaker_label(dialogue):
            clone["dialogue"] = f"{speaker.upper()} : {dialogue}"
    return clone


def split_oversized_row(row: dict) -> list[dict]:
    text = str(row.get("text") or "").strip()
    if len(words(text)) <= MAX_WORDS:
        return [deepcopy(row)]

    label = speaker_label(str(row.get("dialogue") or "")) or speaker_label(text)
    pieces = split_text(text, MAX_WORDS)
    return [_copy_for_split(row, piece, speaker=label) for piece in pieces]


def same_scene(a: dict, b: dict) -> bool:
    return str(a.get("scene_index") or 1) == str(b.get("scene_index") or 1)


def merge_short_rows(rows: list[dict]) -> list[dict]:
    """Merge tiny beats only when the result stays renderable and in the same scene."""
    result: list[dict] = []
    i = 0
    while i < len(rows):
        row = deepcopy(rows[i])
        count = len(words(str(row.get("text") or "")))
        if count >= MIN_WORDS:
            result.append(row)
            i += 1
            continue

        merged = False
        if i + 1 < len(rows) and same_scene(row, rows[i + 1]):
            next_row = deepcopy(rows[i + 1])
            text = f"{row.get('text', '').strip()} {next_row.get('text', '').strip()}".strip()
            if len(words(text)) <= MAX_WORDS:
                next_row["text"] = text
                if row.get("dialogue") and not next_row.get("dialogue"):
                    next_row["dialogue"] = row.get("dialogue")
                rows[i + 1] = next_row
                merged = True
        if not merged and result and same_scene(result[-1], row):
            text = f"{result[-1].get('text', '').strip()} {row.get('text', '').strip()}".strip()
            if len(words(text)) <= MAX_WORDS:
                result[-1]["text"] = text
                if row.get("dialogue") and not result[-1].get("dialogue"):
                    result[-1]["dialogue"] = row.get("dialogue")
                merged = True

        if not merged:
            result.append(row)
        i += 1
    return result


def normalize_beats(
    chunks: list[dict],
    *,
    form: str,
    resolve_character_names,
) -> list[dict]:
    """Deterministic normalization after LLM generation and before persistence.

    resolve_character_names(row) must return canonical character names from the
    project bible/database for the structured character_ids on that row.
    """
    expanded: list[dict] = []
    for item in chunks:
        expanded.extend(split_oversized_row(dict(item)))

    normalized = merge_short_rows(expanded)

    if form == "conversation":
        for row in normalized:
            dialogue = str(row.get("dialogue") or "").strip()
            text = str(row.get("text") or "").strip()
            if not dialogue:
                continue
            label = speaker_label(dialogue) or speaker_label(text)
            if not label:
                names = resolve_character_names(row)
                if len(names) == 1:
                    label = names[0]
                elif names:
                    # Multiple visible characters do not identify the speaker.
                    # Keep the dialogue untouched and let semantic validation
                    # request a repair instead of attributing it arbitrarily.
                    row["speaker_candidates"] = names
            if label and not speaker_label(dialogue):
                row["dialogue"] = f"{label.upper()} : {dialogue}"

    for index, row in enumerate(normalized, start=1):
        row["normalized_index"] = index
        row["word_count"] = len(words(str(row.get("text") or "")))
    return normalized
