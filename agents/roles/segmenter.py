from __future__ import annotations

from agents.backends import get_text


class BeatSegmenter:
    """Turns a script into visually renderable 6-8 second beats."""

    role = "beat_segmenter"
    target_words = 24

    def __init__(self):
        self.text = get_text()

    def segment(self, script: str, *, form: str = "storytell", bible: dict | None = None, feedback: str = "") -> dict:
        mode_rules = {
            "conversation": (
                "CONVERSATION: chaque beat contenant une parole doit fournir speaker_id avec l'id CANONIQUE exact "
                "du personnage qui parle, présent dans la bible. Dans text ET dialogue, écris aussi "
                "NOM_DU_PERSONNAGE : réplique; jamais une réplique anonyme. character_ids désigne tous les personnages "
                "visibles, tandis que speaker_id désigne uniquement le locuteur principal. Si plusieurs personnages "
                "parlent, crée des beats distincts à une pause naturelle afin qu'un beat ait au maximum un speaker_id. "
                "Ne transforme jamais le dialogue en narration. "
                "Fusionne une micro-réplique avec l'action ou la réaction visuelle adjacente dans la même scène."
            ),
            "voix_off": "VOIX OFF: conserve explicitement la voix off dans dialogue et décris séparément l'image.",
            "rencontre": "RENCONTRE: privilégie gestes, regards, silences et répliques courtes entre les deux présences.",
            "storytell": "STORYTELL: conserve la narration tout en créant une action visuelle précise par beat.",
        }
        return self.text.generate_json(
            system=(
                "Tu es le segmenter vidéo de StudioBililingi. Ne découpe PAS mécaniquement tous les 24 mots. "
                "Un beat est une unité visuelle cohérente de 6 à 8 secondes avec une seule intention dramatique. "
                "Ne crée jamais un clip autonome pour une micro-réplique ou réaction comme Non, Allô, Oui, un nom "
                "ou une phrase de quelques mots: fusionne-la avec l'action, la réaction ou la réplique adjacente dans "
                "la même scène. La cible de production est 24 mots par beat. Pour chaque beat, vise 20 à 28 mots; "
                "ne dépasse jamais 32 mots. Si le contenu dépasse 32 mots, crée plusieurs beats en conservant le même "
                "scene_index et la continuité. Un beat de moins de 12 mots doit être fusionné avec un voisin compatible, "
                "sauf silence/action visuelle qui remplit réellement 6 à 8 secondes. Une longue réplique doit être "
                "découpée à une pause naturelle avec une "
                "action ou réaction visible pour chaque partie. Respecte les changements de scène, de lieu, de locuteur "
                "et d'action. Retourne JSON {\"beats\": [...]} uniquement. Chaque beat doit fournir: "
                "text, scene_index, scene_heading, scene_summary, location_id, time_of_day, lighting, "
                "character_ids, speaker_id, prop_ids, camera {shot_size, angle, move, lens}, emotion, dialogue, "
                "continuity, duration_seconds, video_prompt, negative_prompt, backend. "
                "Utilise uniquement les ids de personnages/lieux/objets présents dans la bible quand ils existent. "
                "video_prompt décrit exactement ce qui doit être visible à l'écran, qui parle, la réaction visible "
                "et l'identité/continuité à préserver. "
                f"{mode_rules.get(form, mode_rules['storytell'])}"
            ),
            user=(
                f"MODE: {form}\n\nBIBLE:\n{bible or {}}\n\n"
                f"CORRECTIONS OBLIGATOIRES DE LA PASSE PRECEDENTE:\n{feedback or 'Aucune'}\n\n"
                f"SCRIPT:\n{script}"
            ),
        )
