from apps.production.models import Review
from apps.story.models import Beat, BeatTake

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
    # Recontextualization creates a draft take instead of mutating the canonical beat.
    next_number = (beat.takes.order_by("-number").values_list("number", flat=True).first() or 0) + 1
    BeatTake.objects.create(
        beat=beat,
        number=next_number,
        prompt=text[:400],
        negative_prompt=beat.negative_prompt,
        backend=beat.backend,
        status=BeatTake.Status.QUEUED,
        generation_meta={"form": form, "rewrite_instruction": prompt, "source_text": beat.text},
    )
    Review.objects.create(beat=beat, episode=beat.episode, decision=Review.Decision.REVISE, comment=f"[{form}] {prompt}")
    return beat
