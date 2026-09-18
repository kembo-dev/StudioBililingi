from __future__ import annotations

from apps.production.models import Asset
from apps.story.models import Beat


def _latest_ref(project, role: str, key: str | None = None):
    qs = project.assets.filter(role=role).order_by("-id")
    if not key:
        return None
    for asset in qs:
        if (asset.meta or {}).get("key") == key:
            return asset
    return None


def resolve_ingredients(beat: Beat) -> dict:
    """Resolve only references explicitly attached to the beat.

    Never fall back to every character/prop in the project: doing so leaks
    unrelated continuity into video generation.
    """
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


def render_beat(beat: Beat) -> Beat:
    """Render a beat. The caller/queue owns the Job lifecycle."""
    from agents.backends import get_video

    project = beat.episode.season.project
    pack = resolve_ingredients(beat)
    backend = get_video()
    prompt = beat.video_prompt or beat.text

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
        )
        Asset.objects.create(
            project=project,
            beat=beat,
            kind=Asset.Kind.VIDEO,
            role=Asset.Role.CLIP,
            uri=uri,
            provider=getattr(backend, "provider_id", ""),
            meta={"prompt": prompt, "ingredients": pack["items"], "take": beat.take},
        )
        beat.status = Beat.Status.REVIEW
        beat.save(update_fields=["status"])
    except Exception:
        beat.status = Beat.Status.REJECTED
        beat.save(update_fields=["status"])
        raise
    return beat
