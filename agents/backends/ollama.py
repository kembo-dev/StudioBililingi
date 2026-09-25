"""Ollama text backend. Uses only the Python standard library."""

from __future__ import annotations

import json
import os
from urllib import error, request

from .google import _parse_json


class OllamaTextBackend:
    provider_id = "ollama"

    def __init__(self, *, model: str | None = None, base_url: str | None = None, timeout: int | None = None):
        self.model = model or os.getenv("OLLAMA_MODEL", "qwen3:14b")
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")).rstrip("/")
        self.timeout = timeout or int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "180"))

    def generate_json(self, system: str, user: str) -> dict:
        payload = json.dumps({
            "model": self.model,
            "stream": False,
            "format": "json",
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }).encode("utf-8")
        req = request.Request(
            f"{self.base_url}/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=self.timeout) as response:
                raw = json.loads(response.read().decode("utf-8"))
        except error.URLError as exc:
            raise RuntimeError(f"Ollama unavailable at {self.base_url}: {exc}") from exc
        content = ((raw.get("message") or {}).get("content") or "").strip()
        result = _parse_json(content)
        result["_provider"] = self.provider_id
        result["_model"] = self.model
        return result
