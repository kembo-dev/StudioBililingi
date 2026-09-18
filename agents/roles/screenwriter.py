from __future__ import annotations

from agents.backends import get_text


class Screenwriter:
    role = "screenwriter"

    def __init__(self):
        self.text = get_text()

    def write(self, *, concept: str, bible: dict, episode: dict, form: str = "storytell") -> dict:
        shapes = {
            "conversation": "FORME CONVERSATION : fountain = répliques NOM : texte seulement.",
            "voix_off": "FORME VOIX OFF : VOIX OFF : « … » puis l'image.",
            "rencontre": "FORME RENCONTRE : deux présences, geste, réplique.",
            "storytell": "FORME STORYTELL : narration 3e personne.",
        }
        return self.text.generate_json(
            system=(
                "Tu écris UN épisode. JSON : {\"fountain\": str, \"scenes\": []}. "
                f"{shapes.get(form, shapes['storytell'])} Respecte la bible. Français."
            ),
            user=f"FORME:{form}\nCONCEPT:\n{concept}\n\nBIBLE:\n{bible}\n\nEPISODE:\n{episode}",
        )
