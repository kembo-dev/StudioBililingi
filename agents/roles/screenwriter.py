from __future__ import annotations

from agents.backends import get_text


class Screenwriter:
    role = "screenwriter"

    def __init__(self):
        self.text = get_text()

    def write(self, *, concept: str, bible: dict, episode: dict, form: str = "storytell") -> dict:
        shapes = {
            "conversation": (
                "MODE CONVERSATION. Le scénario est porté par de vraies répliques entre les personnages. "
                "Utilise des en-têtes de scène (INT./EXT. - LIEU - JOUR/NUIT), de très brèves actions visuelles, "
                "puis des répliques au format NOM : texte. Pas de narrateur et pas de prose racontant ce que les "
                "personnages pourraient dire. La conversation doit faire avancer l'action et rester jouable à l'écran."
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
                f"{shape} Respecte strictement la bible, le ton, les noms, lieux et objets établis. Français naturel."
            ),
            user=(
                f"MODE DE LIVRAISON: {form}\n\n"
                f"CONCEPT:\n{concept}\n\n"
                f"BIBLE:\n{bible}\n\n"
                f"EPISODE:\n{episode}"
            ),
        )
