from __future__ import annotations

from agents.backends import get_text


class ProductionReviewer:
    """Produces a structured QA verdict; humans remain responsible for final lock approval."""

    role = "production_reviewer"

    def __init__(self):
        self.text = get_text(role=self.role)

    def review(self, *, shot: dict, take: dict, continuity: dict) -> dict:
        result = self.text.generate_json(
            system=(
                "Tu es le Production Reviewer de StudioBililingi. Évalue uniquement les éléments observables ou les "
                "métadonnées fournies: conformité au shot, continuité, références, langue, dialogue, voix et contraintes "
                "de révision. Réponds uniquement en JSON: {verdict:'pass'|'revise'|'unknown', issues:[...], checks:[...]}. "
                "Si la vidéo elle-même n'est pas analysable à partir des données fournies, utilise unknown pour les critères "
                "visuels concernés. Ne prétends jamais avoir vu une vidéo non fournie."
            ),
            user=f"SHOT:\n{shot}\n\nTAKE:\n{take}\n\nCONTINUITE:\n{continuity}",
        )
        result.setdefault("verdict", "unknown")
        result.setdefault("issues", [])
        result.setdefault("checks", [])
        return result
