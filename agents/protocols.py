from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class TextBackend(Protocol):
    provider_id: str

    def generate_json(self, system: str, user: str) -> dict: ...


@runtime_checkable
class ImageBackend(Protocol):
    provider_id: str

    def generate(self, prompt: str, refs: list[str] | None = None) -> str: ...


@runtime_checkable
class VideoBackend(Protocol):
    provider_id: str

    def render(
        self,
        prompt: str,
        *,
        start_frame: str | None = None,
        end_frame: str | None = None,
        ingredients: list[str] | None = None,
        duration_seconds: float = 8,
        aspect_ratio: str = "16:9",
    ) -> str: ...


@runtime_checkable
class AudioBackend(Protocol):
    provider_id: str

    def score(self, prompt: str, duration_seconds: float = 30) -> str: ...

    def speak(self, text: str, voice_id: str) -> str: ...
