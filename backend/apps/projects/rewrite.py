from apps.production.models import Review
from apps.story.models import Beat, BeatTake, Shot, ShotTake

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
    rewrite_meta = {}
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
            video_prompt = (raw.get("video_prompt") or "").strip()
            rewrite_meta = {
                "intent": (raw.get("intent") or "").strip(),
                "continuity": (raw.get("continuity") or "").strip(),
                "performance": (raw.get("performance") or "").strip(),
                "camera": (raw.get("camera") or "").strip(),
                "sound": (raw.get("sound") or "").strip(),
                "video_prompt": video_prompt,
            }
    except Exception:
        text = ""
    if not text:
        text = _fallback_text(beat, prompt, form)
    # Apply the staging instruction to the actual production shots. The canonical
    # story text stays immutable, while every existing shot receives the new
    # directing layer and becomes eligible for a fresh generated take.
    shots = list(beat.shots.order_by("index"))
    for shot in shots:
        continuity = dict(shot.continuity or {})
        history = list(continuity.get("staging_revisions") or [])
        history.append({
            "instruction": prompt,
            "intent": rewrite_meta.get("intent", ""),
            "continuity": rewrite_meta.get("continuity", ""),
            "performance": rewrite_meta.get("performance", ""),
            "camera": rewrite_meta.get("camera", ""),
            "sound": rewrite_meta.get("sound", ""),
        })
        continuity["staging_revisions"] = history[-10:]
        continuity["active_staging_instruction"] = prompt
        shot.continuity = continuity
        if rewrite_meta.get("video_prompt"):
            shot.video_prompt = (
                f"{shot.video_prompt.strip()}\n\n"
                f"MISE EN SCÈNE DEMANDÉE: {rewrite_meta['video_prompt']}"
            ).strip()
        else:
            shot.video_prompt = (
                f"{shot.video_prompt.strip()}\n\n"
                f"MISE EN SCÈNE DEMANDÉE: {prompt}"
            ).strip()
        shot.status = Shot.Status.DRAFT
        shot.save(update_fields=["continuity", "video_prompt", "status"])
        shot.takes.filter(status=ShotTake.Status.LOCKED).update(status=ShotTake.Status.REVIEW)

    # Keep an auditable beat-level proposal as well.
    next_number = (beat.takes.order_by("-number").values_list("number", flat=True).first() or 0) + 1
    BeatTake.objects.create(
        beat=beat,
        number=next_number,
        prompt=text[:400],
        negative_prompt=beat.negative_prompt,
        backend=beat.backend,
        status=BeatTake.Status.REVIEW,
        generation_meta={
            "form": form,
            "rewrite_instruction": prompt,
            "source_text": beat.text,
            "script_doctor": rewrite_meta,
            "applied_to_shot_ids": [shot.id for shot in shots],
        },
    )
    Review.objects.create(beat=beat, episode=beat.episode, decision=Review.Decision.REVISE, comment=f"[mise_en_scene:{form}] {prompt}")
    return beat
