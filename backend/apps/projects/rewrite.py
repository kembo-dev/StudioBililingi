from apps.production.models import Review
from apps.story.models import Beat


def _fallback_text(beat: Beat, instruction: str) -> str:
    return " ".join(f"{instruction.strip()} {beat.text}".split()[:24])


def recontextualize_beat(beat: Beat, instruction: str) -> Beat:
    prompt = (instruction or "").strip()
    if not prompt:
        raise ValueError("Indique comment recadrer le beat")
    project = beat.episode.season.project
    bible = project.bibles.first()
    text = ""
    try:
        from agents.roles.rewriter import BeatRewriter
        raw = BeatRewriter().rewrite(beat=beat.text, instruction=prompt, concept=project.concept, bible=bible.payload if bible else {})
        if isinstance(raw, dict):
            text = (raw.get("text") or raw.get("beat") or "").strip()
    except Exception:
        text = ""
    if not text:
        text = _fallback_text(beat, prompt)
    beat.text = " ".join(text.split()[:28])
    beat.word_count = len(beat.text.split())
    beat.video_prompt = beat.text
    beat.status = Beat.Status.DRAFT
    beat.take = beat.take + 1
    beat.save(update_fields=["text", "word_count", "video_prompt", "status", "take"])
    Review.objects.create(beat=beat, episode=beat.episode, decision=Review.Decision.REVISE, comment=prompt)
    return beat
