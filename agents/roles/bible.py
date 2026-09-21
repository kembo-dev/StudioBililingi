from __future__ import annotations

from agents.backends import get_text


class WorldBibleAgent:
    role = "world_bible"

    def __init__(self):
        self.text = get_text()

    def draft(self, concept: str) -> dict:
        return self.text.generate_json(
            system=(
                "Tu construis une bible de série strictement à partir du concept fourni: personnages, lieux, objets. "
                "Réponds en JSON compatible world_bible.schema.json. Ne verrouille rien: locked=false. "
                "N'invente pas de personnages ou motifs hérités d'un autre récit. Les mots de structure éditoriale "
                "comme Concept, Début, Accroche, Fin, Conclusion, Twist, Genre ou Mode ne sont JAMAIS des personnages. "
                "Un personnage doit être une personne ou présence réellement décrite ou nécessaire au concept. "
                "Pour chaque personnage, fournis un id canonique court et stable dérivé de son nom, un name canonique "
                "qui sera utilisé dans tous les scripts, et aliases contenant les variantes utiles de ce même nom. "
                "N'utilise pas protag, protagoniste, hero, mentor, autre ou antag comme id si un vrai nom est disponible. "
                "Les rôles, looks, voix, lieux et objets doivent être spécifiques à cette histoire."
            ),
            user=concept,
        )
