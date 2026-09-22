from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from django.utils.text import slugify


_GENERIC = {
    "protag", "protagoniste", "hero", "heros", "personnage", "character",
    "mentor", "antag", "antagoniste", "autre",
}


def identity_token(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.casefold().replace("’", "'")
    return re.sub(r"[^a-z0-9]+", "", value)


def _aliases_from_item(item: dict) -> list[str]:
    values = [item.get("id"), item.get("key"), item.get("name")]
    aliases = item.get("aliases") or []
    if isinstance(aliases, str):
        aliases = [aliases]
    values.extend(aliases)
    return [str(v).strip() for v in values if str(v or "").strip()]


def normalize_bible_payload(payload: dict) -> dict:
    """Give every character a stable canonical id and explicit aliases."""
    result = dict(payload or {})
    characters = []
    used: set[str] = set()
    for index, raw in enumerate(result.get("characters") or [], start=1):
        if not isinstance(raw, dict):
            continue
        item = dict(raw)
        name = str(item.get("name") or "").strip() or f"Personnage {index}"
        proposed = str(item.get("id") or item.get("key") or "").strip()
        key = slugify(proposed or name) or f"personnage-{index}"
        if key in _GENERIC:
            name_key = slugify(name)
            if name_key and name_key not in _GENERIC:
                key = name_key
        base = key
        suffix = 2
        while key in used:
            key = f"{base}-{suffix}"
            suffix += 1
        used.add(key)

        aliases = _aliases_from_item(item)
        aliases.extend([name, key, name.upper()])
        item["id"] = key
        item["name"] = name
        item["aliases"] = list(dict.fromkeys(a for a in aliases if a))
        characters.append(item)
    result["characters"] = characters
    return result


@dataclass(frozen=True)
class ResolvedCharacter:
    key: str
    name: str


class CharacterResolver:
    """Resolve LLM character references against canonical project identities."""

    def __init__(self, project):
        self.project = project
        self._index: dict[str, ResolvedCharacter] = {}
        bible = project.bibles.first()
        payload_items = (bible.payload.get("characters") or []) if bible else []
        aliases_by_key: dict[str, list[str]] = {}
        for item in payload_items:
            if not isinstance(item, dict):
                continue
            key = str(item.get("id") or item.get("key") or "")
            aliases_by_key[key] = _aliases_from_item(item)

        for character in project.characters.all():
            resolved = ResolvedCharacter(character.key, character.name)
            values = [character.key, character.name, character.name.upper()]
            values.extend(aliases_by_key.get(character.key, []))
            # Dialogue models often emit a title + canonical name (e.g.
            # "DR. LÉO DUBOIS") while the bible stores "Léo Dubois".
            # Index safe honorific variants instead of treating them as new identities.
            for value in list(values):
                clean = str(value or "").strip()
                if clean:
                    values.extend([
                        f"Dr {clean}", f"Dr. {clean}", f"Docteur {clean}",
                        f"M. {clean}", f"Mme {clean}",
                    ])
            for value in values:
                token = identity_token(value)
                if token:
                    self._index[token] = resolved

    def resolve(self, value) -> ResolvedCharacter | None:
        if isinstance(value, dict):
            candidates = [value.get("id"), value.get("key"), value.get("name")]
        else:
            candidates = [value]
        for candidate in candidates:
            token = identity_token(candidate)
            if token and token in self._index:
                return self._index[token]
        return None

    def resolve_many(self, values) -> list[ResolvedCharacter]:
        if not values:
            return []
        if isinstance(values, (str, dict)):
            values = [values]
        found = []
        seen = set()
        for value in values:
            character = self.resolve(value)
            if character and character.key not in seen:
                seen.add(character.key)
                found.append(character)
        return found

    def names_for_row(self, row: dict) -> list[str]:
        values = row.get("character_ids") or row.get("characters") or []
        return [item.name for item in self.resolve_many(values)]

    def canonical_keys(self, values) -> list[str]:
        return [item.key for item in self.resolve_many(values)]
