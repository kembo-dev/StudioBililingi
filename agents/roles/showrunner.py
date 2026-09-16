from __future__ import annotations

from agents.backends import get_text


class Showrunner:
    """Root role. Delegates. Stops at human checkpoints."""

    role = "showrunner"

    def __init__(self):
        self.text = get_text()

    def plan(self, concept: str) -> dict:
        return self.text.generate_json(
            system=(
                "Tu es le showrunner de StudioBililingi. "
                "Propose un plan de saison: logline, ton, nombre d'épisodes, checkpoints HITL."
            ),
            user=concept,
        )
