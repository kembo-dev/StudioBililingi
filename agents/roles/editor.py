from __future__ import annotations

from agents.backends import get_text


class Editor:
    """Plans episode assembly from approved takes without inventing story material."""

    role = "editor"

    def __init__(self):
        self.text = get_text(role=self.role)

    def plan(self, *, episode: dict, shots: list[dict]) -> dict:
        result = self.text.generate_json(
            system=(
                "Tu es le monteur de StudioBililingi. Tu travailles uniquement avec les shots/takes fournis. "
                "Tu ne réécris jamais l'histoire. Vérifie ordre, raccords, rythme, continuité et transitions. "
                "Réponds uniquement en JSON avec ordered_shot_ids, transitions, pacing_notes, continuity_warnings, ready. "
                "Si un shot requis n'a pas de take verrouillé, ready=false."
            ),
            user=f"EPISODE:\n{episode}\n\nSHOTS:\n{shots}",
        )
        result.setdefault("ordered_shot_ids", [])
        result.setdefault("transitions", [])
        result.setdefault("pacing_notes", [])
        result.setdefault("continuity_warnings", [])
        result.setdefault("ready", False)
        return result
