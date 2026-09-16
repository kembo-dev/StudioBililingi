from __future__ import annotations

import json
import os
import re


def _parse_json(text: str) -> dict:
    raw = (text or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?", "", raw, flags=re.I).strip()
        raw = re.sub(r"```$", "", raw).strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"(\{.*\}|\[.*\])", raw, flags=re.S)
        if not match:
            raise
        data = json.loads(match.group(1))
    if isinstance(data, list):
        return {"beats": data}
    if not isinstance(data, dict):
        return {"value": data}
    return data


class GoogleTextBackend:
    provider_id = "google-gemini"

    def generate_json(self, system: str, user: str) -> dict:
        from google import genai
        from google.genai import types

        use_vertex = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "").lower() in {"1", "true", "yes"}
        kwargs: dict = {}
        if use_vertex:
            kwargs = {
                "vertexai": True,
                "project": os.getenv("GOOGLE_CLOUD_PROJECT"),
                "location": os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
            }
        client = genai.Client(**kwargs)
        model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        response = client.models.generate_content(
            model=model,
            contents=user,
            config=types.GenerateContentConfig(
                system_instruction=system,
                response_mime_type="application/json",
                temperature=0.7,
            ),
        )
        payload = _parse_json(response.text or "")
        payload["_provider"] = self.provider_id
        payload["_model"] = model
        return payload


class GoogleImageBackend:
    provider_id = "google-nano-banana"

    def generate(self, prompt: str, refs: list[str] | None = None) -> str:
        raise NotImplementedError("Nano Banana / Gemini Image not wired yet")


class GoogleVideoBackend:
    provider_id = "google-veo-3.1"

    def render(self, prompt: str, *, start_frame=None, end_frame=None, ingredients=None, duration_seconds=8, aspect_ratio="16:9") -> str:
        raise NotImplementedError("Veo 3.1 / Omni Flash not wired yet")


class GoogleAudioBackend:
    provider_id = "google-lyria-tts"

    def score(self, prompt: str, duration_seconds: float = 30) -> str:
        raise NotImplementedError("Lyria not wired yet")

    def speak(self, text: str, voice_id: str) -> str:
        raise NotImplementedError("Gemini TTS not wired yet")
