"""Local stand-ins so the foundation runs without API keys."""


class StubTextBackend:
    provider_id = "stub-text"

    def generate_json(self, system: str, user: str) -> dict:
        return {
            "provider": self.provider_id,
            "note": "stub — no model called",
            "system_preview": system[:80],
            "user_preview": user[:80],
        }


class StubImageBackend:
    provider_id = "stub-image"

    def generate(self, prompt: str, refs: list[str] | None = None) -> str:
        return f"stub://image/{abs(hash(prompt))}"


class StubVideoBackend:
    provider_id = "stub-video"

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
        refs = ingredients or []
        token = abs(hash((prompt, start_frame or "", tuple(refs))))
        return f"stub://video/{token}?refs={len(refs)}"


class StubAudioBackend:
    provider_id = "stub-audio"

    def score(self, prompt: str, duration_seconds: float = 30) -> str:
        return f"stub://score/{abs(hash(prompt))}"

    def speak(self, text: str, voice_id: str) -> str:
        return f"stub://voice/{voice_id}/{abs(hash(text))}"
