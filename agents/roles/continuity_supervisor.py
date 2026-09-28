from __future__ import annotations

from agents.backends import get_text


class ContinuitySupervisor:
    """Audits a shot package against canonical visual/audio constraints."""

    role = "continuity_supervisor"

    def __init__(self):
        self.text = get_text(role=self.role)

    def inspect(self, *, shot: dict, continuity: dict, references: list[dict], scene_frame: dict | None = None) -> dict:
        result = self.text.generate_json(
            system=(
                "Tu es le Continuity Supervisor de StudioBililingi. Vérifie sans réécrire le contenu: identité des "
                "personnages, références UID, vêtements, accessoires, décor, Scene Frame, speaker, langue et voix. "
                "Réponds uniquement en JSON: {compliant:boolean, errors:[string], warnings:[string], locks:[string]}. "
                "Une erreur est une contradiction canonique certaine; une information absente devient un warning, pas une invention."
            ),
            user=f"SHOT:\n{shot}\n\nCONTINUITE:\n{continuity}\n\nREFERENCES:\n{references}\n\nSCENE_FRAME:\n{scene_frame or {}}",
        )
        result.setdefault("compliant", not bool(result.get("errors")))
        result.setdefault("errors", [])
        result.setdefault("warnings", [])
        result.setdefault("locks", [])
        return result
