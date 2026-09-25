from __future__ import annotations

from agents.backends import get_text


class ScenePlanner:
    """Plans canonical scenes before beat segmentation."""

    role = "scene_planner"

    def __init__(self):
        self.text = get_text(role=self.role)

    def plan(
        self,
        *,
        script: str,
        episode: dict,
        bible: dict,
        narrative_contract: dict,
        project_constraints: dict,
    ) -> dict:
        return self.text.generate_json(
            system=(
                "Tu es le Scene Planner de StudioBililingi. Transforme le scénario en plan de scènes CANONIQUE avant "
                "tout découpage en beats. Réponds uniquement en JSON {\"scenes\":[...]}. Chaque scène contient exactement: "
                "index, heading, summary, location_id, time_of_day, character_ids, prop_ids, event_ids, target_seconds. "
                "location_id, character_ids et prop_ids utilisent uniquement les ids canoniques de la BIBLE. "
                "event_ids utilise uniquement les EVxx du NARRATIVE CONTRACT assignés à cet épisode. "
                "Crée une nouvelle scène à chaque changement réel de lieu ou de moment. Ne fusionne jamais maison, trajet, "
                "rue et école dans une même scène. Ne saute pas un lieu intermédiaire explicitement nécessaire à l'action. "
                "Chaque EVxx de l'épisode doit apparaître dans au moins une scène et aucun EVxx d'un autre épisode ne doit "
                "apparaître. Respecte genre, sous-genre, cadre géographique/culturel et mode. "
                "DURÉE PAR ÉPISODE: si episode_duration_seconds contient un nombre, c'est une durée FIXE pour CET épisode "
                "et la somme des target_seconds doit viser cette valeur. Si episode_duration_seconds vaut null/None, "
                "la durée est AUTOMATIQUE: estime la durée naturelle de CET épisode à partir du script, des dialogues, "
                "actions, silences et EVxx, puis répartis cette durée entre les scènes sans étirer ni compresser artificiellement. "
                "N'ajoute aucune scène de "
                "remplissage, morale abstraite, répétition d'un événement déjà accompli ou nouvelle sous-intrigue. "
                "Le plan décrit ce qui se passe et où; il ne réécrit pas l'histoire."
            ),
            user=(
                f"EPISODE:\n{episode}\n\n"
                f"CONTRAINTES PROJET:\n{project_constraints}\n\n"
                f"NARRATIVE CONTRACT:\n{narrative_contract}\n\n"
                f"BIBLE:\n{bible}\n\n"
                f"SCRIPT:\n{script}"
            ),
        )
