from __future__ import annotations

from agents.backends import get_text


class BeatSegmenter:
    """Turns a script into narrative beats constrained by the locked Scene Plan."""

    role = "beat_segmenter"
    target_words = 24

    def __init__(self):
        self.text = get_text()

    def segment(self, script: str, *, form: str = "storytell", bible: dict | None = None, feedback: str = "", narrative_contract: dict | None = None, scene_plan: list[dict] | None = None) -> dict:
        mode_rules = {
            "conversation": (
                "CONVERSATION: chaque beat contenant une parole doit fournir speaker_id avec l'id CANONIQUE exact "
                "du personnage qui parle, présent dans la bible. Dans text ET dialogue, écris aussi "
                "NOM_DU_PERSONNAGE : réplique; jamais une réplique anonyme. character_ids désigne tous les personnages "
                "visibles, tandis que speaker_id désigne uniquement le locuteur principal. Si plusieurs personnages "
                "parlent, crée des beats distincts à une pause naturelle afin qu'un beat ait au maximum un speaker_id. "
                "Ne transforme jamais le dialogue en narration. Ne coupe JAMAIS une phrase ou une réplique au milieu: "
                "chaque beat doit se terminer à une vraie fin de phrase ou à une pause de dialogue grammaticalement complète. "
                "Si une phrase dépasse la limite, réécris-la en plusieurs phrases naturelles avant de créer les beats. "
                "Fusionne une micro-réplique avec l'action ou la réaction visuelle adjacente dans la même scène."
            ),
            "voix_off": (
                "VOIX OFF: sépare strictement narration et dialogue personnage. Mets la voix off externe dans narration. "
                "Mets uniquement les paroles réellement prononcées par un personnage dans dialogue avec speaker_id canonique. "
                "Un même beat peut contenir narration ET dialogue si les deux sont nécessaires à la même unité narrative."
            ),
            "rencontre": "RENCONTRE: privilégie gestes, regards, silences et répliques courtes entre les deux présences.",
            "storytell": "STORYTELL: conserve la narration tout en créant une action visuelle précise par beat.",
        }
        return self.text.generate_json(
            system=(
                "Tu es le segmenter vidéo de StudioBililingi. Ne découpe PAS mécaniquement tous les 24 mots. "
                "Un beat est une unité NARRATIVE cohérente avec une seule intention dramatique; ce n'est pas un clip vidéo. "
                "Ne crée jamais un clip autonome pour une micro-réplique ou réaction comme Non, Allô, Oui, un nom "
                "ou une phrase de quelques mots: fusionne-la avec l'action, la réaction ou la réplique adjacente dans "
                "la même scène. La longueur en mots est seulement informative: conserve ensemble une action, une intention "
                "ou un échange cohérent, même au-delà de 24/32 mots. Ne découpe jamais un beat uniquement pour satisfaire "
                "une limite vidéo: les SHOTS seront créés ensuite comme unités filmables. Une longue réplique doit être "
                "découpée à une pause naturelle avec une "
                "action ou réaction visible pour chaque partie. Respecte les changements de scène, de lieu, de locuteur "
                "et d'action. Avant de répondre, parcours chaque scène du SCENE PLAN et construis ses beats uniquement "
                "avec les event_ids autorisés pour CETTE scène; ne déplace jamais un EVxx vers une autre scène pendant une correction. "
                "Retourne JSON {\"beats\": [...]} uniquement. Chaque beat doit fournir: "
                "text, event_id, scene_index, scene_heading, scene_summary, location_id, time_of_day, lighting, "
                "character_ids, speaker_id, prop_ids, camera {shot_size, angle, move, lens}, emotion, narration, dialogue, "
                "continuity, duration_seconds, video_prompt, negative_prompt, backend. "
                "Utilise uniquement les ids de personnages/lieux/objets présents dans la bible quand ils existent. "
                "SCENE PLAN LOCK: le SCENE PLAN est déjà validé et canonique. Chaque beat doit reprendre exactement un scene_index existant, son location_id et son time_of_day. Ne crée, ne fusionne, ne déplace et ne renumérote aucune scène. "
                "event_id doit être l'identifiant EVxx exact du NARRATIVE CONTRACT correspondant à l'information narrative réellement avancée par le beat et doit être autorisé par event_ids de la scène choisie. Plusieurs beats peuvent partager un event_id uniquement si chacun montre une étape visuelle distincte nécessaire; n'ajoute jamais des beats philosophiques ou moraux qui répètent la même information pour remplir la durée. DUREE VERROUILLEE: pour chaque scène, la somme exacte des duration_seconds de ses beats doit viser target_seconds du SCENE PLAN (tolérance maximale 15%). Ne suppose pas 8 secondes par beat: attribue 3 à 8 secondes selon l'action/réplique. Pour une scène de 60 secondes, ne produis pas 14 beats de 8 secondes. Préfère fusionner les informations compatibles et conserver uniquement les unités réellement filmables. "
                "video_prompt décrit exactement ce qui doit être visible à l'écran, qui parle, la réaction visible "
                "et l'identité/continuité à préserver. "
                f"{mode_rules.get(form, mode_rules['storytell'])}"
            ),
            user=(
                f"MODE: {form}\n\nBIBLE:\n{bible or {}}\n\nNARRATIVE CONTRACT:\n{narrative_contract or {}}\n\nSCENE PLAN VERROUILLE:\n{scene_plan or []}\n\n"
                f"CORRECTIONS OBLIGATOIRES DE LA PASSE PRECEDENTE:\n{feedback or 'Aucune'}\n\n"
                f"SCRIPT:\n{script}"
            ),
        )
