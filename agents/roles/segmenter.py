from __future__ import annotations

from agents.backends import get_text


class BeatSegmenter:
    """Turns a script into visually renderable 6-8 second beats."""

    role = "beat_segmenter"
    target_words = 24

    def __init__(self):
        self.text = get_text()

    def segment(self, script: str, *, form: str = "storytell", bible: dict | None = None) -> dict:
        mode_rules = {
            "conversation": (
                "CONVERSATION: conserve le locuteur et sa réplique. Ne transforme jamais le dialogue en narration. "
                "Un beat peut contenir une courte réplique et la réaction visuelle correspondante."
            ),
            "voix_off": "VOIX OFF: conserve explicitement la voix off dans dialogue et décris séparément l'image.",
            "rencontre": "RENCONTRE: privilégie gestes, regards, silences et répliques courtes entre les deux présences.",
            "storytell": "STORYTELL: conserve la narration tout en créant une action visuelle précise par beat.",
        }
        return self.text.generate_json(
            system=(
                "Tu es le segmenter vidéo de StudioBililingi. Ne découpe PAS mécaniquement tous les 24 mots. "
                "Un beat est une unité visuelle cohérente de 6 à 8 secondes avec une seule intention dramatique. "
                "~24 mots est une cible, jamais une obligation. Respecte les changements de scène, de lieu, de locuteur "
                "et d'action. Retourne JSON {\"beats\": [...]} uniquement. Chaque beat doit fournir: "
                "text, scene_index, scene_heading, scene_summary, location_id, time_of_day, lighting, "
                "character_ids, prop_ids, camera {shot_size, angle, move, lens}, emotion, dialogue, "
                "continuity, duration_seconds, video_prompt, negative_prompt, backend. "
                "Utilise uniquement les ids de personnages/lieux/objets présents dans la bible quand ils existent. "
                "video_prompt décrit ce qui doit être visible à l'écran et l'identité/continuité à préserver. "
                f"{mode_rules.get(form, mode_rules['storytell'])}"
            ),
            user=f"MODE: {form}\n\nBIBLE:\n{bible or {}}\n\nSCRIPT:\n{script}",
        )
