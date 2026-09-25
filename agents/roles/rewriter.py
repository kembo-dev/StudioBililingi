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
        self.text = get_text(role=self.role)

    def rewrite(self, *, beat: str, instruction: str, concept: str, bible: dict, form: str = "storytell") -> dict:
        shape = FORMS.get(form, FORMS["storytell"])
        return self.text.generate_json(
            system=(
                "Tu es script doctor et réalisateur. Tu dois RAISONNER le beat avant de proposer une réécriture, "
                "sans exposer ton raisonnement interne. JSON strict : "
                "{\"text\": str, \"word_count\": int, \"video_prompt\": str, \"form\": str, "
                "\"intent\": str, \"continuity\": str, \"performance\": str, \"camera\": str, \"sound\": str}. "
                f"{shape} Le résultat doit être professionnel, filmable et précis. "
                "Ne compresse pas mécaniquement à ~24 mots : conserve toute information narrative et toute réplique "
                "nécessaire au sens. Identifie implicitement l'objectif dramatique, le sujet qui agit/parle, la réaction, "
                "la continuité avec le beat source, puis construis une mise en scène claire. "
                "En conversation, préserve mot pour mot les répliques canoniques déjà présentes sauf si l'instruction "
                "demande explicitement de modifier le texte. Ne transforme jamais une description visuelle en dialogue. "
                "video_prompt doit décrire cadrage, mouvement caméra, jeu, blocking, lumière, ambiance et son, "
                "sans inventer de personnages, lieux, accessoires ou événements absents de la Bible/du beat. "
                "Reste strictement dans la Bible et le concept."
            ),
            user=(
                f"FORME: {form}\nINSTRUCTION DE MISE EN SCÈNE:\n{instruction}\n\n"
                f"BEAT CANONIQUE À PRÉSERVER:\n{beat}\n\nCONCEPT:\n{concept}\n\nBIBLE:\n{bible}\n\n"
                "Retourne une proposition de beat qui améliore le rendu cinématographique sans casser l'histoire."
            ),
        )
