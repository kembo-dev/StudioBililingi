from __future__ import annotations

from agents.backends import get_text


class Screenwriter:
    role = "screenwriter"

    def __init__(self):
        self.text = get_text()

    def write(self, *, concept: str, bible: dict, episode: dict) -> dict:
        return self.text.generate_json(
            system=(
                "Tu écris le script d'un épisode de série courte. JSON uniquement : "
                '{"fountain": str, "scenes": [{"heading": str, "action": str, "dialogue": [str]}]}. '
                "Respecte STRICTEMENT les personnages, lieux et objets de la bible. "
                "Pas de nouveaux personnages. Texte en français, visuel, jouable."
            ),
            user=f"CONCEPT:\n{concept}\n\nBIBLE:\n{bible}\n\nEPISODE:\n{episode}",
        )
