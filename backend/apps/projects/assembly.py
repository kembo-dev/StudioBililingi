from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlretrieve

from apps.production.models import Asset
from apps.story.models import BeatTake, Episode


def _local_clip(uri: str, directory: str, index: int) -> str:
    parsed = urlparse(uri)
    if parsed.scheme in ("", "file"):
        path = parsed.path if parsed.scheme == "file" else uri
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
    """Concatenate the locked take of every beat from the latest script."""
    latest_script = episode.scripts.order_by("-version").first()
    if latest_script is None:
        raise ValueError("Aucun script à assembler")

    beats = list(latest_script.beats.order_by("index").prefetch_related("takes"))
    if not beats:
        raise ValueError("Aucun beat à assembler")

    locked = []
    for beat in beats:
        take = beat.takes.filter(status=BeatTake.Status.LOCKED).order_by("-number").first()
        if take is None or not take.uri:
            raise ValueError(f"Beat {beat.index}: aucun take verrouillé")
        locked.append((beat, take))

    project = episode.season.project
    media_root = os.environ.get("STUDIO_MEDIA_ROOT", "/tmp/studiobililingi-media")
    output_dir = os.path.join(media_root, f"project-{project.id}", f"episode-{episode.id}")
    os.makedirs(output_dir, exist_ok=True)
    output = os.path.join(output_dir, "final.mp4")

    with tempfile.TemporaryDirectory(prefix="studiobililingi-assembly-") as tmp:
        paths = [_local_clip(take.uri, tmp, i) for i, (_, take) in enumerate(locked)]
        manifest = os.path.join(tmp, "concat.txt")
        with open(manifest, "w", encoding="utf-8") as handle:
            for path in paths:
                escaped = path.replace("'", "'\\''")
                handle.write(f"file '{escaped}'\n")

        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", manifest, "-c", "copy", output],
            check=True,
            capture_output=True,
            text=True,
        )

    return Asset.objects.create(
        project=project,
        kind=Asset.Kind.VIDEO,
        role=Asset.Role.EPISODE_CUT,
        uri=f"file://{output}",
        provider="ffmpeg",
        meta={
            "episode_id": episode.id,
            "script_id": latest_script.id,
            "takes": [{"beat_id": beat.id, "take_id": take.id, "number": take.number} for beat, take in locked],
        },
    )
