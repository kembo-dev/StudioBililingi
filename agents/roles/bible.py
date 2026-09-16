from __future__ import annotations

from agents.backends import get_text


class WorldBibleAgent:
    role = "world_bible"

    def __init__(self):
        self.text = get_text()

    def draft(self, concept: str) -> dict:
        return self.text.generate_json(
            system=(
                "Tu construis une bible de série: personnages, lieux, objets. "
                "Réponds en JSON compatible world_bible.schema.json. "
                "Ne verrouille rien: locked=false."
            ),
            user=concept,
        )
