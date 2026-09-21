from __future__ import annotations

from agents.backends import get_text


class WorldBibleAgent:
    role = "world_bible"

    def __init__(self):
        self.text = get_text()

    def draft(self, concept: str, *, delivery: str = "storytell") -> dict:
        conversation_rule = (
            "MODE CONVERSATION: la bible doit rendre possibles de vrais échanges dramatiques. "
            "Nomme le protagoniste avec un vrai nom propre, jamais un intitulé générique comme Designer Parisien. "
            "Ajoute seulement les personnages secondaires réellement utiles au concept et à l'arc (collègue, artisan, "
            "client, proche, fournisseur, etc. selon l'histoire), avec au moins un interlocuteur actif récurrent si le "
            "concept le permet. Ne crée pas de figurants artificiels uniquement pour remplir cette règle. "
        ) if delivery == "conversation" else ""
        return self.text.generate_json(
            system=(
                "Tu construis une bible de série strictement à partir du concept fourni: personnages, lieux, objets. "
                "Réponds UNIQUEMENT avec un objet JSON. Il doit contenir obligatoirement les clés: "
                "version, project_id, logline, tone, locked, characters, locations, props. "
                "characters, locations et props sont TOUJOURS des tableaux JSON, jamais des objets ni du texte. "
                "Chaque entrée characters est un objet {id,name,aliases,role,want,need,look,voice,locked}. "
                "Chaque entrée locations est un objet {id,name,look,time_of_day,locked}. "
                "Chaque entrée props est un objet {id,name,look,story_function,locked}. "
                "Ne verrouille rien: locked=false. "
                "N'invente pas de personnages ou motifs hérités d'un autre récit. Les mots de structure éditoriale "
                "comme Concept, Début, Accroche, Fin, Conclusion, Twist, Genre ou Mode ne sont JAMAIS des personnages. "
                "Un personnage doit être une personne ou présence réellement décrite ou nécessaire au concept. "
                "Pour chaque personnage, fournis un id canonique court et stable dérivé de son nom, un name canonique "
                "qui sera utilisé dans tous les scripts, et aliases contenant les variantes utiles de ce même nom. "
                "N'utilise pas protag, protagoniste, hero, mentor, autre ou antag comme id si un vrai nom est disponible. "
                f"{conversation_rule}"
                "Les rôles, looks, voix, lieux et objets doivent être spécifiques à cette histoire."
            ),
            user=f"MODE DE LIVRAISON: {delivery}\n\nCONCEPT:\n{concept}",
        )
