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


def _speaker_occurrences(text: str) -> list[tuple[int, int, str]]:
    return [(m.start(1), m.end(), m.group(1).strip()) for m in _SPEAKER_RE.finditer(text or "")]


def split_multi_speaker_row(row: dict) -> list[dict]:
    """One dialogue speaker per beat; never keep A: ... B: ... together."""
    text = str(row.get("text") or "").strip()
    occurrences = _speaker_occurrences(text)
    if len(occurrences) <= 1:
        return [deepcopy(row)]

    pieces: list[dict] = []
    prefix = text[:occurrences[0][0]].strip()
    for i, (start, _end, label) in enumerate(occurrences):
        stop = occurrences[i + 1][0] if i + 1 < len(occurrences) else len(text)
        piece = text[start:stop].strip()
        if i == 0 and prefix:
            piece = f"{prefix} {piece}".strip()
        clone = deepcopy(row)
        clone["text"] = piece
        clone["dialogue"] = piece
        clone["speaker_label"] = label
        clone.pop("speaker_id", None)
        pieces.append(clone)
    return pieces


def split_oversized_row(row: dict) -> list[dict]:
    """Split long beats without duplicating a complete dialogue on every child."""
    text = str(row.get("text") or "").strip()
    if len(words(text)) <= MAX_WORDS:
        return [deepcopy(row)]

    label = speaker_label(str(row.get("dialogue") or "")) or speaker_label(text)
    pieces = split_text(text, MAX_WORDS)
    result: list[dict] = []
    for piece in pieces:
        clone = deepcopy(row)
        clone["text"] = piece.strip()
        if clone.get("dialogue"):
            clone["dialogue"] = piece.strip()
            if label and not speaker_label(clone["dialogue"]):
                clone["dialogue"] = f"{label.upper()} : {clone['dialogue']}"
        result.append(clone)
    return result

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


def inherit_orphan_dialogue_continuations(rows: list[dict], *, resolve_character_names) -> list[dict]:
    """Carry the previous speaker onto tiny continuation fragments.

    Segmenters sometimes split a spoken sentence into two beats and omit the
    speaker on the second fragment (e.g. "CHLOÉ: Merci..." / "Tu as raison...").
    We only inherit when the previous row is explicit dialogue, both rows are in
    the same scene, and the orphan is short enough to plausibly be a continuation.
    """
    result: list[dict] = []
    for raw in rows:
        row = deepcopy(raw)
        text = str(row.get("text") or "").strip()
        explicit_here = speaker_label(text) or speaker_label(str(row.get("dialogue") or ""))
        if (
            result
            and not explicit_here
            and not row.get("dialogue")
            and len(words(text)) <= 10
            and same_scene(result[-1], row)
        ):
            prev = result[-1]
            prev_label = speaker_label(str(prev.get("dialogue") or "")) or speaker_label(str(prev.get("text") or ""))
            prev_speaker_id = prev.get("speaker_id")
            if prev_label or prev_speaker_id:
                # Do not reinterpret obvious visual/action directions as speech.
                actionish = bool(re.match(
                    r"^(le|la|les|un|une|il|elle|ils|elles|plan|caméra|camera|submersible|thomas\s+(entre|s'approche|tend|verse)|chloé\s+(prend|sourit|regarde))\b",
                    text,
                    flags=re.I,
                ))
                if not actionish:
                    label = prev_label or str(prev_speaker_id)
                    row["dialogue"] = f"{label.upper()} : {text}"
                    row["text"] = row["dialogue"]
                    if prev_speaker_id:
                        row["speaker_id"] = prev_speaker_id
                    else:
                        # Resolve the inherited dialogue label immediately so
                        # normalized conversation beats carry the canonical key.
                        names = resolve_character_names(row)
                        if len(names) == 1:
                            row["speaker_id"] = next(
                                (
                                    key for key in (row.get("character_ids") or [])
                                    if isinstance(key, str)
                                ),
                                None,
                            )
                    row["speaker_inherited"] = True
        result.append(row)
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
    speaker_split: list[dict] = []
    for item in chunks:
        speaker_split.extend(split_multi_speaker_row(dict(item)))

    expanded: list[dict] = []
    for item in speaker_split:
        expanded.extend(split_oversized_row(item))

    # Do not merge dialogue beats: a merge can recreate two-speaker beats or
    # attach an action to the wrong speaker. Tiny dialogue beats are valid
    # render units; only non-dialogue action beats are eligible for merging.
    normalized: list[dict] = []
    action_buffer: list[dict] = []
    for row in expanded:
        if row.get("dialogue") or speaker_label(str(row.get("text") or "")):
            if action_buffer:
                normalized.extend(merge_short_rows(action_buffer))
                action_buffer = []
            normalized.append(row)
        else:
            action_buffer.append(row)
    if action_buffer:
        normalized.extend(merge_short_rows(action_buffer))

    if form == "conversation":
        normalized = inherit_orphan_dialogue_continuations(normalized, resolve_character_names=resolve_character_names)
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
