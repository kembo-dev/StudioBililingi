"""Swap providers without changing agent roles."""

from __future__ import annotations

import os

from .google import GoogleAudioBackend, GoogleImageBackend, GoogleTextBackend, GoogleVideoBackend
from .stub import StubAudioBackend, StubImageBackend, StubTextBackend, StubVideoBackend


def _choice(modality: str) -> str:
    specific = os.getenv(f"STUDIO_{modality}_BACKEND", "").strip().lower()
    if specific:
        return specific
    return os.getenv("STUDIO_BACKENDS", "stub").strip().lower()


def get_text():
    return GoogleTextBackend() if _choice("TEXT") == "google" else StubTextBackend()


def get_image():
    return GoogleImageBackend() if _choice("IMAGE") == "google" else StubImageBackend()


def get_video():
    return GoogleVideoBackend() if _choice("VIDEO") == "google" else StubVideoBackend()


def get_audio():
    return GoogleAudioBackend() if _choice("AUDIO") == "google" else StubAudioBackend()
