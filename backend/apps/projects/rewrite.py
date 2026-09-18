from apps.production.models import Review
from apps.story.models import Beat

FORMS = ("storytell", "voix_off", "conversation", "rencontre")


def _fallback_text(beat: Beat, instruction: str, form: str) -> str:
    short = " ".join((instruction.strip() + " " + beat.text).split()[:22])
    if form == "voix_off":
        return f"VOIX OFF : « {short} »"
    if form == "conversation":
        return f"MARC : {short[:70]} / LA VOIX : Tu as entendu."
    if form == "rencontre":
        return f"Ils se font face. {short[:80]}"
    return short


def recontextualize_beat(beat: Beat, instruction: str, form: str = "storytell") -> Beat:
    prompt = (instruction or "").strip()
    form = (form or "storytell").strip().lower().replace(" ", "_")
    if form not in FORMS:
        form = "storytell"
    if not prompt:
        raise ValueError("Indique comment recadrer le beat")
    project = beat.episode.season.project
    bible = project.bibles.first()
    text = ""
    try:
        from agents.roles.rewriter import BeatRewriter
        raw = BeatRewriter().rewrite(
            beat=beat.text,
            instruction=prompt,
            concept=project.concept,
            bible=bible.payload if bible else {},
            form=form,
        )
        if isinstance(raw, dict):
            text = (raw.get("text") or "").strip()
    except Exception:
        text = ""
    if not text:
        text = _fallback_text(beat, prompt, form)
    beat.text = text[:400]
    beat.word_count = len(beat.text.split())
    beat.video_prompt = beat.text
    camera = dict(beat.camera or {})
    camera["form"] = form
    beat.camera = camera
    beat.status = Beat.Status.DRAFT
    beat.take = beat.take + 1
    beat.save(update_fields=["text", "word_count", "video_prompt", "camera", "status", "take"])
    Review.objects.create(beat=beat, episode=beat.episode, decision=Review.Decision.REVISE, comment=f"[{form}] {prompt}")
    return beat
