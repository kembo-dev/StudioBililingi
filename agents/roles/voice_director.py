from __future__ import annotations

from agents.backends import get_text


class VoiceDirector:
    """Audits and directs narrator/character voice continuity before rendering."""

    role = "voice_director"

    def __init__(self):
        self.text = get_text(role=self.role)

    def direct(self, *, beat: dict, audio_contract: dict, speaker: dict | None = None) -> dict:
        result = self.text.generate_json(
            system=(
                "Tu es le Voice Director de StudioBililingi. Tu ne modifies jamais le texte canonique. "
                "Tu vérifies et diriges langue, narrateur, speaker, voix, accent, débit, tonalité et séparation "
                "narration/dialogue. Réponds uniquement en JSON avec: speech_mode, narrator_direction, "
                "speaker_direction, language_lock, errors, warnings. Si une donnée manque, signale-la sans l'inventer."
            ),
            user=f"BEAT:\n{beat}\n\nAUDIO CONTRACT:\n{audio_contract}\n\nSPEAKER:\n{speaker or {}}",
        )
        result.setdefault("errors", [])
        result.setdefault("warnings", [])
        return result
