from __future__ import annotations

from apps.jobs.models import Job
from apps.production.models import Asset
from apps.story.models import Beat


def _latest_ref(project, role: str, key: str | None = None):
    qs = project.assets.filter(role=role).order_by("-id")
    if key:
        for asset in qs:
            if (asset.meta or {}).get("key") == key:
                return asset
    return qs.first()


def resolve_ingredients(beat: Beat) -> dict:
    project = beat.episode.season.project
    picked = []

    keys = {c.key for c in beat.characters.all()} or {c.key for c in project.characters.all()}
    for key in keys:
        asset = _latest_ref(project, Asset.Role.CHARACTER_REF, key)
        if asset:
            picked.append({"role": asset.role, "key": key, "uri": asset.uri, "name": (asset.meta or {}).get("name")})

    loc_key = beat.location.key if beat.location_id else None
    loc = _latest_ref(project, Asset.Role.LOCATION_REF, loc_key)
    if loc:
        picked.append({"role": loc.role, "key": (loc.meta or {}).get("key"), "uri": loc.uri, "name": (loc.meta or {}).get("name")})

    prop_keys = {p.key for p in beat.props.all()} or {p.key for p in project.props.all()}
    for key in prop_keys:
        asset = _latest_ref(project, Asset.Role.PROP_REF, key)
        if asset:
            picked.append({"role": asset.role, "key": key, "uri": asset.uri, "name": (asset.meta or {}).get("name")})

    uris = [item["uri"] for item in picked if item.get("uri")]
    start = next((item["uri"] for item in picked if item["role"] == Asset.Role.LOCATION_REF), None)
    return {"items": picked, "uris": uris, "start_frame": start}


def render_beat(beat: Beat) -> Beat:
    from agents.backends import get_video

    pack = resolve_ingredients(beat)
    if beat.status == Beat.Status.DRAFT:
        beat.status = Beat.Status.APPROVED_TEXT
        beat.save(update_fields=["status"])
    beat.status = Beat.Status.RENDERING
    beat.save(update_fields=["status"])
    backend = get_video()
    prompt = beat.video_prompt or beat.text
    project = beat.episode.season.project
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
            meta={"prompt": prompt, "take": beat.take, "ingredients": pack["items"], "start_frame": pack["start_frame"]},
        )
        Job.objects.create(
            project=project,
            kind=Job.Kind.VIDEO,
            status=Job.Status.SUCCEEDED,
            agent_role="cinematographer",
            backend=getattr(backend, "provider_id", ""),
            result={"beat_id": beat.id, "uri": uri, "ingredients": len(pack["uris"])},
        )
        beat.status = Beat.Status.REVIEW
        beat.save(update_fields=["status"])
    except Exception as exc:
        beat.status = Beat.Status.REJECTED
        beat.save(update_fields=["status"])
        Job.objects.create(
            project=project,
            kind=Job.Kind.VIDEO,
            status=Job.Status.FAILED,
            agent_role="cinematographer",
            backend=getattr(backend, "provider_id", ""),
            error=str(exc),
            result={"ingredients": pack["items"]},
        )
        raise
    return beat
