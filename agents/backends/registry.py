"""Config-driven provider registry. Agent roles never depend on a concrete vendor."""

from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv

_REPO_DIR = Path(__file__).resolve().parents[2]
load_dotenv(_REPO_DIR / ".env")
load_dotenv(_REPO_DIR / "backend" / ".env")

from .google import GoogleAudioBackend, GoogleImageBackend, GoogleTextBackend, GoogleVideoBackend
from .ollama import OllamaTextBackend
from .stub import StubAudioBackend, StubImageBackend, StubTextBackend, StubVideoBackend

_CONFIG_PATH = Path(os.getenv("STUDIO_MODELS_CONFIG", str(_REPO_DIR / "config" / "models.json")))


def _config() -> dict:
    try:
        return json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid Studio model config {_CONFIG_PATH}: {exc}") from exc


def _legacy_choice(modality: str) -> str:
    specific = os.getenv(f"STUDIO_{modality.upper()}_BACKEND", "").strip().lower()
    if specific:
        return specific
    return os.getenv("STUDIO_BACKENDS", "").strip().lower()


def _selection(modality: str, role: str | None = None) -> dict:
    cfg = _config()
    selected = dict((cfg.get("defaults") or {}).get(modality) or {})
    role_cfg = (cfg.get("roles") or {}).get(role or "") or {}
    override = role_cfg.get(modality)
    if isinstance(override, str):
        selected["provider"] = override
    elif isinstance(override, dict):
        selected.update(override)
    elif role_cfg.get("provider") and modality == "text":
        selected.update({k: v for k, v in role_cfg.items() if k in {"provider", "model"}})

    # Existing deployments keep working: explicit env backend choices override config.
    legacy = _legacy_choice(modality)
    if legacy:
        selected["provider"] = legacy
    return selected


def _provider_config(provider: str) -> dict:
    return dict((_config().get("providers") or {}).get(provider) or {})


def get_text(role: str | None = None):
    choice = _selection("text", role)
    provider = str(choice.get("provider") or "stub").lower()
    model = choice.get("model")
    if provider == "google":
        backend = GoogleTextBackend()
        if model:
            backend.model_override = str(model)
        return backend
    if provider == "ollama":
        cfg = _provider_config("ollama")
        text_cfg = cfg.get("text") or {}
        return OllamaTextBackend(
            model=str(model or text_cfg.get("model") or os.getenv("OLLAMA_MODEL", "qwen3:14b")),
            base_url=str(cfg.get("base_url") or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")),
            timeout=int(text_cfg.get("timeout_seconds") or os.getenv("OLLAMA_TIMEOUT_SECONDS", "180")),
        )
    if provider == "stub":
        return StubTextBackend()
    raise ValueError(f"Unknown text provider: {provider}")


def get_image(role: str | None = None):
    choice = _selection("image", role)
    provider = str(choice.get("provider") or "stub").lower()
    if provider == "google":
        backend = GoogleImageBackend()
        if choice.get("model"):
            backend.model_override = str(choice["model"])
        return backend
    if provider == "stub":
        return StubImageBackend()
    raise ValueError(f"Unknown image provider: {provider}")


def get_video(role: str | None = None):
    choice = _selection("video", role)
    provider = str(choice.get("provider") or "stub").lower()
    if provider == "google":
        backend = GoogleVideoBackend()
        if choice.get("model"):
            backend.model_override = str(choice["model"])
        return backend
    if provider == "stub":
        return StubVideoBackend()
    raise ValueError(f"Unknown video provider: {provider}")


def get_audio(role: str | None = None):
    choice = _selection("audio", role)
    provider = str(choice.get("provider") or "stub").lower()
    if provider == "google":
        return GoogleAudioBackend()
    if provider == "stub":
        return StubAudioBackend()
    raise ValueError(f"Unknown audio provider: {provider}")
