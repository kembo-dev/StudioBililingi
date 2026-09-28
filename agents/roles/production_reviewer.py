from __future__ import annotations

from agents.backends import get_text


class ProductionReviewer:
    """Structured QA with optional frame-level visual inspection."""

    role = "production_reviewer"

    def __init__(self):
        self.text = get_text(role=self.role)

    def review(self, *, shot: dict, take: dict, continuity: dict, frames: list[str] | None = None) -> dict:
        system = (
            "Tu es le Production Reviewer de StudioBililingi. Évalue uniquement ce qui est réellement fourni. "
            "Contrôle conformité au shot, continuité, références, identité, vêtements, accessoires, décor, cadrage, "
            "langue, dialogue, voix et contraintes de révision. Réponds uniquement en JSON: "
            "{verdict:'pass'|'revise'|'unknown', issues:[...], checks:[...], visual_checks:[...]}. "
            "Si des images de frames sont fournies, inspecte-les visuellement et compare-les aux références et locks "
            "décrits dans les métadonnées. N'invente jamais de détail invisible. Si aucune frame n'est disponible, "
            "marque les critères purement visuels comme unknown."
        )
        user = f"SHOT:\n{shot}\n\nTAKE:\n{take}\n\nCONTINUITE:\n{continuity}"
        if frames and hasattr(self.text, "generate_json_with_images"):
            result = self.text.generate_json_with_images(system=system, user=user, images=frames)
            result["visual_review"] = True
            result["reviewed_frames"] = list(frames)
        else:
            result = self.text.generate_json(system=system, user=user)
            result["visual_review"] = False
            result["reviewed_frames"] = list(frames or [])
        result.setdefault("verdict", "unknown")
        result.setdefault("issues", [])
        result.setdefault("checks", [])
        result.setdefault("visual_checks", [])
        return result
