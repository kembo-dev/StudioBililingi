from __future__ import annotations

import re

from apps.projects.character_resolver import identity_token, normalize_bible_payload

_GENERIC_NAMES = {
    "designerparisien", "jeune designer", "jeunedesigner", "protagoniste",
    "personnageprincipal", "hero", "heros",
}


def _is_generic_name(name: str) -> bool:
    token = identity_token(name)
    return token in {identity_token(value) for value in _GENERIC_NAMES}


def normalize_story_bible(payload: dict, *, delivery: str) -> dict:
    """Normalize semantic story invariants before persistence."""
    result = normalize_bible_payload(payload)
    characters = result.get("characters") or []

    for item in characters:
        name = str(item.get("name") or "").strip()
        if _is_generic_name(name):
            item["needs_canonical_name"] = True

    if delivery == "conversation":
        active = [
            item for item in characters
            if str(item.get("role") or "").casefold() not in {"posthume", "mentor posthume"}
        ]
        result["conversation_profile"] = {
            "active_character_count": len(active),
            "has_interlocutor": len(active) >= 2,
        }
    return result


def bible_errors(payload: dict, *, delivery: str) -> list[str]:
    errors = []
    characters = payload.get("characters") or []
    for item in characters:
        if item.get("needs_canonical_name"):
            errors.append(
                f"personnage sans vrai nom canonique: {item.get('name')!r}"
            )

    if delivery == "conversation":
        profile = payload.get("conversation_profile") or {}
        if not profile.get("has_interlocutor"):
            errors.append(
                "mode conversation sans au moins deux personnages actifs capables d'échanger"
            )
    return errors


def script_conversation_errors(fountain: str, bible: dict) -> list[str]:
    """Detect structurally one-sided dialogue while allowing occasional monologue."""
    canonical = {
        identity_token(item.get("name")): item.get("name")
        for item in (bible.get("characters") or [])
        if item.get("name")
    }
    speakers = []
    for line in (fountain or "").splitlines():
        match = re.match(r"^\s*([^:]{2,60})\s*:\s*\S", line)
        if not match:
            continue
        token = identity_token(match.group(1))
        if token in canonical:
            speakers.append(canonical[token])

    unique = list(dict.fromkeys(speakers))
    if len(speakers) >= 4 and len(unique) < 2:
        return ["épisode conversation dominé par un seul locuteur"]
    return []
