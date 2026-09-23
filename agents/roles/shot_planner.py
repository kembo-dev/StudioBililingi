from __future__ import annotations

from agents.backends import get_text


class ShotPlanner:
    """Splits one narrative beat into distinct filmable shots without narrative loss."""

    role = "shot_planner"

    def __init__(self):
        self.text = get_text()

    def plan(self, *, beat: dict, durations: list[int], bible: dict | None = None) -> dict:
        return self.text.generate_json(
            system=(
                "Tu es le Shot Planner de StudioBililingi. Un BEAT est une unité narrative canonique et ne doit jamais "
                "être réécrit, raccourci ou amputé. Découpe son contenu en SHOTS visuels successifs correspondant exactement "
                "aux durées fournies. Réponds uniquement en JSON {\"shots\":[...]}. Il doit y avoir exactement autant "
                "de shots que de durées. Chaque shot contient: index, text, video_prompt, camera, continuity. "
                "text décrit uniquement la portion narrative couverte par ce shot; l'union ordonnée des shots doit couvrir "
                "100% de l'action, du dialogue, des réactions et informations du beat, sans omission et sans duplication. "
                "Ne coupe jamais une phrase parlée au milieu. Si un dialogue traverse plusieurs shots, place la réplique "
                "complète dans un shot et utilise les autres pour l'écoute, les gestes ou réactions réellement présents "
                "dans le beat. N'invente aucun événement, personnage, lieu, objet ou dialogue. "
                "video_prompt est autonome et filmable: sujet visible, action précise, éventuel dialogue exact, réaction, "
                "cadrage/mouvement et continuité. Préserve strictement les ids et la continuité canonique fournis. "
                "LANGUE: conserve mot pour mot tout dialogue dans sa langue d'origine. Ne traduis, ne paraphrase et ne "
                "change jamais la langue d'une réplique. La voix et l'accent du personnage viennent de la BIBLE et restent "
                "identiques entre les shots. Les références visuelles canoniques sont des contraintes d'identité strictes."
            ),
            user=f"BIBLE:\n{bible or {}}\n\nBEAT CANONIQUE:\n{beat}\n\nDUREES SHOTS (secondes):\n{durations}",
        )
