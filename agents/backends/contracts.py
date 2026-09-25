"""Stable backend contracts for StudioBililingi model providers."""

from __future__ import annotations

from typing import Protocol


class TextBackend(Protocol):
    provider_id: str
    def generate_json(self, system: str, user: str) -> dict: ...


class ImageBackend(Protocol):
    provider_id: str
    def generate(self, prompt: str, refs: list[str] | None = None, *, project_key: str | None = None) -> str: ...


class VideoBackend(Protocol):
    provider_id: str
    def render(self, prompt: str, **kwargs) -> str: ...


class AudioBackend(Protocol):
    provider_id: str
