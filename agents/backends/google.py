"""Google defaults: Gemini text, Nano Banana images, Veo video, Lyria/TTS audio.

Implementations are wired later. Signatures stay stable so roles do not change.
"""

from __future__ import annotations


class GoogleTextBackend:
    provider_id = "google-gemini"

    def generate_json(self, system: str, user: str) -> dict:
        raise NotImplementedError("Gemini client not wired yet")


class GoogleImageBackend:
    provider_id = "google-nano-banana"

    def generate(self, prompt: str, refs: list[str] | None = None) -> str:
        raise NotImplementedError("Nano Banana / Gemini Image not wired yet")


class GoogleVideoBackend:
    provider_id = "google-veo-3.1"

    def render(
        self,
        prompt: str,
        *,
        start_frame: str | None = None,
        end_frame: str | None = None,
        ingredients: list[str] | None = None,
        duration_seconds: float = 8,
        aspect_ratio: str = "16:9",
    ) -> str:
        raise NotImplementedError("Veo 3.1 / Omni Flash not wired yet")


class GoogleAudioBackend:
    provider_id = "google-lyria-tts"

    def score(self, prompt: str, duration_seconds: float = 30) -> str:
        raise NotImplementedError("Lyria not wired yet")

    def speak(self, text: str, voice_id: str) -> str:
        raise NotImplementedError("Gemini TTS not wired yet")
