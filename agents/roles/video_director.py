from __future__ import annotations

from agents.backends import get_text


class VideoDirector:
    """Turns an approved shot package into provider-ready directing instructions."""

    role = "video_director"

    def __init__(self):
        self.text = get_text(role=self.role)

    def direct(self, *, shot: dict, continuity: dict, constraints: list[dict] | None = None) -> dict:
        return self.text.generate_json(
            system=(
                "Tu es le Video Director de StudioBililingi. Tu ne réécris jamais l'histoire ni les dialogues. "
                "Tu transformes un shot canonique en instructions de réalisation vidéo précises: blocking, performance, "
                "cadrage, mouvement caméra, lumière, rythme et son non verbal. Respecte absolument les références, "
                "identités, langue, speaker, narration et contraintes de continuité. Réponds uniquement en JSON avec "
                "video_direction, camera, performance, lighting, rhythm, sound et warnings. "
                "N'ajoute aucun personnage, objet, dialogue ou événement absent du shot."
            ),
            user=f"SHOT:\n{shot}\n\nCONTINUITE:\n{continuity}\n\nCONTRAINTES:\n{constraints or []}",
        )
