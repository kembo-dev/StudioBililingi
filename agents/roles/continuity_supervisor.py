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

    def inspect_scene_frame(self, *, shot: dict, scene_frame: dict | None = None) -> dict:
        """Visually verify that a locked Scene Frame actually depicts the shot to render."""
        scene_frame = scene_frame or {}
        uri = str(scene_frame.get("uri") or "").strip()
        if not uri or not hasattr(self.text, "generate_json_with_images"):
            return {
                "suitable": True,
                "status": "unknown",
                "errors": [],
                "warnings": ["Scene Frame visual compatibility was not checked by this backend."],
            }
        result = self.text.generate_json_with_images(
            system=(
                "Tu es le Continuity Supervisor de StudioBililingi. Tu reçois UNE image: la Scene Frame verrouillée "
                "qui pourrait devenir l'image de départ d'une génération vidéo. Vérifie visuellement si cette image "
                "est compatible avec l'action visuelle, le cadrage, le décor et les contraintes explicites du shot. "
                "Ne juge pas le style artistique général. Une incompatibilité certaine (par exemple maison au sol "
                "alors que le shot exige une vue aérienne des toits d'une ville) doit rendre suitable=false. "
                "Réponds uniquement en JSON: "
                "{suitable:boolean,status:'pass'|'fail'|'unknown',errors:[string],warnings:[string],checks:[object]}."
            ),
            user=(
                "SHOT A PRODUIRE:\n"
                f"{shot}\n\n"
                "L'image fournie après ce texte est la Scene Frame verrouillée. "
                "Décide si elle peut servir d'ancre visuelle sans contredire le shot."
            ),
            images=[uri],
        )
        result.setdefault("suitable", result.get("status") != "fail")
        result.setdefault("status", "pass" if result.get("suitable") else "fail")
        result.setdefault("errors", [])
        result.setdefault("warnings", [])
        result.setdefault("checks", [])
        return result
