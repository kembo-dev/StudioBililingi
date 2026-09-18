from __future__ import annotations

from agents.backends import get_text

FORMS = {
    "storytell": "Forme STORYTELL : narration filmable à la 3e personne. Pas de répliques.",
    "voix_off": "Forme VOIX OFF : une phrase VOIX OFF entre guillemets, puis l'image.",
    "conversation": "Forme CONVERSATION : répliques NOM : texte. Au moins deux tours.",
    "rencontre": "Forme RENCONTRE : deux présences, un geste, une réplique, une réaction.",
}


class BeatRewriter:
    role = "beat_rewriter"

    def __init__(self):
        self.text = get_text()

    def rewrite(self, *, beat: str, instruction: str, concept: str, bible: dict, form: str = "storytell") -> dict:
        shape = FORMS.get(form, FORMS["storytell"])
        return self.text.generate_json(
            system=(
                "Tu réécris UN beat. JSON : {\"text\": str, \"word_count\": int, \"video_prompt\": str, \"form\": str}. "
                f"~24 mots. {shape} Applique l'instruction. Reste dans la bible."
            ),
            user=f"FORME: {form}\nINSTRUCTION:\n{instruction}\n\nBEAT:\n{beat}\n\nCONCEPT:\n{concept}\n\nBIBLE:\n{bible}",
        )
