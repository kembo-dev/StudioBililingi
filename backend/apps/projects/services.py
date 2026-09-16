from __future__ import annotations

import re

from django.utils.text import slugify

from apps.accounts.models import Organization
from apps.bible.models import Character, Location, Prop, WorldBible
from apps.jobs.models import Job
from apps.projects.models import Project, Season
from apps.story.models import Beat, Episode, Script


def _ensure_org(name: str) -> Organization:
    slug = slugify(name) or "studio"
    org, _ = Organization.objects.get_or_create(slug=slug, defaults={"name": name})
    return org


def create_project(*, title: str, concept: str, genre: str = "", tone: str = "", ending_intent: str = "", organization_name: str = "Studio") -> Project:
    org = _ensure_org(organization_name)
    base = slugify(title) or "projet"
    slug = base
    n = 2
    while Project.objects.filter(organization=org, slug=slug).exists():
        slug = f"{base}-{n}"
        n += 1
    project = Project.objects.create(
        organization=org,
        title=title,
        slug=slug,
        concept=concept,
        genre=genre,
        tone=tone,
        ending_intent=ending_intent,
        status=Project.Status.ACTIVE,
    )
    Season.objects.create(project=project, number=1, title="Saison 1", premise=concept[:400])
    return project


def _words(text: str) -> list[str]:
    return [w for w in re.split(r"\s+", text.strip()) if w]


def seed_bible(concept: str) -> dict:
    short = concept.strip()[:80] or "Série sans titre"
    return {
        "version": 1,
        "logline": short,
        "tone": "dramatique, immédiat",
        "locked": False,
        "characters": [
            {"id": "protag", "name": "Awa", "role": "protagoniste", "want": "protéger ce qui reste", "need": "accepter l'aide", "look": "30 ans, tresses courtes, veste usée", "voice": "calme", "locked": False},
            {"id": "antag", "name": "Malo", "role": "antagoniste", "want": "contrôler la version officielle", "need": "ne plus mentir", "look": "costume clair", "voice": "poli", "locked": False},
        ],
        "locations": [{"id": "quai", "name": "Quai de nuit", "look": "lampadaires jaunes, eau noire", "time_of_day": "nuit", "locked": False}],
        "props": [{"id": "carnet", "name": "Carnet rouge", "look": "couverture abîmée", "story_function": "preuve", "locked": False}],
        "source": "stub-seed",
        "concept": concept,
    }


def seed_season_plan(concept: str) -> list[dict]:
    return [
        {"number": 1, "title": "La preuve", "logline": "Awa trouve le carnet. Quelqu'un la suit.", "function_in_arc": "déclencheur"},
        {"number": 2, "title": "La version officielle", "logline": "Malo propose un marché. Awa refuse.", "function_in_arc": "premier obstacle"},
        {"number": 3, "title": "Le quai", "logline": "Échange de nuit. Le carnet change de main.", "function_in_arc": "point médian"},
        {"number": 4, "title": "Ce qui reste", "logline": "Awa choisit la vérité. Le prix est immédiat.", "function_in_arc": "climax"},
    ]


def persist_bible(project: Project, payload: dict) -> WorldBible:
    version = (project.bibles.first().version + 1) if project.bibles.exists() else 1
    bible = WorldBible.objects.create(project=project, version=version, payload=payload, locked=False)
    for item in payload.get("characters", []):
        Character.objects.update_or_create(
            project=project,
            key=item.get("id") or slugify(item.get("name", "perso")),
            defaults={"bible": bible, "name": item.get("name", "Sans nom"), "role": item.get("role", ""), "want": item.get("want", ""), "need": item.get("need", ""), "look": item.get("look", ""), "voice": item.get("voice", ""), "locked": False},
        )
    for item in payload.get("locations", []):
        Location.objects.update_or_create(
            project=project,
            key=item.get("id") or slugify(item.get("name", "lieu")),
            defaults={"bible": bible, "name": item.get("name", "Lieu"), "look": item.get("look", ""), "time_of_day": item.get("time_of_day", ""), "locked": False},
        )
    for item in payload.get("props", []):
        Prop.objects.update_or_create(
            project=project,
            key=item.get("id") or slugify(item.get("name", "objet")),
            defaults={"bible": bible, "name": item.get("name", "Objet"), "look": item.get("look", ""), "story_function": item.get("story_function", ""), "locked": False},
        )
    Job.objects.create(project=project, kind=Job.Kind.BIBLE, status=Job.Status.SUCCEEDED, agent_role="world_bible", backend="stub-text", result={"bible_id": bible.id})
    return bible


def persist_episodes(project: Project, plan: list[dict]) -> list[Episode]:
    season = project.seasons.order_by("number").first()
    created = []
    for row in plan:
        episode, _ = Episode.objects.update_or_create(
            season=season,
            number=row["number"],
            defaults={"title": row["title"], "logline": row["logline"], "function_in_arc": row.get("function_in_arc", ""), "status": Episode.Status.OUTLINED},
        )
        created.append(episode)
    return created


def seed_script(episode: Episode) -> str:
    return (
        f"{episode.title}. {episode.logline} "
        "Awa serre le carnet. Un pas derrière elle. Malo apparaît sous le lampadaire. "
        "Elle refuse le marché. L'eau claque contre le quai. Quelqu'un récupère le carnet."
    )


def segment_text(text: str, target: int = 24) -> list[str]:
    words = _words(text)
    return [" ".join(words[i : i + target]) for i in range(0, len(words), target)] if words else []


def persist_beats(episode: Episode, chunks: list[str]) -> list[Beat]:
    script = Script.objects.create(episode=episode, version=episode.scripts.count() + 1, fountain="\n".join(chunks), payload={"beats": chunks})
    episode.beats.all().delete()
    created = []
    location = episode.season.project.locations.first()
    for index, chunk in enumerate(chunks):
        created.append(
            Beat.objects.create(
                episode=episode,
                script=script,
                index=index,
                text=chunk,
                word_count=len(_words(chunk)),
                duration_seconds=8,
                location=location,
                video_prompt=chunk,
                backend="google-veo-3.1",
                status=Beat.Status.DRAFT,
            )
        )
    episode.status = Episode.Status.SEGMENTED
    episode.save(update_fields=["status"])
    Job.objects.create(project=episode.season.project, kind=Job.Kind.SEGMENT, status=Job.Status.SUCCEEDED, agent_role="beat_segmenter", backend="stub-text", result={"episode_id": episode.id, "beats": len(created)})
    return created


def run_showrunner(project: Project) -> dict:
    try:
        from agents.roles.showrunner import Showrunner
        raw = Showrunner().plan(project.concept)
    except Exception:
        raw = {"provider": "stub-text"}
    return {"agent": raw, "episodes": [e.id for e in persist_episodes(project, seed_season_plan(project.concept))]}


def run_bible(project: Project) -> WorldBible:
    try:
        from agents.roles.bible import WorldBibleAgent
        raw = WorldBibleAgent().draft(project.concept)
    except Exception:
        raw = {}
    payload = raw if raw.get("characters") else seed_bible(project.concept)
    payload.setdefault("project_id", str(project.id))
    return persist_bible(project, payload)


def run_segment(episode: Episode, script_text: str | None = None) -> list[Beat]:
    text = script_text or seed_script(episode)
    try:
        from agents.roles.segmenter import BeatSegmenter
        raw = BeatSegmenter().segment(text)
        chunks = raw.get("beats") if isinstance(raw, dict) else None
    except Exception:
        chunks = None
    return persist_beats(episode, chunks or segment_text(text))


def review_beat(beat: Beat, decision: str, comment: str = "") -> Beat:
    from apps.production.models import Review
    allowed = {"approve": Beat.Status.APPROVED_TEXT, "reject": Beat.Status.REJECTED, "revise": Beat.Status.DRAFT}
    if decision not in allowed:
        raise ValueError("decision must be approve, reject or revise")
    Review.objects.create(beat=beat, episode=beat.episode, decision=decision, comment=comment)
    beat.status = Beat.Status.LOCKED if decision == "approve" and beat.assets.filter(role="clip").exists() else allowed[decision]
    beat.save(update_fields=["status"])
    return beat


def render_beat(beat: Beat) -> Beat:
    from agents.backends import get_video
    from apps.production.models import Asset
    if beat.status == Beat.Status.DRAFT:
        beat.status = Beat.Status.APPROVED_TEXT
        beat.save(update_fields=["status"])
    beat.status = Beat.Status.RENDERING
    beat.save(update_fields=["status"])
    backend = get_video()
    prompt = beat.video_prompt or beat.text
    uri = backend.render(prompt, duration_seconds=float(beat.duration_seconds), aspect_ratio=beat.episode.season.project.aspect_ratio)
    Asset.objects.create(project=beat.episode.season.project, beat=beat, kind=Asset.Kind.VIDEO, role=Asset.Role.CLIP, uri=uri, provider=getattr(backend, "provider_id", ""), meta={"prompt": prompt, "take": beat.take})
    Job.objects.create(project=beat.episode.season.project, kind=Job.Kind.VIDEO, status=Job.Status.SUCCEEDED, agent_role="cinematographer", backend=getattr(backend, "provider_id", ""), result={"beat_id": beat.id, "uri": uri})
    beat.status = Beat.Status.REVIEW
    beat.save(update_fields=["status"])
    return beat
