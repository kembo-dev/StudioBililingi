from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlretrieve

from django.conf import settings

from apps.production.models import Asset
from apps.story.models import Episode, ShotTake


def _local_clip(uri: str, directory: str, index: int) -> str:
    parsed = urlparse(uri)
    if parsed.scheme in ("", "file"):
        path = parsed.path if parsed.scheme == "file" else uri
        if str(path).startswith("/media/"):
            path = os.path.join(str(settings.MEDIA_ROOT), str(path)[len("/media/"):])
        if not os.path.exists(path):
            raise ValueError(f"Clip introuvable: {uri}")
        return os.path.abspath(path)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Assemblage impossible pour URI non matérialisée: {uri}")
    suffix = Path(parsed.path).suffix or ".mp4"
    target = os.path.join(directory, f"clip-{index:04d}{suffix}")
    urlretrieve(uri, target)
    return target


def assemble_episode(episode: Episode) -> Asset:
    """Concatenate locked ShotTakes from the latest segmentation in story order."""
    latest_script = episode.scripts.order_by("-version").first()
    if latest_script is None:
        raise ValueError("Aucun script à assembler")
    segmentation = latest_script.segmentations.order_by("-version").first()
    beats_qs = segmentation.beats if segmentation else latest_script.beats
    beats = list(beats_qs.order_by("index").prefetch_related("shots__takes"))
    if not beats:
        raise ValueError("Aucun beat à assembler")

    locked = []
    for beat in beats:
        shots = list(beat.shots.order_by("index"))
        if not shots:
            raise ValueError(f"Beat {beat.index}: aucun shot de production")
        for shot in shots:
            take = shot.takes.filter(status=ShotTake.Status.LOCKED).order_by("-number").first()
            if take is None or not take.uri:
                raise ValueError(f"Beat {beat.index} / Shot {shot.index}: aucun take verrouillé")
            locked.append((beat, shot, take))

    project = episode.season.project
    production_agents_enabled = os.getenv("STUDIO_PRODUCTION_AGENTS", "").strip().lower() in {"1", "true", "yes", "on"}
    if "test" in sys.argv and os.getenv("STUDIO_PRODUCTION_AGENTS_TESTS", "").strip().lower() not in {"1", "true", "yes", "on"}:
        production_agents_enabled = False
    editor_plan = {}
    sound_plan = []
    if production_agents_enabled:
        from agents.roles.editor import Editor
        from agents.roles.sound_director import SoundDirector

        editor_plan = Editor().plan(
            episode={
                "id": episode.id,
                "number": episode.number,
                "title": episode.title,
                "logline": episode.logline,
            },
            shots=[
                {
                    "beat_id": beat.id,
                    "beat_index": beat.index,
                    "shot_id": shot.id,
                    "shot_index": shot.index,
                    "take_id": take.id,
                    "take_number": take.number,
                    "duration_seconds": float(shot.duration_seconds),
                }
                for beat, shot, take in locked
            ],
        )
        for beat in beats:
            sound_plan.append({
                "beat_id": beat.id,
                "beat_index": beat.index,
                "direction": SoundDirector().direct(
                    beat={
                        "id": beat.id,
                        "index": beat.index,
                        "text": beat.text,
                        "dialogue": beat.dialogue,
                        "continuity": beat.continuity,
                    },
                    audio_contract=project.audio_contract or {},
                    scene={
                        "id": beat.scene_id,
                        "heading": beat.scene.heading if beat.scene_id else "",
                        "summary": beat.scene.summary if beat.scene_id else "",
                    },
                ),
            })

    media_root = str(settings.MEDIA_ROOT)
    relative_dir = os.path.join("episodes", f"{project.id}-{project.slug}", f"episode-{episode.id}")
    output_dir = os.path.join(media_root, relative_dir)
    os.makedirs(output_dir, exist_ok=True)
    output = os.path.join(output_dir, "final.mp4")

    with tempfile.TemporaryDirectory(prefix="studiobililingi-assembly-") as tmp:
        paths = [_local_clip(take.uri, tmp, i) for i, (_, _, take) in enumerate(locked)]
        manifest = os.path.join(tmp, "concat.txt")
        with open(manifest, "w", encoding="utf-8") as handle:
            for path in paths:
                escaped = path.replace("'", "'\\''")
                handle.write(f"file '{escaped}'\n")
        subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", manifest, "-c", "copy", output], check=True, capture_output=True, text=True)

    return Asset.objects.create(
        project=project, kind=Asset.Kind.VIDEO, role=Asset.Role.EPISODE_CUT,
        uri=f"/media/{relative_dir.replace(os.sep, '/')}/final.mp4", provider="ffmpeg",
        meta={
            "episode_id": episode.id, "script_id": latest_script.id,
            "segmentation_id": segmentation.id if segmentation else None,
            "shots": [{"beat_id": beat.id, "shot_id": shot.id, "take_id": take.id, "number": take.number} for beat, shot, take in locked],
            "editor_plan": editor_plan,
            "sound_plan": sound_plan,
            "production_agents_enabled": production_agents_enabled,
        },
    )

