from __future__ import annotations

from agents.backends import get_text


class BeatSegmenter:
    """Cuts a script into ~24-word beats for 6–8s clips."""

    role = "beat_segmenter"
    target_words = 24

    def __init__(self):
        self.text = get_text()

    def segment(self, script: str) -> dict:
        return self.text.generate_json(
            system=(
                "Découpe le script en beats. Chaque beat: ~24 mots, une action, "
                "un lieu, les personnages présents, intention caméra. "
                "JSON compatible beat.schema.json (liste)."
            ),
            user=script,
        )
