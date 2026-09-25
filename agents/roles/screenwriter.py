from __future__ import annotations

from agents.backends import get_text


class Screenwriter:
    role = "screenwriter"

    def __init__(self):
        self.text = get_text(role=self.role)

    def write(
        self,
        *,
        concept: str,
        bible: dict,
        episode: dict,
        form: str = "storytell",
        continuity: list[dict] | None = None,
        narrative_contract: dict | None = None,
        project_constraints: dict | None = None,
    ) -> dict:
        shapes = {
            "conversation": (
                "MODE CONVERSATION. Le scénario est porté par de vrais échanges entre personnages présents ou reliés "
                "de façon crédible (face à face, téléphone, visio). Utilise des en-têtes de scène "
                "(INT./EXT. - LIEU - JOUR/NUIT), de très brèves actions visuelles, puis des répliques au format "
                "NOM CANONIQUE : texte. Quand une scène contient un échange, écris les DEUX côtés de la conversation: "
                "question/réponse/réaction. N'écris jamais une série de réponses du protagoniste à un interlocuteur "
                "inaudible. Un monologue ou une parole au grand-père absent reste possible ponctuellement si l'histoire "
                "l'exige, mais ne doit pas devenir la structure dominante de l'épisode. Pas de narrateur. "
                "Utilise uniquement les noms canoniques de la bible et fais avancer l'action par le dialogue."
            ),
            "voix_off": (
                "MODE VOIX OFF. La narration VOIX OFF porte l'histoire et les images l'illustrent. "
                "Sépare clairement VOIX OFF et actions visuelles."
            ),
            "rencontre": (
                "MODE RENCONTRE. Deux présences se rencontrent physiquement : gestes, silences et répliques courtes "
                "font avancer la scène."
            ),
            "storytell": "MODE STORYTELL. Narration cinématographique à la troisième personne, sans faux dialogue.",
        }
        shape = shapes.get(form, shapes["storytell"])
        return self.text.generate_json(
            system=(
                "Tu es le scénariste de StudioBililingi. Écris UN épisode exploitable en production vidéo. "
                "Réponds en JSON avec exactement les clés fountain et scenes. fountain contient le scénario complet. "
                "scenes est une liste d'objets avec index, heading, summary, location_id, time_of_day et character_ids. "
                f"{shape} Respecte strictement la bible, le ton, les noms, lieux et objets établis. "
                "PROJECT CONTRACT: les contraintes projet sont canoniques. Respecte genre, sous-genre et cadre géographique/culturel sans déplacer l'histoire. Respecte la durée cible de l'épisode: calibre la quantité d'action et de narration pour cette durée sans répétition, remplissage moral ou nouvelle sous-intrigue. "
                "N'introduis pas spontanément un nouveau lieu majeur, passage secret, tunnel, pièce cachée, organisation, "
                "réseau, mouvement, artefact central ou nouvel enjeu politique qui n'est ni dans le CONCEPT ni dans la BIBLE. "
                "Si l'épisode exige un nouvel élément visuel mineur, décris-le explicitement dans scenes mais ne transforme "
                "jamais cet ajout en nouvelle prémisse de la série. L'arc doit rester une conséquence directe du concept. "
                "SCENE CONTRACT: crée une nouvelle scène dès que le lieu ou le temps change. Chaque scène doit avoir un location_id canonique correspondant au lieu réellement montré; ne saute jamais un trajet ou un lieu intermédiaire décrit par l'action. "
                "EVENT CONTRACT: respecte strictement le NARRATIVE CONTRACT, notamment point_of_view, narrator, tense et events. En voix off, si point_of_view=third_person et narrator=external, le narrateur ne doit JAMAIS parler comme le protagoniste avec je/moi/mon/ma. L'épisode doit seulement accomplir les événements prévus; ne recommence pas le début de l'histoire pour remplir la durée et ne rejoue aucun événement déjà présent dans la continuité. "
                "La continuité canonique des épisodes précédents est une contrainte: ne renomme pas un lieu, "
                "ne répète pas un événement déjà accompli et ne prétends pas qu'une action passée a eu lieu si elle "
                "n'apparaît pas dans cette continuité. Français naturel."
            ),
            user=(
                f"MODE DE LIVRAISON: {form}\n\n"
                f"CONCEPT:\n{concept}\n\n"
                f"CONTRAINTES PROJET VERROUILLEES:\n{project_constraints or {}}\n\n"
                f"BIBLE:\n{bible}\n\n"
                f"NARRATIVE CONTRACT VERROUILLE:\n{narrative_contract or {}}\n\n"
                f"CONTINUITE CANONIQUE DES EPISODES PRECEDENTS:\n{continuity or []}\n\n"
                f"EPISODE:\n{episode}"
            ),
        )
