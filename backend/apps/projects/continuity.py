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
    audio_contract = project.audio_contract or {}
    narrator_contract = audio_contract.get("narrator") or {}
    lines = [
        beat.video_prompt or beat.text,
        "",
        f"VISUAL STYLE LOCK [{project.visual_style}]: {visual_style_prompt(project.visual_style)}",
        "Never drift to another rendering medium or visual style between shots.",
        "",
        "CONTINUITY LOCK - preserve exactly across shots:",
        "",
        "AUDIO CONTINUITY LOCK:",
        f"Canonical spoken language: {audio_contract.get('language') or 'français'}.",
        f"Narrator voice: {narrator_contract.get('voice') or 'project default'}; accent: {narrator_contract.get('accent') or 'natural'}; tone: {narrator_contract.get('tone') or 'natural'}; pace: {narrator_contract.get('pace') or 'modéré'}.",
        "Every recurring character must keep the same canonical voice description across all shots. Never swap a character voice with the narrator voice.",
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


def resolve_ingredients(beat: Beat, *, reference_uids: list[str] | None = None) -> dict:
    """Resolve canonical media refs, optionally restricted to explicit stable UIDs."""
    project = beat.episode.season.project
    picked = []

    for character in beat.characters.all():
        asset = _latest_ref(project, Asset.Role.CHARACTER_REF, character.key)
        if asset:
            picked.append({"role": asset.role, "key": character.key, "reference_uid": character.reference_uid, "uri": asset.uri, "name": (asset.meta or {}).get("name")})

    if beat.location_id:
        loc = _latest_ref(project, Asset.Role.LOCATION_REF, beat.location.key)
        if loc:
            picked.append({"role": loc.role, "key": beat.location.key, "reference_uid": beat.location.reference_uid, "uri": loc.uri, "name": (loc.meta or {}).get("name")})

    for prop in beat.props.all():
        asset = _latest_ref(project, Asset.Role.PROP_REF, prop.key)
        if asset:
            picked.append({"role": asset.role, "key": prop.key, "reference_uid": prop.reference_uid, "uri": asset.uri, "name": (asset.meta or {}).get("name")})

    requested_uids = [str(uid) for uid in (reference_uids or []) if str(uid).strip()]
    if requested_uids:
        by_uid = {str(item.get("reference_uid")): item for item in picked}
        picked = [by_uid[uid] for uid in requested_uids if uid in by_uid]

    # Veo can consume only a small number of asset refs. Preserve every
    # canonical binding in items/reference_uids, while ordering the actual media
    # payload by identity importance: speaker, other characters, location, props.
    speaker_key = beat.speaker.key if beat.speaker_id else None
    role_priority = {
        Asset.Role.CHARACTER_REF: 1,
        Asset.Role.LOCATION_REF: 2,
        Asset.Role.PROP_REF: 3,
    }
    priority_uids = []
    if hasattr(beat, "_shot_priority_reference_uids"):
        priority_uids = [str(uid) for uid in beat._shot_priority_reference_uids if str(uid).strip()]
    priority_rank = {uid: index for index, uid in enumerate(priority_uids)}
    media_items = sorted(
        [item for item in picked if item.get("uri")],
        key=lambda item: (
            0 if str(item.get("reference_uid") or "") in priority_rank else 1,
            priority_rank.get(str(item.get("reference_uid") or ""), 999),
            0 if speaker_key and item.get("key") == speaker_key else role_priority.get(item.get("role"), 9),
            str(item.get("reference_uid") or ""),
        ),
    )
    uris = [item["uri"] for item in media_items]
    start = next((item["uri"] for item in media_items if item["role"] == Asset.Role.LOCATION_REF), None)
    return {
        "items": picked,
        "media_items": media_items,
        "uris": uris,
        "start_frame": start,
    }


def _veo_safe_visual_action(shot) -> str:
    """Keep child/school scenes visually equivalent while avoiding ambiguous dressing imagery."""
    beat = shot.beat
    raw = str(shot.video_prompt or shot.text or "").strip()
    corpus = " ".join([
        raw,
        str(shot.text or ""),
        str(beat.text or ""),
        " ".join(str(character.look or "") for character in beat.characters.all()),
    ]).lower()
    child_markers = ("jeune élève", "jeune eleve", "garçon", "garcon", "fille", "enfant", "écolier", "ecolier", "élève", "eleve")
    dressing_markers = ("enfil", "s'habill", "se rhabill", "déshabill", "deshabill", "met son uniforme", "mettre son uniforme")
    if any(x in corpus for x in child_markers) and any(x in corpus for x in dressing_markers):
        return (
            "A school student is already fully dressed in the complete school uniform. "
            "In a normal family morning routine, the student stands beside the prepared bed, "
            "neatly adjusts the collar and sleeves of the uniform, then picks up the school bag. "
            "Wholesome educational context; ordinary age-appropriate school preparation. "
            "No dressing or undressing is shown."
        )
    return raw


def shot_render_package(shot, adjustment_prompt: str = "") -> dict:
    """Reuse the Beat's canonical refs/voice while applying the Shot's visual action."""
    beat = shot.beat
    readiness = validate_render_readiness(beat)
    context = readiness["context"]
    # Freeze the exact canonical entities used by this shot. The UID list is
    # persisted on Shot so every later take/re-adjustment resolves the same refs.
    canonical_pack = readiness["ingredients"]
    if not shot.reference_uids:
        shot.reference_uids = [
            item["reference_uid"] for item in canonical_pack["items"] if item.get("reference_uid")
        ]
        shot.save(update_fields=["reference_uids"])
    priority_uids = list((shot.continuity or {}).get("priority_reference_uids") or [])
    beat._shot_priority_reference_uids = priority_uids
    pack = resolve_ingredients(beat, reference_uids=shot.reference_uids)
    scene_frame = beat.assets.filter(role=Asset.Role.START_FRAME, meta__locked=True).order_by("-id").first()
    project = beat.episode.season.project
    audio_contract = project.audio_contract or {}
    narrator_contract = audio_contract.get("narrator") or {}
    previous_take = shot.takes.exclude(uri="").order_by("-number").first()

    adjustment = str(adjustment_prompt or "").strip()
    speech_mode = _speech_mode(beat)
    beat_audio = _beat_audio(beat)
    visual_action = _veo_safe_visual_action(shot)
    lines = []
    if adjustment:
        lines.extend([
            "USER ADJUSTMENT - HIGH PRIORITY FOR THIS NEW TAKE:",
            adjustment,
            "Apply this requested camera/acting/lighting/staging change visibly in the generated take while preserving all canonical identity, story and dialogue locks below.",
            "",
        ])
    revision_constraints = list((shot.continuity or {}).get("revision_constraints") or [])
    if revision_constraints:
        lines.extend(["HUMAN REVISION CONSTRAINTS - MANDATORY:"])
        for constraint in revision_constraints:
            instruction = str(constraint.get("instruction") or "").strip()
            if instruction:
                lines.append(f"- {instruction}")
        lines.extend([
            "These corrections override older staging details. Do not reintroduce removed props, wardrobe or visual elements.",
            "",
        ])
    lines.extend([
        "VISUAL ACTION ONLY - NEVER SPEAK OR NARRATE THIS TEXT:",
        visual_action,
        "",
        continuity_prompt(beat, context),
        "",
        "SHOT LOCK:",
        f"Render visually only this shot action: {visual_action}",
        "The action/description text is silent directing metadata. It must NEVER be spoken, narrated, read aloud, lip-synced, or turned into dialogue by any character or off-screen voice.",
        "Do not add, translate, paraphrase or replace spoken dialogue.",
    ])
    if speech_mode == "narration":
        lines.extend([
            "SPEECH MODE: EXTERNAL VOICE-OVER NARRATION.",
            f'ONLY ALLOWED NARRATION (verbatim): "{beat_audio["narration"]}"',
            "The narrator is external and off-screen. No visible character lip-syncs or speaks these words.",
            f"NARRATOR VOICE LOCK: voice={narrator_contract.get('voice') or 'project default'}; accent={narrator_contract.get('accent') or 'natural'}; tone={narrator_contract.get('tone') or 'natural'}; pace={narrator_contract.get('pace') or 'modéré'}. Keep the exact same narrator identity across every narrated shot.",
            "Pronounce the canonical narration in its original language; when it is French, speak French naturally.",
            "Do not translate, paraphrase, summarize, improvise or add words before or after the canonical narration.",
        ])
    elif speech_mode == "dialogue":
        lines.extend([
            "SPEECH MODE: DIALOGUE ONLY.",
            f'ONLY ALLOWED SPOKEN WORDS (verbatim): "{beat_audio["dialogue"]}"',
            "The canonical story/dialogue language is French when the supplied dialogue is French. Pronounce French text in French; never replace it with English or another language.",
            "No narration, no description, no improvised words, no extra words before or after the canonical dialogue.",
            "LANGUAGE LOCK: speak the canonical dialogue verbatim in its original language. "
            "Do not translate, paraphrase, summarize or switch language.",
        ])
    elif speech_mode == "mixed":
        lines.extend([
            "SPEECH MODE: NARRATION + CHARACTER DIALOGUE.",
            f'ONLY ALLOWED NARRATION (verbatim): "{beat_audio["narration"]}"',
            f'ONLY ALLOWED CHARACTER DIALOGUE (verbatim): "{beat_audio["dialogue"]}"',
            "VOICE SEPARATION LOCK: narration is spoken only by the external off-screen narrator; character dialogue is spoken only by the canonical speaker.",
            f"NARRATOR VOICE LOCK: voice={narrator_contract.get('voice') or 'project default'}; accent={narrator_contract.get('accent') or 'natural'}; tone={narrator_contract.get('tone') or 'natural'}; pace={narrator_contract.get('pace') or 'modéré'}.",
            "Never swap narrator and character voices. Never make a visible character lip-sync the narration.",
            "LANGUAGE LOCK: preserve both canonical texts verbatim in their original language. Do not translate, paraphrase, summarize or improvise.",
        ])
    else:
        lines.extend([
            "SPEECH MODE: SILENT.",
            "There is NO spoken dialogue in this shot. No character and no off-screen voice may speak or narrate anything.",
            "Use only visual acting and natural non-verbal ambience appropriate to the scene.",
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
    uid_lines = [
        f"{item['role']} UID={item.get('reference_uid')} KEY={item.get('key')} NAME={item.get('name')}"
        for item in pack["items"] if item.get("reference_uid")
    ]
    if uid_lines:
        lines.extend([
            "",
            "CANONICAL REFERENCE UID LOCK:",
            *uid_lines,
            "Every occurrence of the same UID across beats and shots is the exact same canonical entity. Never reinterpret or replace it.",
        ])
    if adjustment and previous_take:
        lines.extend([
            "",
            "PREVIOUS TAKE CONTINUITY:",
            f"Previous take #{previous_take.number} is the presentation baseline. Preserve all canonical identity, set, wardrobe, voice and language continuity from it; change only what the user explicitly requests.",
        ])
    if adjustment:
        lines.extend([
            "",
            "USER ADJUSTMENT CONFIRMATION:",
            f"The requested change for this take is: {adjustment}",
            "The resulting take must visibly reflect that change. It may alter staging, acting, framing, camera, lighting or rhythm, but never canonical identity, references, story facts, exact dialogue, dialogue language, voice continuity or locked visual style.",
        ])
    return {
        **readiness,
        "prompt": "\n".join(lines),
        "project": project,
        "ingredients": pack,
        "context": context,
        "scene_frame": (
            {"id": scene_frame.id, "uri": scene_frame.uri, "meta": scene_frame.meta}
            if scene_frame else None
        ),
        "previous_take": (
            {"id": previous_take.id, "number": previous_take.number, "uri": previous_take.uri}
            if previous_take else None
        ),
        "speech_mode": speech_mode,
    }


def _beat_audio(beat: Beat) -> dict:
    audio = (beat.continuity or {}).get("audio") or {}
    narration = str(audio.get("narration") or "").strip()
    dialogue = str(audio.get("dialogue") or "").strip()
    # Legacy beats stored their single spoken channel in beat.dialogue.
    if not narration and not dialogue and beat.dialogue:
        if beat.speaker_id:
            dialogue = str(beat.dialogue).strip()
        else:
            project = beat.episode.season.project
            if project.delivery == "voix_off":
                narration = str(beat.dialogue).strip()
            else:
                dialogue = str(beat.dialogue).strip()
    return {"narration": narration, "dialogue": dialogue}


def _speech_mode(beat: Beat) -> str:
    """Return silent, narration, dialogue or mixed from explicit beat audio channels."""
    audio = _beat_audio(beat)
    if audio["narration"] and audio["dialogue"]:
        return "mixed"
    if audio["narration"]:
        return "narration"
    if audio["dialogue"]:
        return "dialogue"
    return "silent"

def _is_voice_over(beat: Beat) -> bool:
    return _speech_mode(beat) == "narration"


def validate_render_readiness(beat: Beat) -> dict:
    """Fail before spending Veo quota when canonical continuity is incomplete."""
    context = build_continuity_context(beat)
    pack = resolve_ingredients(beat)
    errors = []

    if not beat.video_prompt and not beat.text:
        errors.append("beat sans prompt vidéo exploitable")
    scene_frame = beat.assets.filter(role=Asset.Role.START_FRAME, meta__locked=True).order_by("-id").first()
    if scene_frame is None:
        errors.append("image de scène du beat absente ou non verrouillée")
    beat_audio = _beat_audio(beat)
    if beat_audio["dialogue"] and not beat.speaker_id:
        errors.append("dialogue personnage sans speaker canonique")
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
