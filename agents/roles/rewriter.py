from __future__ import annotations

from agents.backends import get_text


class BeatRewriter:
    role = "beat_rewriter"

    def __init__(self):
        self.text = get_text()

    def rewrite(self, *, beat: str, instruction: str, concept: str, bible: dict) -> dict:
        return self.text.generate_json(
            system=(
                "Tu réécris UN beat. JSON uniquement : "
                '{"text": str, "word_count": int, "video_prompt": str}. '
                "Environ 24 mots, une action filmable. Applique l'instruction. Pas de nouveau personnage."
            ),
            user=f"INSTRUCTION:\n{instruction}\n\nBEAT:\n{beat}\n\nCONCEPT:\n{concept}\n\nBIBLE:\n{bible}",
        )
