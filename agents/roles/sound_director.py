from __future__ import annotations

from agents.backends import get_text


class SoundDirector:
    """Plans non-dialogue sound, ambience and music around locked spoken audio."""

    role = "sound_director"

    def __init__(self):
        self.text = get_text(role=self.role)

    def direct(self, *, beat: dict, audio_contract: dict, scene: dict | None = None) -> dict:
        result = self.text.generate_json(
            system=(
                "Tu es le Sound Director de StudioBililingi. Les dialogues, narrations et voix canoniques sont verrouillés "
                "et ne doivent jamais être modifiés. Planifie seulement ambiances, bruitages, musique, silences et niveaux. "
                "Réponds uniquement en JSON avec ambience, sfx, music, silence, mix_notes, warnings."
            ),
            user=f"BEAT:\n{beat}\n\nAUDIO CONTRACT:\n{audio_contract}\n\nSCENE:\n{scene or {}}",
        )
        result.setdefault("ambience", [])
        result.setdefault("sfx", [])
        result.setdefault("music", [])
        result.setdefault("silence", [])
        result.setdefault("mix_notes", [])
        result.setdefault("warnings", [])
        return result
