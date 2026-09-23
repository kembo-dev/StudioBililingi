from __future__ import annotations

from apps.production.models import Asset
from apps.story.models import Beat, BeatTake


def _latest_ref(project, role: str, key: str | None = None):
    qs = project.assets.filter(role=role).order_by("-id")
    if not key:
        return None
    for asset in qs:
        if (asset.meta or {}).get("key") == key:
            return asset
    return None


def _character_state(character, *, speaker_id: int | None = None) -> dict:
    return {
        "key": character.key,
        "name": character.name,
        "role": character.role,
        "look": character.look,
        "voice": character.voice,
        "is_speaker": character.id == speaker_id,
    }


def build_continuity_context(beat: Beat) -> dict:
    """Build deterministic visual continuity from canonical project entities."""
    scene = beat.scene
    previous = None
    if beat.script_id:
        previous = (
            Beat.objects.filter(script_id=beat.script_id, index__lt=beat.index)
            .order_by("-index")
            .first()
        )

    characters = [
        _character_state(character, speaker_id=beat.speaker_id)
        for character in beat.characters.all().order_by("key")
    ]
    location = None
    if beat.location_id:
        location = {
            "key": beat.location.key,
            "name": beat.location.name,
            "look": beat.location.look,
            "time_of_day": (
                scene.time_of_day if scene and scene.time_of_day else beat.location.time_of_day
            ),
            "lighting": scene.lighting if scene else "",
        }
    props = [
        {
            "key": prop.key,
            "name": prop.name,
            "look": prop.look,
            "story_function": prop.story_function,
        }
        for prop in beat.props.all().order_by("key")
    ]

    return {
        "scene": {
            "index": scene.index if scene else None,
            "heading": scene.heading if scene else "",
            "summary": scene.summary if scene else "",
        },
        "characters": characters,
        "speaker": (
            {"key": beat.speaker.key, "name": beat.speaker.name, "voice": beat.speaker.voice}
            if beat.speaker_id else None
        ),
        "location": location,
        "props": props,
        "beat_state": beat.continuity if isinstance(beat.continuity, dict) else {},
        "previous_beat": (
            {
                "id": previous.id,
                "index": previous.index,
                "continuity": previous.continuity if isinstance(previous.continuity, dict) else {},
                "camera": previous.camera if isinstance(previous.camera, dict) else {},
                "emotion": previous.emotion,
            }
            if previous else None
        ),
    }


def continuity_prompt(beat: Beat, context: dict) -> str:
    """Turn canonical continuity into stable video instructions."""
    from agents.roles.art_director import visual_style_prompt

    project = beat.episode.season.project
    lines = [
        beat.video_prompt or beat.text,
        "",
        f"VISUAL STYLE LOCK [{project.visual_style}]: {visual_style_prompt(project.visual_style)}",
        "Never drift to another rendering medium or visual style between shots.",
        "",
        "CONTINUITY LOCK - preserve exactly across shots:",
    ]
    location = context.get("location")
    if location:
        lines.append(
            f"LOCATION [{location['key']}]: {location['name']}. "
            f"Visual identity: {location['look']}. Time: {location['time_of_day']}. "
            f"Lighting: {location['lighting']}."
        )
    for character in context.get("characters") or []:
        speaking = " SPEAKING CHARACTER." if character.get("is_speaker") else ""
        lines.append(
            f"CHARACTER [{character['key']}]: {character['name']}. "
            f"Keep exact identity and appearance: {character['look']}. "
            f"Voice continuity: {character['voice']}.{speaking}"
        )
    for prop in context.get("props") or []:
        lines.append(
            f"PROP [{prop['key']}]: {prop['name']}. Keep exact appearance: {prop['look']}."
        )
    state = context.get("beat_state") or {}
    if state:
        lines.append(f"BEAT CONTINUITY STATE: {state}.")
    previous = context.get("previous_beat")
    if previous:
        lines.append(
            f"PREVIOUS SHOT STATE: continuity={previous['continuity']}; "
            f"camera={previous['camera']}; emotion={previous['emotion']}."
        )
    lines.append("Do not change face, age, skin tone, hairstyle, wardrobe, props or set identity unless explicitly required by the beat.")
    return "\n".join(lines)


def resolve_ingredients(beat: Beat) -> dict:
    """Resolve only references explicitly attached to the beat."""
    project = beat.episode.season.project
    picked = []

    for character in beat.characters.all():
        asset = _latest_ref(project, Asset.Role.CHARACTER_REF, character.key)
        if asset:
            picked.append({"role": asset.role, "key": character.key, "uri": asset.uri, "name": (asset.meta or {}).get("name")})

    if beat.location_id:
        loc = _latest_ref(project, Asset.Role.LOCATION_REF, beat.location.key)
        if loc:
            picked.append({"role": loc.role, "key": beat.location.key, "uri": loc.uri, "name": (loc.meta or {}).get("name")})

    for prop in beat.props.all():
        asset = _latest_ref(project, Asset.Role.PROP_REF, prop.key)
        if asset:
            picked.append({"role": asset.role, "key": prop.key, "uri": asset.uri, "name": (asset.meta or {}).get("name")})

    uris = [item["uri"] for item in picked if item.get("uri")]
    start = next((item["uri"] for item in picked if item["role"] == Asset.Role.LOCATION_REF), None)
    return {"items": picked, "uris": uris, "start_frame": start}


def shot_render_package(shot, adjustment_prompt: str = "") -> dict:
    """Reuse the Beat's canonical refs/voice while applying the Shot's visual action."""
    beat = shot.beat
    readiness = validate_render_readiness(beat)
    context = readiness["context"]
    pack = readiness["ingredients"]
    project = beat.episode.season.project

    lines = [
        shot.video_prompt or shot.text,
        "",
        continuity_prompt(beat, context),
        "",
        "SHOT LOCK:",
        f"Render only this shot action: {shot.text}",
        "Do not add, translate, paraphrase or replace spoken dialogue.",
    ]
    if beat.dialogue:
        lines.extend([
            f'CANONICAL SPOKEN DIALOGUE: "{beat.dialogue}"',
            "LANGUAGE LOCK: speak the canonical dialogue exactly in its original language. "
            "Do not translate it to English or to any other language.",
        ])
    speaker = context.get("speaker")
    if speaker:
        lines.append(
            f"SPEAKER LOCK: {speaker['name']} must keep the canonical voice/accent: {speaker['voice']}."
        )
    lines.append(
        "REFERENCE IMAGE LOCK: character reference images are identity constraints, not inspiration. "
        "Preserve the same face, age, skin tone, hair and wardrobe visible in the supplied references."
    )
    adjustment = str(adjustment_prompt or "").strip()
    if adjustment:
        lines.extend([
            "",
            "USER TAKE ADJUSTMENT:",
            adjustment,
            "Apply this adjustment only to staging, acting, framing, camera, lighting, rhythm or other non-canonical presentation details. "
            "It must never override character identity, canonical references, location identity, story facts, exact dialogue, original dialogue language, voice continuity or locked visual style.",
        ])
    return {
        **readiness,
        "prompt": "\n".join(lines),
        "project": project,
        "ingredients": pack,
        "context": context,
    }


def validate_render_readiness(beat: Beat) -> dict:
    """Fail before spending Veo quota when canonical continuity is incomplete."""
    context = build_continuity_context(beat)
    pack = resolve_ingredients(beat)
    errors = []

    if not beat.video_prompt and not beat.text:
        errors.append("beat sans prompt vidéo exploitable")
    if beat.dialogue and not beat.speaker_id:
        errors.append("dialogue sans speaker canonique")
    if beat.location_id and not any(
        item["role"] == Asset.Role.LOCATION_REF for item in pack["items"]
    ):
        errors.append(f"référence visuelle du lieu absente: {beat.location.key}")
    missing_characters = [
        character.key
        for character in beat.characters.all()
        if not any(
            item["role"] == Asset.Role.CHARACTER_REF and item["key"] == character.key
            for item in pack["items"]
        )
    ]
    if missing_characters:
        errors.append("références personnages absentes: " + ", ".join(missing_characters))

    return {
        "ready": not errors,
        "errors": errors,
        "context": context,
        "ingredients": pack,
        "prompt": continuity_prompt(beat, context),
    }


def render_beat(beat: Beat) -> Beat:
    """Render a beat with canonical continuity. The queue owns Job lifecycle."""
    from agents.backends import get_video

    project = beat.episode.season.project
    readiness = validate_render_readiness(beat)
    if not readiness["ready"]:
        raise ValueError("Rendu vidéo refusé: " + "; ".join(readiness["errors"]))
    context = readiness["context"]
    pack = readiness["ingredients"]
    backend = get_video()
    prompt = readiness["prompt"]
    next_number = (beat.takes.order_by("-number").values_list("number", flat=True).first() or 0) + 1
    take = BeatTake.objects.create(
        beat=beat,
        number=next_number,
        prompt=prompt,
        negative_prompt=beat.negative_prompt,
        backend=getattr(backend, "provider_id", beat.backend),
        status=BeatTake.Status.RENDERING,
        generation_meta={"ingredients": pack["items"], "continuity": context},
    )

    if beat.status == Beat.Status.DRAFT:
        beat.status = Beat.Status.APPROVED_TEXT
        beat.save(update_fields=["status"])
    beat.status = Beat.Status.RENDERING
    beat.save(update_fields=["status"])

    try:
        uri = backend.render(
            prompt,
            start_frame=pack["start_frame"],
            ingredients=pack["uris"],
            duration_seconds=float(beat.duration_seconds),
            aspect_ratio=project.aspect_ratio,
            project_key=f"{project.id}-{project.slug}",
        )
        Asset.objects.create(
            project=project,
            beat=beat,
            beat_take=take,
            kind=Asset.Kind.VIDEO,
            role=Asset.Role.CLIP,
            uri=uri,
            provider=getattr(backend, "provider_id", ""),
            meta={
                "prompt": prompt,
                "ingredients": pack["items"],
                "continuity": context,
                "take": take.number,
                "take_id": take.id,
            },
        )
        take.uri = uri
        take.status = BeatTake.Status.REVIEW
        take.save(update_fields=["uri", "status"])
        beat.take = take.number
        beat.status = Beat.Status.REVIEW
        beat.save(update_fields=["status", "take"])
    except Exception:
        take.status = BeatTake.Status.FAILED
        take.save(update_fields=["status"])
        beat.status = Beat.Status.REJECTED
        beat.save(update_fields=["status"])
        raise
    return beat
