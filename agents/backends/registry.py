"""Swap providers without changing agent roles."""

from __future__ import annotations

import os

from .google import GoogleAudioBackend, GoogleImageBackend, GoogleTextBackend, GoogleVideoBackend
from .stub import StubAudioBackend, StubImageBackend, StubTextBackend, StubVideoBackend


def _use_stubs() -> bool:
    return os.getenv("STUDIO_BACKENDS", "stub") == "stub"


def get_text():
    return StubTextBackend() if _use_stubs() else GoogleTextBackend()


def get_image():
    return StubImageBackend() if _use_stubs() else GoogleImageBackend()


def get_video():
    return StubVideoBackend() if _use_stubs() else GoogleVideoBackend()


def get_audio():
    return StubAudioBackend() if _use_stubs() else GoogleAudioBackend()
