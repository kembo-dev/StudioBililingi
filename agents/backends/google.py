from __future__ import annotations

import json
import os
import re
import time
import uuid
from pathlib import Path


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



def _is_resource_exhausted(exc: Exception) -> bool:
    text = str(exc)
    return "429" in text and ("RESOURCE_EXHAUSTED" in text or "Resource exhausted" in text)


def _with_quota_retry(call):
    """Retry short-lived Vertex capacity/quota errors with bounded backoff."""
    attempts = max(1, int(os.getenv("GOOGLE_QUOTA_RETRIES", "3")))
    base = max(1.0, float(os.getenv("GOOGLE_QUOTA_RETRY_SECONDS", "4")))
    for attempt in range(attempts):
        try:
            return call()
        except Exception as exc:
            if not _is_resource_exhausted(exc) or attempt + 1 >= attempts:
                raise
            time.sleep(base * (2 ** attempt))


def _client():
    """Create a process-local GenAI client safe for Celery prefork workers."""
    from google import genai

    use_vertex = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "").lower() in {"1", "true", "yes"}
    if use_vertex:
        return genai.Client(
            vertexai=True,
            project=os.getenv("GOOGLE_CLOUD_PROJECT"),
            location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
        )
    api_key = os.getenv("GEMINI_API_KEY", "").strip() or os.getenv("GOOGLE_API_KEY", "").strip()
    return genai.Client(api_key=api_key or None)


def _media_root() -> Path:
    raw = os.getenv("STUDIO_MEDIA_DIR", "").strip()
    path = Path(raw) if raw else Path(__file__).resolve().parents[2] / "backend" / "media"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _safe_media_segment(value: str | None, fallback: str = "unassigned") -> str:
    value = re.sub(r"[^a-zA-Z0-9._-]+", "-", str(value or "").strip()).strip("-._")
    return value or fallback


def _save_bytes(folder: str, data: bytes, suffix: str, *, project_key: str | None = None) -> str:
    relative = Path(folder)
    if project_key:
        relative /= _safe_media_segment(project_key)
    directory = _media_root() / relative
    directory.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}{suffix}"
    (directory / name).write_bytes(data)
    return f"/media/{relative.as_posix()}/{name}"


def _usable(uri: str | None) -> bool:
    return bool(uri) and uri.startswith(("http://", "https://", "gs://", "/media/"))


def _local_media_path(uri: str | None) -> Path | None:
    if not uri or not str(uri).startswith("/media/"):
        return None
    relative = str(uri)[len("/media/"):]
    path = (_media_root() / relative).resolve()
    root = _media_root().resolve()
    try:
        path.relative_to(root)
    except ValueError:
        return None
    return path if path.exists() else None


def _video_reference_image(types, uri: str):
    """Convert a Studio asset URI into a real GenAI Image object."""
    local = _local_media_path(uri)
    if local:
        return types.Image.from_file(location=str(local))
    if str(uri).startswith("gs://"):
        import mimetypes
        mime = mimetypes.guess_type(str(uri))[0] or "image/png"
        return types.Image(gcs_uri=str(uri), mime_type=mime)
    return None


class GoogleTextBackend:
    provider_id = "google-gemini"

    def generate_json(self, system: str, user: str) -> dict:
        from google.genai import types

        model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        client = _client()
        try:
            response = _with_quota_retry(lambda: client.models.generate_content(
                model=model,
                contents=user,
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    response_mime_type="application/json",
                    temperature=0.7,
                ),
            ))
        finally:
            client.close()
        payload = _parse_json(response.text or "")
        payload["_provider"] = self.provider_id
        payload["_model"] = model
        return payload


class GoogleImageBackend:
    provider_id = "google-nano-banana"

    def generate(self, prompt: str, refs: list[str] | None = None, *, project_key: str | None = None) -> str:
        from google.genai import types

        model = os.getenv("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")
        client = _client()
        try:
            contents = [prompt]
            for uri in (refs or []):
                image = _video_reference_image(types, uri) if _usable(uri) else None
                if image is not None:
                    contents.append(image)
            response = _with_quota_retry(lambda: client.models.generate_content(
                model=model,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                ),
            ))
            parts = list(getattr(response, "parts", None) or [])
            if not parts:
                for candidate in getattr(response, "candidates", None) or []:
                    content = getattr(candidate, "content", None)
                    parts.extend(getattr(content, "parts", None) or [])

            for part in parts:
                inline = getattr(part, "inline_data", None) or getattr(part, "inlineData", None)
                data = getattr(inline, "data", None) if inline else None
                mime = getattr(inline, "mime_type", None) or getattr(inline, "mimeType", None) or "image/png"
                if data:
                    if isinstance(data, str):
                        import base64
                        data = base64.b64decode(data)
                    suffix = ".jpg" if "jpeg" in mime else ".png"
                    return _save_bytes("refs", data, suffix, project_key=project_key)

            text = getattr(response, "text", "") or ""
            raise RuntimeError(
                f"Gemini Image returned no image bytes ({model}). "
                f"Response text: {text[:200]!r}"
            )
        finally:
            client.close()


class GoogleVideoBackend:
    provider_id = "google-veo-3.1"

    def extract_reference_frame(self, video_uri: str, *, project_key: str | None = None) -> str:
        """Extract the first stable frame of a previous local take for visual re-adjustment."""
        import subprocess

        source = _local_media_path(video_uri)
        if source is None:
            raise ValueError("Previous take is not available as a local Studio video")
        relative = Path("take-frames")
        if project_key:
            relative /= _safe_media_segment(project_key)
        directory = _media_root() / relative
        directory.mkdir(parents=True, exist_ok=True)
        output = directory / f"{uuid.uuid4().hex}.jpg"
        command = [
            "ffmpeg", "-y", "-ss", "0.15", "-i", str(source),
            "-frames:v", "1", "-q:v", "2", str(output),
        ]
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=30)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise RuntimeError(f"Unable to extract previous take frame: {exc}") from exc
        if result.returncode != 0 or not output.exists():
            raise RuntimeError(
                "Unable to extract previous take frame: " + (result.stderr or "")[-500:]
            )
        return f"/media/{relative.as_posix()}/{output.name}"

    def render(
        self,
        prompt: str,
        *,
        start_frame=None,
        end_frame=None,
        ingredients=None,
        duration_seconds=8,
        aspect_ratio="16:9",
        project_key: str | None = None,
    ) -> str:
        from google.genai import types

        model = os.getenv("VEO_MODEL", "veo-3.1-generate-001")
        usable = [uri for uri in (ingredients or []) if _usable(uri)]
        text = prompt

        # Veo 3.1 accepts at most three asset reference images. Keep selection
        # deterministic: callers order canonical refs by priority and stable UID.
        max_reference_images = max(1, min(3, int(os.getenv("VEO_MAX_REFERENCE_IMAGES", "3"))))
        selected_uris = usable[:max_reference_images]

        # Real visual conditioning: pass Studio refs to Veo as reference images
        # instead of merely mentioning their filesystem URI in the prompt.
        reference_images = []
        for uri in selected_uris:
            image = _video_reference_image(types, uri)
            if image is not None:
                reference_images.append(
                    types.VideoGenerationReferenceImage(
                        image=image,
                        reference_type="asset",
                    )
                )

        start_image = _video_reference_image(types, start_frame) if _usable(start_frame) else None
        end_image = _video_reference_image(types, end_frame) if _usable(end_frame) else None

        config_kwargs = {"aspect_ratio": aspect_ratio, "number_of_videos": 1}
        raw_duration = max(4.0, min(8.0, float(duration_seconds or 8)))
        # Veo text-to-video accepts discrete clip lengths, not arbitrary seconds.
        # Choose the nearest supported duration and prefer the longer option on ties.
        supported_durations = (4, 6, 8)
        requested_duration = min(supported_durations, key=lambda value: (abs(value - raw_duration), -value))
        config_kwargs["duration_seconds"] = requested_duration

        # Veo reference-images mode cannot be mixed with image/last-frame mode.
        if reference_images:
            config_kwargs["reference_images"] = reference_images
        elif end_image is not None:
            config_kwargs["last_frame"] = end_image

        try:
            config = types.GenerateVideosConfig(**config_kwargs)
        except (TypeError, ValueError):
            # Keep compatibility with older installed SDKs.
            config_kwargs.pop("duration_seconds", None)
            config_kwargs.pop("reference_images", None)
            config_kwargs.pop("last_frame", None)
            config = types.GenerateVideosConfig(**config_kwargs)

        client = _client()
        try:
            if reference_images:
                kwargs = {
                    "model": model,
                    "source": types.GenerateVideosSource(prompt=text),
                    "config": config,
                }
            elif start_image is not None:
                kwargs = {
                    "model": model,
                    "source": types.GenerateVideosSource(prompt=text, image=start_image),
                    "config": config,
                }
            else:
                kwargs = {
                    "model": model,
                    "source": types.GenerateVideosSource(prompt=text),
                    "config": config,
                }
            operation = _with_quota_retry(lambda: client.models.generate_videos(**kwargs))
            timeout = int(os.getenv("VEO_TIMEOUT_SECONDS", "600"))
            started = time.time()
            while not getattr(operation, "done", False):
                if time.time() - started > timeout:
                    raise TimeoutError(f"Veo timed out after {timeout}s")
                time.sleep(8)
                operation = client.operations.get(operation)

            response = getattr(operation, "response", None) or getattr(operation, "result", None)
            videos = getattr(response, "generated_videos", None) or []
            if not videos:
                filtered_count = getattr(response, "rai_media_filtered_count", None) if response else None
                filtered_reasons = getattr(response, "rai_media_filtered_reasons", None) if response else None
                operation_error = getattr(operation, "error", None)
                details = []
                if filtered_count:
                    details.append(f"filtered_count={filtered_count}")
                if filtered_reasons:
                    details.append("filtered_reasons=" + "; ".join(str(reason) for reason in filtered_reasons))
                if operation_error:
                    details.append(f"operation_error={operation_error}")
                suffix = f": {' | '.join(details)}" if details else ""
                raise RuntimeError(f"Veo returned no video ({model}){suffix}")
            video = videos[0]
            video_file = getattr(video, "video", None)
            data = getattr(video_file, "video_bytes", None) if video_file else None
            if data:
                if isinstance(data, str):
                    import base64
                    data = base64.b64decode(data)
                return _save_bytes("clips", data, ".mp4", project_key=project_key)
            uri = getattr(video_file, "uri", None) if video_file else getattr(video, "uri", None)
            if uri:
                return uri
            raise RuntimeError("Veo video had neither bytes nor uri")
        finally:
            client.close()


class GoogleAudioBackend:
    provider_id = "google-lyria-tts"

    def score(self, prompt: str, duration_seconds: float = 30) -> str:
        raise NotImplementedError("Lyria not wired yet")

    def speak(self, text: str, voice_id: str) -> str:
        raise NotImplementedError("Gemini TTS not wired yet")
