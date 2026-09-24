from __future__ import annotations

import re

from django.db import transaction
from django.utils.text import slugify

from apps.accounts.models import Organization
from apps.bible.models import Character, Location, Prop, WorldBible
from apps.jobs.models import Job
from apps.projects.models import NarrativeContract, NarrativeEvent, Project, Season
from apps.story.models import Beat, BeatTake, Episode, Scene, ScenePlan, Script, Segmentation, Shot, ShotTake
from apps.projects.beat_normalizer import normalize_beats, speaker_label, _speaker_occurrences
from apps.projects.character_resolver import CharacterResolver, identity_token, normalize_bible_payload
from apps.projects.story_normalizer import bible_errors, normalize_story_bible, script_conversation_errors


def _ensure_org(name: str) -> Organization:
    slug = slugify(name) or "studio"
    org, _ = Organization.objects.get_or_create(slug=slug, defaults={"name": name})
    return org


def assist_concept(*, idea: str, delivery: str = "storytell") -> dict:
    idea = str(idea or "").strip()
    if not idea:
        raise ValueError("Décris d'abord ton idée de départ")
    from agents.backends import get_text

    raw = get_text().generate_json(
        system=(
            "Tu es l'assistant de conception narrative de StudioBililingi. Transforme une idée utilisateur en concept "
            "clair et fidèle SANS gonfler artificiellement l'histoire. Réponds en JSON avec exactement: "
            "title, concept, genre, tone, story_type, recommended_episode_count, events, ending_intent. "
            "events est une liste chronologique de faits/actions concrets présents ou directement impliqués par l'idée. "
            "recommended_episode_count est le nombre NATUREL d'épisodes: une idée courte, linéaire, avec un seul trajet "
            "ou objectif doit généralement rester à 1 épisode. N'ajoute ni antagoniste, twist, catastrophe, mystère, "
            "romance ou enjeu majeur absent de l'idée. Tu peux enrichir les détails sensoriels et l'intention, mais pas "
            "changer la prémisse. Le concept final doit être exploitable par un scénariste et rester concis. "
            f"Le mode de livraison prévu est {delivery}; il influence la forme, jamais l'intrigue. Français naturel."
        ),
        user=idea,
    )
    if not isinstance(raw, dict):
        raise RuntimeError("L'assistant concept n'a pas retourné une réponse structurée")
    events = [str(item).strip() for item in (raw.get("events") or []) if str(item).strip()]
    try:
        count = max(1, min(50, int(raw.get("recommended_episode_count") or 1)))
    except (TypeError, ValueError):
        count = 1
    return {
        "title": str(raw.get("title") or "").strip(),
        "concept": str(raw.get("concept") or idea).strip(),
        "genre": str(raw.get("genre") or "").strip(),
        "tone": str(raw.get("tone") or "").strip(),
        "story_type": str(raw.get("story_type") or "").strip(),
        "recommended_episode_count": count,
        "events": events,
        "ending_intent": str(raw.get("ending_intent") or "").strip(),
    }


def persist_narrative_contract(
    project: Project,
    *,
    events: list[str],
    story_type: str = "",
    recommended_episode_count: int = 1,
    point_of_view: str | None = None,
) -> NarrativeContract:
    if point_of_view not in {choice for choice, _ in NarrativeContract.PointOfView.choices}:
        point_of_view = (
            NarrativeContract.PointOfView.DIALOGUE
            if project.delivery in {"conversation", "rencontre"}
            else NarrativeContract.PointOfView.THIRD_PERSON
        )
    contract, _ = NarrativeContract.objects.update_or_create(
        project=project,
        defaults={
            "point_of_view": point_of_view,
            "narrator": "external" if point_of_view == NarrativeContract.PointOfView.THIRD_PERSON else "none",
            "tense": "present",
            "story_type": str(story_type or "")[:40],
            "recommended_episode_count": max(1, min(50, int(recommended_episode_count or 1))),
            "rules": {
                "no_repetition": True,
                "no_moral_filler": True,
                "one_new_story_information_per_beat": True,
                "scene_changes_on_location_or_time": True,
            },
            "locked": True,
        },
    )
    contract.events.all().delete()
    NarrativeEvent.objects.bulk_create([
        NarrativeEvent(
            contract=contract,
            key=f"EV{index:02d}",
            position=index,
            description=str(description).strip(),
        )
        for index, description in enumerate(events, start=1)
        if str(description).strip()
    ])
    return contract


def narrative_contract_payload(project: Project) -> dict:
    try:
        contract = project.narrative_contract
    except NarrativeContract.DoesNotExist:
        return {}
    return {
        "point_of_view": contract.point_of_view,
        "narrator": contract.narrator,
        "tense": contract.tense,
        "story_type": contract.story_type,
        "recommended_episode_count": contract.recommended_episode_count,
        "rules": contract.rules,
        "events": [
            {
                "key": event.key,
                "position": event.position,
                "description": event.description,
                "episode_number": event.episode_number,
                "status": event.status,
            }
            for event in contract.events.all()
        ],
    }


def project_constraints_payload(project: Project) -> dict:
    return {
        "genre": project.genre,
        "subgenre": project.subgenre,
        "setting": project.setting,
        "episode_count_target": project.episode_count_target,
        "episode_duration_seconds": project.episode_duration_seconds,
        "delivery": project.delivery,
        "visual_style": project.visual_style,
    }


def create_project(*, title: str, concept: str, genre: str = "", subgenre: str = "", setting: str = "", tone: str = "", ending_intent: str = "", episode_count_target: int | None = None, episode_duration_seconds: int | None = None, delivery: str = "storytell", visual_style: str = Project.VisualStyle.REALISTIC, organization_name: str = "Studio") -> Project:
    org = _ensure_org(organization_name)
    base = slugify(title) or "projet"
    slug = base
    n = 2
    while Project.objects.filter(organization=org, slug=slug).exists():
        slug = f"{base}-{n}"
        n += 1
    project = Project.objects.create(
        organization=org, title=title, slug=slug, concept=concept,
        genre=genre, subgenre=subgenre, setting=setting, tone=tone, ending_intent=ending_intent, episode_count_target=episode_count_target, episode_duration_seconds=episode_duration_seconds, delivery=delivery, visual_style=visual_style, status=Project.Status.ACTIVE,
    )
    Season.objects.create(project=project, number=1, title="Saison 1", premise=concept[:400])
    return project


def _words(text: str) -> list[str]:
    return [w for w in re.split(r"\s+", text.strip()) if w]


def seed_bible(concept: str) -> dict:
    short = concept.strip()[:80] or "Série sans titre"
    return {
        "version": 1, "logline": short, "tone": "dramatique, immédiat", "locked": False,
        "characters": [
            {"id": "protag", "name": "Awa", "role": "protagoniste", "want": "protéger ce qui reste", "need": "accepter l'aide", "look": "30 ans, tresses courtes, veste usée", "voice": "calme", "locked": False},
            {"id": "antag", "name": "Malo", "role": "antagoniste", "want": "contrôler la version officielle", "need": "ne plus mentir", "look": "costume clair", "voice": "poli", "locked": False},
        ],
        "locations": [{"id": "quai", "name": "Quai de nuit", "look": "lampadaires jaunes, eau noire", "time_of_day": "nuit", "locked": False}],
        "props": [{"id": "carnet", "name": "Carnet rouge", "look": "couverture abîmée", "story_function": "preuve", "locked": False}],
        "source": "stub-seed", "concept": concept,
    }


def seed_season_plan(concept: str) -> list[dict]:
    return [
        {"number": 1, "title": "La preuve", "logline": "Awa trouve le carnet. Quelqu'un la suit.", "function_in_arc": "déclencheur"},
        {"number": 2, "title": "La version officielle", "logline": "Malo propose un marché. Awa refuse.", "function_in_arc": "premier obstacle"},
        {"number": 3, "title": "Le quai", "logline": "Échange de nuit. Le carnet change de main.", "function_in_arc": "point médian"},
        {"number": 4, "title": "Ce qui reste", "logline": "Awa choisit la vérité. Le prix est immédiat.", "function_in_arc": "climax"},
    ]


def _fit_model_text(model, field_name: str, value) -> str:
    """Bound generated text to the database field instead of trusting the LLM."""
    text = str(value or "").strip()
    field = model._meta.get_field(field_name)
    max_length = getattr(field, "max_length", None)
    return text[:max_length] if max_length else text


def _fit_slug(model, value, fallback: str) -> str:
    field = model._meta.get_field("key")
    raw = slugify(str(value or "")) or fallback
    return raw[: field.max_length].rstrip("-") or fallback


def persist_bible(project: Project, payload: dict) -> WorldBible:
    payload = normalize_bible_payload(payload)
    version = (project.bibles.first().version + 1) if project.bibles.exists() else 1
    bible = WorldBible.objects.create(project=project, version=version, payload=payload, locked=False)
    for item in payload.get("characters", []):
        Character.objects.update_or_create(
            project=project,
            key=_fit_slug(Character, item.get("id") or item.get("name"), "perso"),
            defaults={
                "bible": bible,
                "name": _fit_model_text(Character, "name", item.get("name", "Sans nom")) or "Sans nom",
                "role": _fit_model_text(Character, "role", item.get("role", "")),
                "want": str(item.get("want") or ""),
                "need": str(item.get("need") or ""),
                "look": str(item.get("look") or ""),
                "voice": str(item.get("voice") or ""),
                "locked": False,
            },
        )
    for item in payload.get("locations", []):
        Location.objects.update_or_create(
            project=project,
            key=_fit_slug(Location, item.get("id") or item.get("name"), "lieu"),
            defaults={
                "bible": bible,
                "name": _fit_model_text(Location, "name", item.get("name", "Lieu")) or "Lieu",
                "look": str(item.get("look") or ""),
                "time_of_day": _fit_model_text(Location, "time_of_day", item.get("time_of_day", "")),
                "locked": False,
            },
        )
    for item in payload.get("props", []):
        Prop.objects.update_or_create(
            project=project,
            key=_fit_slug(Prop, item.get("id") or item.get("name"), "objet"),
            defaults={
                "bible": bible,
                "name": _fit_model_text(Prop, "name", item.get("name", "Objet")) or "Objet",
                "look": str(item.get("look") or ""),
                "story_function": _fit_model_text(Prop, "story_function", item.get("story_function", "")),
                "locked": False,
            },
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
            defaults={
                "title": _fit_model_text(Episode, "title", row["title"]) or f"Épisode {row['number']}",
                "logline": str(row["logline"] or "").strip(),
                "function_in_arc": _fit_model_text(Episode, "function_in_arc", row.get("function_in_arc", "")),
                "status": Episode.Status.OUTLINED,
            },
        )
        created.append(episode)
    return created


def seed_script(episode: Episode) -> str:
    """Last-resort script that still respects the project's delivery mode."""
    project = episode.season.project
    title = episode.title
    logline = episode.logline
    if project.delivery == "conversation":
        return (
            f"INT./EXT. - SCENE DE {title.upper()} - JOUR/NUIT\n"
            f"PROTAGONISTE : {logline}\n"
            "AUTRE : Qu'est-ce que tu vas faire maintenant ?\n"
            "PROTAGONISTE : Je vais vérifier par moi-même."
        )
    if project.delivery == "voix_off":
        return f"VOIX OFF : {logline}\nIMAGE : Une action visuelle concrète révèle l'enjeu de {title}."
    if project.delivery == "rencontre":
        return (
            f"SCENE - {title}\n"
            "Les deux personnages se font face. Un silence.\n"
            f"PROTAGONISTE : {logline}\n"
            "AUTRE : Alors montre-moi."
        )
    return f"{title}. {logline}"


def segment_text(text: str, target: int = 24) -> list[str]:
    """Legacy fallback: split on sentence boundaries, never every N words."""
    sentences = [s.strip() for s in re.split(r"(?<=[.!?…])\\s+", text.strip()) if s.strip()]
    chunks, current = [], []
    for sentence in sentences:
        candidate = " ".join(current + [sentence]).strip()
        if current and len(_words(candidate)) > 32:
            chunks.append(" ".join(current))
            current = [sentence]
        else:
            current.append(sentence)
    if current:
        chunks.append(" ".join(current))
    return chunks


def _entity_keys(value) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        return [value]
    keys = []
    for item in value:
        if isinstance(item, dict):
            key = item.get("id") or item.get("key") or item.get("name")
        else:
            key = item
        if key:
            keys.append(str(key))
    return keys


def _scene_contract_errors(rows: list[dict]) -> list[str]:
    errors = []
    locations_by_scene: dict[int, set[str]] = {}
    scene_by_location_run = None
    previous_location = None
    for position, row in enumerate(rows, start=1):
        try:
            scene_index = int(row.get("scene_index") or 1)
        except (TypeError, ValueError):
            scene_index = 1
        raw_location = row.get("location_id") or row.get("location")
        if isinstance(raw_location, dict):
            raw_location = raw_location.get("id") or raw_location.get("key") or raw_location.get("name")
        location = str(raw_location or "").strip()
        if location:
            locations_by_scene.setdefault(scene_index, set()).add(location)
            if previous_location and location != previous_location and scene_by_location_run == scene_index:
                errors.append(
                    f"Beat {position}: changement de lieu {previous_location} -> {location} sans nouvelle scène"
                )
            previous_location = location
            scene_by_location_run = scene_index
    for scene_index, locations in locations_by_scene.items():
        if len(locations) > 1:
            errors.append(
                f"Scène {scene_index}: plusieurs lieux incompatibles dans la même scène ({', '.join(sorted(locations))})"
            )
    return errors


@transaction.atomic
def persist_beats(episode: Episode, chunks: list, *, script: Script | None = None, scene_plan: ScenePlan | None = None) -> list[Beat]:
    """Persist a new immutable segmentation version.

    Previous scripts/beats are preserved. Structured segmenter metadata is
    resolved against the locked project bible instead of being discarded.
    """
    project = episode.season.project
    rows = [{"text": row} if isinstance(row, str) else dict(row) for row in chunks]
    contract_errors = _scene_contract_errors(rows)
    if contract_errors:
        raise ValueError("Segmentation refusée: " + "; ".join(contract_errors))
    script = script or episode.scripts.order_by("-version").first()
    if script is None:
        # Compatibility for direct/legacy callers. The production pipeline
        # always supplies the canonical screenplay explicitly.
        script = Script.objects.create(
            episode=episode,
            version=episode.scripts.count() + 1,
            fountain="\n".join(str(row.get("text") or "") for row in rows),
            payload={"source": "legacy-segmentation"},
        )
    if scene_plan is None:
        scene_plan = script.scene_plans.filter(locked=True).order_by("-version").first()
    if scene_plan is None:
        # Legacy tests/tools can still persist beats without a Scene Plan, but
        # normal run_segment always provides the locked production plan.
        segmentation = None
    else:
        latest_segmentation = script.segmentations.order_by("-version").first()
        segmentation = Segmentation.objects.create(
            episode=episode,
            script=script,
            scene_plan=scene_plan,
            version=(latest_segmentation.version + 1) if latest_segmentation else 1,
            payload=rows,
        )
    created = []
    scenes: dict[int, Scene] = {}
    resolver = CharacterResolver(project)

    for index, row in enumerate(rows):
        text = str(row.get("text") or "").strip()
        if not text:
            continue
        raw_scene_index = row.get("scene_index") or 1
        try:
            scene_index = int(raw_scene_index)
        except (TypeError, ValueError):
            scene_index = 1
        scene = scenes.get(scene_index)
        if scene is None:
            scene = Scene.objects.create(
                episode=episode,
                script=script,
                segmentation=segmentation,
                index=scene_index,
                heading=_fit_model_text(Scene, "heading", row.get("scene_heading") or row.get("heading") or ""),
                summary=str(row.get("scene_summary") or ""),
                time_of_day=_fit_model_text(Scene, "time_of_day", row.get("time_of_day") or ""),
                lighting=str(row.get("lighting") or ""),
                continuity_state=row.get("continuity") if isinstance(row.get("continuity"), dict) else {},
            )
            scenes[scene_index] = scene

        loc_key = row.get("location_id") or row.get("location")
        if isinstance(loc_key, dict):
            loc_key = loc_key.get("id") or loc_key.get("key") or loc_key.get("name")
        location = project.locations.filter(key=loc_key).first() if loc_key else None
        if location is None and loc_key:
            location = project.locations.filter(name__iexact=str(loc_key)).first()
        if location and scene.location_id is None:
            scene.location = location
            scene.save(update_fields=["location"])

        speaker = resolver.resolve(row.get("speaker_id"))
        if speaker is None and row.get("dialogue"):
            speaker_name = _canonical_speaker_from_dialogue(
                str(row.get("dialogue") or "") or str(row.get("text") or ""),
                resolver,
            )
            speaker = resolver.resolve(speaker_name) if speaker_name else None

        event_key = str(row.get("event_id") or "").strip()
        narrative_event = None
        if event_key:
            narrative_event = NarrativeEvent.objects.filter(
                contract__project=project,
                key=event_key,
                episode_number=episode.number,
            ).first()
            if narrative_event is None:
                raise ValueError(f"Événement narratif inconnu pour E{episode.number}: {event_key}")

        beat = Beat.objects.create(
            episode=episode,
            script=script,
            segmentation=segmentation,
            scene=scene,
            narrative_event=narrative_event,
            index=index,
            text=text,
            word_count=len(_words(text)),
            duration_seconds=row.get("duration_seconds") or 8,
            location=location,
            camera=row.get("camera") if isinstance(row.get("camera"), dict) else {},
            continuity=row.get("continuity") if isinstance(row.get("continuity"), dict) else {},
            emotion=_fit_model_text(Beat, "emotion", row.get("emotion") or ""),
            dialogue=str(row.get("dialogue") or ""),
            speaker_id=(
                project.characters.filter(key=speaker.key).values_list("id", flat=True).first()
                if speaker else None
            ),
            video_prompt=str(row.get("video_prompt") or text),
            negative_prompt=str(row.get("negative_prompt") or ""),
            backend=_fit_model_text(Beat, "backend", row.get("backend") or "google-veo-3.1"),
            status=Beat.Status.DRAFT,
        )

        char_keys = resolver.canonical_keys(row.get("character_ids") or row.get("characters"))
        prop_keys = _entity_keys(row.get("prop_ids") or row.get("props"))
        characters = list(project.characters.filter(key__in=char_keys))
        props = list(project.props.filter(key__in=prop_keys))
        beat.characters.set(characters)
        beat.props.set(props)
        scene.characters.add(*characters)
        scene.props.add(*props)
        created.append(beat)

    event_ids = {beat.narrative_event_id for beat in created if beat.narrative_event_id}
    if event_ids:
        NarrativeEvent.objects.filter(id__in=event_ids).update(status=NarrativeEvent.Status.SCRIPTED)

    episode.status = Episode.Status.SEGMENTED
    episode.save(update_fields=["status"])
    Job.objects.create(
        project=project,
        kind=Job.Kind.SEGMENT,
        status=Job.Status.SUCCEEDED,
        agent_role="beat_segmenter",
        backend="stub-text",
        result={"episode_id": episode.id, "script_id": script.id, "segmentation_id": segmentation.id if segmentation else None, "beats": len(created)},
    )
    return created


def _episode_rows(raw: dict, concept: str) -> list[dict]:
    rows = raw.get("episodes") if isinstance(raw, dict) else None
    cleaned = []
    for i, row in enumerate(rows or [], start=1):
        if not isinstance(row, dict):
            continue
        cleaned.append({
            "number": int(row.get("number") or i),
            "title": row.get("title") or f"Épisode {i}",
            "logline": row.get("logline") or concept[:180],
            "function_in_arc": row.get("function_in_arc") or "",
            "events": [str(event).strip() for event in (row.get("events") or []) if str(event).strip()],
        })
    return cleaned or seed_season_plan(concept)


def _validate_episode_plan(rows: list[dict]) -> list[str]:
    errors = []
    seen = {}
    for row in rows:
        for event in row.get("events") or []:
            token = re.sub(r"[^a-z0-9]+", " ", event.lower()).strip()
            if not token:
                continue
            if token in seen:
                errors.append(
                    f"Événement dupliqué entre E{seen[token]} et E{row['number']}: {event}"
                )
            else:
                seen[token] = row["number"]
    return errors


def run_showrunner(project: Project) -> dict:
    try:
        from agents.roles.showrunner import Showrunner
        contract = narrative_contract_payload(project)
        project_constraints = project_constraints_payload(project)
        bible = project.bibles.first()
        raw = Showrunner().plan(
            project.concept
            + "\n\nCONTRAINTES PROJET VERROUILLEES:\n" + str(project_constraints)
            + ("\n\nNARRATIVE CONTRACT VERROUILLE:\n" + str(contract) if contract else ""),
            delivery=project.delivery,
            bible=bible.payload if bible else None,
        )
    except Exception as exc:
        raw = {"_error": str(exc)}
    if raw.get("tone") and not project.tone:
        # Generated prose must never be allowed to overflow compact DB fields.
        project.tone = _fit_model_text(Project, "tone", raw["tone"])
        project.save(update_fields=["tone"])
    rows = _episode_rows(raw, project.concept)
    if raw.get("_error"):
        raise RuntimeError(f"Le showrunner n'a pas pu générer le plan de saison: {raw['_error']}")
    plan_errors = _validate_episode_plan(rows)
    if plan_errors:
        raise RuntimeError("Plan de saison incohérent: " + "; ".join(plan_errors))
    episodes = persist_episodes(project, rows)
    try:
        contract = project.narrative_contract
    except NarrativeContract.DoesNotExist:
        contract = NarrativeContract.objects.create(
            project=project,
            point_of_view=(
                NarrativeContract.PointOfView.DIALOGUE
                if project.delivery in {"conversation", "rencontre"}
                else NarrativeContract.PointOfView.THIRD_PERSON
            ),
            narrator="none" if project.delivery in {"conversation", "rencontre"} else "external",
            tense="present",
            story_type="",
            recommended_episode_count=project.episode_count_target or len(rows) or 1,
            rules={
                "no_repetition": True,
                "no_moral_filler": True,
                "one_new_story_information_per_beat": True,
                "scene_changes_on_location_or_time": True,
            },
            locked=True,
        )
    planned = []
    position = 1
    for row in rows:
        for description in row.get("events") or []:
            planned.append(NarrativeEvent(
                contract=contract,
                key=f"EV{position:02d}",
                position=position,
                description=description,
                episode_number=row["number"],
                status=NarrativeEvent.Status.PLANNED,
            ))
            position += 1
    if planned:
        if contract.events.filter(beats__isnull=False).exists():
            raise RuntimeError("Le Narrative Contract est déjà consommé par des beats; refuse de réécrire le ledger.")
        contract.events.all().delete()
        NarrativeEvent.objects.bulk_create(planned)
    # The ledger is now assigned to concrete episodes and becomes the canonical
    # event contract consumed by screenwriting and segmentation.
    return {"agent": raw, "episodes": [e.id for e in episodes]}


def _usable_bible(raw) -> bool:
    return (
        isinstance(raw, dict)
        and isinstance(raw.get("characters"), list)
        and any(isinstance(item, dict) and str(item.get("name") or "").strip() for item in raw["characters"])
    )


def run_bible(project: Project) -> WorldBible:
    from agents.roles.bible import WorldBibleAgent

    agent = WorldBibleAgent()
    last_error = ""
    raw = None
    for attempt in range(2):
        try:
            raw = agent.draft(project.concept, delivery=project.delivery, project_constraints=project_constraints_payload(project))
        except Exception as exc:
            last_error = str(exc)
            if attempt == 0:
                continue
            raise RuntimeError(f"La génération de la bible a échoué: {exc}") from exc
        if _usable_bible(raw):
            break
        last_error = (
            "réponse structurée invalide: characters doit être un tableau non vide "
            "d'objets contenant chacun un name"
        )
    if not _usable_bible(raw):
        raise RuntimeError(
            "La génération de la bible n'a retourné aucun personnage exploitable après correction automatique: "
            + last_error
        )

    payload = normalize_story_bible(raw, delivery=project.delivery)
    errors = bible_errors(payload, delivery=project.delivery)
    if errors:
        # One semantic repair attempt: regenerate from the source concept rather
        # than persisting a malformed/generic bible.
        try:
            repaired = agent.draft(
                project.concept
                + "\n\nCONTRAINTES DE CORRECTION OBLIGATOIRES: "
                + "; ".join(errors),
                delivery=project.delivery,
                project_constraints=project_constraints_payload(project),
            )
        except Exception as exc:
            raise RuntimeError(f"La correction automatique de la bible a échoué: {exc}") from exc
        if _usable_bible(repaired):
            payload = normalize_story_bible(repaired, delivery=project.delivery)
            errors = bible_errors(payload, delivery=project.delivery)
        if errors:
            raise RuntimeError("Bible refusée après correction automatique: " + "; ".join(errors))

    payload.setdefault("project_id", str(project.id))
    payload["locked"] = False
    return persist_bible(project, payload)


def lock_bible(project: Project) -> WorldBible:
    bible = project.bibles.first()
    if bible is None:
        raise ValueError("Pas de bible à verrouiller")
    bible.locked = True
    bible.save(update_fields=["locked"])
    project.characters.update(locked=True)
    project.locations.update(locked=True)
    project.props.update(locked=True)
    return bible


def _canonical_continuity(episode: Episode) -> list[dict]:
    """Build continuity only from earlier canonical episode versions."""
    rows = []
    previous = episode.season.episodes.filter(number__lt=episode.number).order_by("number")
    for item in previous:
        script = item.scripts.order_by("-version").first()
        if script is None:
            continue
        scenes = list(
            script.scenes.order_by("index").values("index", "heading", "summary", "time_of_day")
        )
        beats = list(
            script.beats.order_by("index").values_list("text", flat=True)
        )
        rows.append({
            "episode": item.number,
            "title": item.title,
            "logline": item.logline,
            "scenes": scenes,
            "established_events": beats,
        })
    return rows


def write_script(episode: Episode) -> Script:
    project = episode.season.project
    bible = project.bibles.first()
    if bible is None or not bible.locked:
        raise ValueError("Verrouille la bible avant d'écrire les scripts")
    try:
        from agents.roles.screenwriter import Screenwriter
        raw = Screenwriter().write(
            concept=project.concept, bible=bible.payload,
            episode={"number": episode.number, "title": episode.title, "logline": episode.logline},
            form=project.delivery,
            continuity=_canonical_continuity(episode),
            narrative_contract=narrative_contract_payload(project),
            project_constraints=project_constraints_payload(project),
        )
    except Exception as exc:
        raise RuntimeError(f"L'écriture du script a échoué: {exc}") from exc
    fountain = raw.get("fountain") if isinstance(raw, dict) else None
    if not fountain:
        raise RuntimeError("Le scénariste n'a retourné aucun script exploitable")
    if project.delivery == "conversation":
        errors = script_conversation_errors(fountain, bible.payload)
        if errors:
            try:
                raw = Screenwriter().write(
                    concept=project.concept,
                    bible=bible.payload,
                    episode={"number": episode.number, "title": episode.title, "logline": episode.logline},
                    form=project.delivery,
                    continuity=_canonical_continuity(episode),
                    narrative_contract=narrative_contract_payload(project),
                    project_constraints=project_constraints_payload(project),
                )
            except Exception as exc:
                raise RuntimeError(f"La correction du script conversation a échoué: {exc}") from exc
            fountain = raw.get("fountain") if isinstance(raw, dict) else None
            errors = script_conversation_errors(fountain or "", bible.payload)
            if not fountain or errors:
                raise RuntimeError("Script conversation refusé: " + "; ".join(errors or ["script vide"]))
    script = Script.objects.create(episode=episode, version=episode.scripts.count() + 1, fountain=fountain, payload=raw if isinstance(raw, dict) else {"fountain": fountain})
    episode.status = Episode.Status.SCRIPTED
    episode.save(update_fields=["status"])
    Job.objects.create(project=project, kind=Job.Kind.SCRIPT, status=Job.Status.SUCCEEDED, agent_role="screenwriter", result={"episode_id": episode.id, "script_id": script.id})
    return script


def _script_speaker_labels(script_text: str) -> list[str]:
    """Extract only screenplay dialogue labels from the beginning of lines.

    Fountain metadata such as Title:, Author: and Episode: must never become
    characters. A label is accepted only when it looks like a real dialogue
    cue: uppercase (including underscore style) and followed by spoken text.
    """
    blocked = {
        "title", "author", "authors", "episode", "credit", "source", "draftdate",
        "contact", "copyright", "notes", "scene", "image", "voixoff", "transition",
    }
    labels: list[str] = []
    for raw_line in str(script_text or "").splitlines():
        line = raw_line.strip()
        match = re.match(r"^([^:\n]{2,60})\s*:\s*(\S.*)$", line)
        if not match:
            continue
        label = match.group(1).strip().strip('"')
        token = identity_token(label)
        if not token or token in blocked:
            continue
        # Dialogue cues emitted by our writers are uppercase. This rejects
        # prose such as "C'est la première phase, Claire : les charognards..."
        # and Fountain front matter such as "Title: ...".
        letters = [ch for ch in label if ch.isalpha()]
        if not letters or not all(ch.isupper() for ch in letters):
            continue
        clean = re.sub(r"^(DR\.?|DOCTEUR|M\.?|MME)\s+", "", label, flags=re.I)
        parts = [part for part in re.split(r"[ _]+", clean) if part]
        if not (1 <= len(parts) <= 5):
            continue
        labels.append(label)
    return list(dict.fromkeys(labels))


def _ensure_script_speakers(project: Project, bible: WorldBible | None, script_text: str) -> None:
    """Promote legitimate named dialogue speakers into the canonical bible."""
    if bible is None:
        return
    payload = dict(bible.payload or {})
    characters = list(payload.get("characters") or [])
    resolver = CharacterResolver(project)
    known_tokens = {
        identity_token(item.get("name"))
        for item in characters
        if isinstance(item, dict) and item.get("name")
    }
    changed = False

    for label in _script_speaker_labels(script_text):
        if resolver.resolve(label):
            continue
        token = identity_token(label)
        if token in known_tokens:
            continue
        clean_name = re.sub(r"^(DR\.?|DOCTEUR|M\.?|MME)\s+", "", label, flags=re.I).strip()
        clean_name = clean_name.replace("_", " ")
        # Preserve accents while converting model-style CLAIRE_MOREAU to a
        # readable canonical display name.
        name = " ".join(part.capitalize() for part in clean_name.split())
        key = slugify(name) or slugify(label)
        if not key:
            continue
        characters.append({
            "id": key,
            "name": name,
            "aliases": [label, label.upper(), name],
            "role": "interlocuteur",
            "want": "",
            "need": "",
            "look": "Apparence à définir et verrouiller avant génération vidéo.",
            "voice": "",
            "locked": bible.locked,
            "source": "screenwriter",
        })
        known_tokens.add(identity_token(name))
        changed = True

    if changed:
        payload["characters"] = characters
        normalized = normalize_bible_payload(payload)
        bible.payload = normalized
        bible.save(update_fields=["payload"])
        for item in normalized.get("characters") or []:
            Character.objects.update_or_create(
                project=project,
                key=_fit_slug(Character, item.get("id") or item.get("name"), "perso"),
                defaults={
                    "bible": bible,
                    "name": _fit_model_text(Character, "name", item.get("name", "Sans nom")) or "Sans nom",
                    "role": _fit_model_text(Character, "role", item.get("role", "")),
                    "want": str(item.get("want") or ""),
                    "need": str(item.get("need") or ""),
                    "look": str(item.get("look") or ""),
                    "voice": str(item.get("voice") or ""),
                    "locked": bible.locked,
                },
            )

def cleanup_generated_script_characters(project: Project) -> int:
    """Remove bogus characters created by the old permissive speaker parser."""
    bogus_tokens = {
        identity_token("Title"), identity_token("Author"), identity_token("Episode"),
        identity_token("C'est la première phase, Claire"),
    }
    qs = project.characters.filter(role="interlocuteur")
    doomed = [
        character.id for character in qs
        if identity_token(character.name) in bogus_tokens
    ]
    if not doomed:
        return 0
    count, _ = project.characters.filter(id__in=doomed).delete()

    bible = project.bibles.first()
    if bible:
        payload = dict(bible.payload or {})
        payload["characters"] = [
            item for item in (payload.get("characters") or [])
            if identity_token(item.get("name")) not in bogus_tokens
        ]
        bible.payload = payload
        bible.save(update_fields=["payload"])
    return count


def _beat_chunks(raw, fallback_text: str) -> list:
    items = raw if isinstance(raw, list) else (raw.get("beats") if isinstance(raw, dict) else None)
    chunks = []
    for item in items or []:
        if isinstance(item, dict):
            row = dict(item)
            if str(row.get("text") or "").strip():
                row["text"] = str(row["text"]).strip()
                chunks.append(row)
        else:
            text = str(item).strip()
            if text:
                chunks.append({"text": text})
    return chunks or [{"text": text} for text in segment_text(fallback_text)]


def _speaker_names(row: dict, project: Project, resolver: CharacterResolver | None = None) -> list[str]:
    return (resolver or CharacterResolver(project)).names_for_row(row)


def _canonical_speaker_from_dialogue(value: str, resolver: CharacterResolver) -> str:
    """Resolve a speaker from any NAME: prefix, including normal title case."""
    for line in str(value or "").splitlines():
        match = re.match(r"^\s*([^:\n]{1,80})\s*:\s*\S", line)
        if not match:
            continue
        resolved = resolver.resolve(match.group(1).strip())
        if resolved:
            return resolved.name
    return ""


def _extract_speaker_label(value: str) -> str:
    """Return an explicit CHARACTER : label found in structured dialogue or beat text."""
    match = re.search(
        r"(?m)(?:^|\\n|[.!?]\\s+)([A-ZÀ-ÖØ-Þ][A-ZÀ-ÖØ-Þ0-9 _'’.-]{1,40})\\s*:",
        value or "",
    )
    return match.group(1).strip() if match else ""


def _normalize_conversation_beats(chunks: list, *, project: Project) -> list:
    """Preserve/derive speaker labels without inventing a speaker when ambiguous."""
    normalized = []
    for item in chunks:
        row = dict(item)
        dialogue = str(row.get("dialogue") or "").strip()
        text = str(row.get("text") or "").strip()
        if dialogue and not _extract_speaker_label(dialogue):
            label = _extract_speaker_label(text)
            if label:
                row["dialogue"] = f"{label} : {dialogue}"
            else:
                names = _speaker_names(row, project)
                if len(names) == 1:
                    row["dialogue"] = f"{names[0].upper()} : {dialogue}"
        normalized.append(row)
    return normalized


def _segmentation_errors(chunks: list, *, form: str, project: Project) -> list[str]:
    errors = []
    resolver = CharacterResolver(project)
    for i, row in enumerate(chunks, start=1):
        text = str(row.get("text") or "").strip()
        count = len(_words(text))
        if count > 32:
            errors.append(f"beat {i}: {count} mots (>32)")
        if form == "conversation":
            dialogue = str(row.get("dialogue") or "").strip()
            text_value = str(row.get("text") or "").strip()
            labels = _speaker_occurrences(text_value)
            if len(labels) > 1:
                errors.append(f"beat {i}: plusieurs locuteurs dans le même beat")
            if dialogue and len(_speaker_occurrences(dialogue)) > 1:
                errors.append(f"beat {i}: plusieurs locuteurs dans dialogue")
            if dialogue:
                speaker = resolver.resolve(row.get("speaker_id"))
                if speaker is None:
                    explicit = (
                        _canonical_speaker_from_dialogue(dialogue, resolver)
                        or _canonical_speaker_from_dialogue(text_value, resolver)
                    )
                    speaker = resolver.resolve(explicit) if explicit else None
                if speaker is None:
                    names = _speaker_names(row, project, resolver)
                    if len(names) == 1:
                        speaker = resolver.resolve(names[0])
                        if speaker:
                            row["speaker_id"] = speaker.key
                    else:
                        errors.append(f"beat {i}: dialogue sans speaker_id canonique identifiable")
                elif not row.get("speaker_id"):
                    row["speaker_id"] = speaker.key
    return errors


def _semantic_tokens(value: str) -> set[str]:
    stop = {
        "alors", "avec", "avoir", "cette", "comme", "dans", "elle", "elles", "entre", "etre",
        "faire", "leur", "leurs", "mais", "nous", "pour", "plus", "quand", "sans", "sont",
        "tout", "tous", "toute", "toutes", "une", "des", "les", "qui", "que", "sur", "son",
        "ses", "aux", "par", "pas", "est", "et", "du", "de", "la", "le", "un", "au",
    }
    normalized = re.sub(r"[^a-z0-9àâäçéèêëîïôöùûüÿœ]+", " ", str(value or "").lower())
    return {token for token in normalized.split() if len(token) >= 3 and token not in stop}


def _event_redundancy_errors(chunks: list[dict]) -> list[str]:
    """Catch near-duplicate beats inside one event without forbidding visual coverage."""
    errors = []
    by_event: dict[str, list[tuple[int, set[str], str]]] = {}
    for index, row in enumerate(chunks, start=1):
        event_id = str(row.get("event_id") or "").strip()
        text = str(row.get("text") or "").strip()
        if not event_id or not text:
            continue
        tokens = _semantic_tokens(text)
        for previous_index, previous_tokens, previous_text in by_event.get(event_id, []):
            union = tokens | previous_tokens
            similarity = (len(tokens & previous_tokens) / len(union)) if union else 0.0
            if similarity >= 0.72:
                errors.append(
                    f"{event_id}: beats {previous_index} et {index} semblent répéter la même information "
                    f"(similarité {similarity:.0%})"
                )
        by_event.setdefault(event_id, []).append((index, tokens, text))
    return errors


def _natural_episode_duration(scene_plan: list[dict]) -> int:
    """Use the validated Scene Plan as the natural per-episode duration budget."""
    total = 0
    for scene in scene_plan:
        try:
            total += max(0, int(scene.get("target_seconds") or 0))
        except (TypeError, ValueError):
            continue
    return total


def _duration_budget_errors(chunks: list[dict], scene_plan: list[dict], *, fixed_episode_target: int | None = None) -> list[str]:
    errors = []
    targets = {}
    for scene in scene_plan:
        try:
            targets[int(scene.get("index"))] = float(scene.get("target_seconds") or 0)
        except (TypeError, ValueError):
            continue
    actual = {index: 0.0 for index in targets}
    for position, row in enumerate(chunks, start=1):
        try:
            scene_index = int(row.get("scene_index"))
            seconds = float(row.get("duration_seconds") or 0)
        except (TypeError, ValueError):
            errors.append(f"beat {position}: durée ou scene_index invalide")
            continue
        if seconds <= 0:
            errors.append(f"beat {position}: duration_seconds doit être positif")
        actual[scene_index] = actual.get(scene_index, 0.0) + max(0.0, seconds)
    for scene_index, target in targets.items():
        if target <= 0:
            continue
        tolerance_ratio = 0.10 if fixed_episode_target else 0.15
        tolerance = max(3.0 if fixed_episode_target else 4.0, target * tolerance_ratio)
        value = actual.get(scene_index, 0.0)
        if abs(value - target) > tolerance:
            errors.append(
                f"scène {scene_index}: beats totalisent {value:g}s pour une cible de {target:g}s (tolérance ±{tolerance:g}s)"
            )
    return errors


def _fit_scene_durations_without_loss(chunks: list[dict], scene_plan: list[dict]) -> list[dict]:
    """Fit beat timings to locked scene targets without rewriting or dropping narrative content."""
    targets = {}
    for scene in scene_plan:
        try:
            index = int(scene.get("index"))
            target = float(scene.get("target_seconds") or 0)
        except (TypeError, ValueError):
            continue
        if target > 0:
            targets[index] = target

    fitted = [dict(row) for row in chunks]
    by_scene = {}
    for row in fitted:
        try:
            scene_index = int(row.get("scene_index"))
            seconds = float(row.get("duration_seconds") or 0)
        except (TypeError, ValueError):
            continue
        if scene_index in targets and seconds > 0:
            by_scene.setdefault(scene_index, []).append(row)

    for scene_index, rows in by_scene.items():
        target = targets[scene_index]
        total = sum(float(row.get("duration_seconds") or 0) for row in rows)
        if total <= 0:
            continue
        scale = target / total
        assigned = 0.0
        for row in rows[:-1]:
            seconds = max(0.1, round(float(row.get("duration_seconds") or 0) * scale, 1))
            row["duration_seconds"] = seconds
            assigned += seconds
        if rows:
            rows[-1]["duration_seconds"] = max(0.1, round(target - assigned, 1))
    return fitted


def _validate_segmented_beats(chunks: list, *, form: str, project: Project, scene_plan: list[dict] | None = None) -> None:
    errors = _segmentation_errors(chunks, form=form, project=project)
    errors.extend(_event_redundancy_errors(chunks))
    if scene_plan:
        errors.extend(_duration_budget_errors(chunks, scene_plan, fixed_episode_target=project.episode_duration_seconds))
    if errors:
        preview = "; ".join(errors[:8])
        raise ValueError(f"Segmentation refusée après correction automatique: {preview}.")


def _canonical_scene_plan_ids(scenes: list[dict], project: Project) -> list[dict]:
    """Resolve common LLM aliases/names to the exact canonical Bible keys."""
    def norm(value) -> str:
        return re.sub(r"[^a-z0-9]+", "", slugify(str(value or "")).replace("-", ""))

    def aliases(qs):
        result = {}
        for entity in qs:
            for value in (entity.key, entity.name):
                token = norm(value)
                if token:
                    result[token] = entity.key
        return result

    location_aliases = aliases(project.locations.all())
    character_aliases = aliases(project.characters.all())
    prop_aliases = aliases(project.props.all())

    def resolve(value, mapping):
        raw = str(value or "").strip()
        if not raw:
            return raw
        return mapping.get(norm(raw), raw)

    normalized = []
    for source in scenes:
        scene = dict(source)
        scene["location_id"] = resolve(scene.get("location_id"), location_aliases)
        scene["character_ids"] = [
            resolve(value, character_aliases) for value in (scene.get("character_ids") or [])
        ]
        scene["prop_ids"] = [
            resolve(value, prop_aliases) for value in (scene.get("prop_ids") or [])
        ]
        normalized.append(scene)
    return normalized


def _scene_plan_errors(
    scenes: list[dict],
    *,
    project: Project,
    episode: Episode,
    expected_events: set[str],
) -> list[str]:
    errors = []
    canonical_locations = set(project.locations.values_list("key", flat=True))
    canonical_characters = set(project.characters.values_list("key", flat=True))
    canonical_props = set(project.props.values_list("key", flat=True))
    seen_indexes = set()
    used_events = set()
    total_seconds = 0

    for position, scene in enumerate(scenes, start=1):
        try:
            index = int(scene.get("index"))
        except (TypeError, ValueError):
            errors.append(f"scène {position}: index invalide")
            continue
        if index in seen_indexes:
            errors.append(f"scene_index dupliqué: {index}")
        seen_indexes.add(index)

        location_id = str(scene.get("location_id") or "").strip()
        if not location_id or location_id not in canonical_locations:
            errors.append(f"scène {index}: location_id canonique invalide: {location_id or 'vide'}")

        character_ids = {str(value).strip() for value in (scene.get("character_ids") or []) if str(value).strip()}
        prop_ids = {str(value).strip() for value in (scene.get("prop_ids") or []) if str(value).strip()}
        unknown_characters = sorted(character_ids - canonical_characters)
        unknown_props = sorted(prop_ids - canonical_props)
        if unknown_characters:
            errors.append(f"scène {index}: personnages inconnus: {', '.join(unknown_characters)}")
        if unknown_props:
            errors.append(f"scène {index}: objets inconnus: {', '.join(unknown_props)}")

        event_ids = {str(value).strip() for value in (scene.get("event_ids") or []) if str(value).strip()}
        unknown_events = sorted(event_ids - expected_events)
        if unknown_events:
            errors.append(f"scène {index}: événements non autorisés: {', '.join(unknown_events)}")
        used_events.update(event_ids)

        try:
            seconds = int(scene.get("target_seconds") or 0)
        except (TypeError, ValueError):
            seconds = 0
        if seconds <= 0:
            errors.append(f"scène {index}: target_seconds doit être positif")
        total_seconds += max(0, seconds)

    missing = sorted(expected_events - used_events)
    if missing:
        errors.append("événements sans scène: " + ", ".join(missing))
    target = project.episode_duration_seconds
    if target:
        target = int(target)
        tolerance = max(10, round(target * 0.25))
        if scenes and abs(total_seconds - target) > tolerance:
            errors.append(
                f"durée du scene plan {total_seconds}s hors cible épisode {target}s (tolérance ±{tolerance}s)"
            )
    return errors


def plan_scenes(episode: Episode, script_text: str, *, persist: bool = True) -> list[dict]:
    project = episode.season.project
    bible = project.bibles.first()
    if bible is None or not bible.locked:
        raise ValueError("Verrouille la bible avant de planifier les scènes")
    contract = narrative_contract_payload(project)
    expected_events = {
        event["key"] for event in contract.get("events", [])
        if event.get("episode_number") == episode.number
    }
    if not expected_events:
        raise ValueError(f"Aucun événement narratif canonique assigné à E{episode.number}")

    from agents.roles.scene_planner import ScenePlanner

    try:
        raw = ScenePlanner().plan(
            script=script_text,
            episode={
                "number": episode.number,
                "title": episode.title,
                "logline": episode.logline,
                "function_in_arc": episode.function_in_arc,
            },
            bible=bible.payload,
            narrative_contract=contract,
            project_constraints=project_constraints_payload(project),
        )
    except Exception as exc:
        raise RuntimeError(f"La planification des scènes a échoué: {exc}") from exc

    scenes = raw.get("scenes") if isinstance(raw, dict) else None
    scenes = [dict(scene) for scene in (scenes or []) if isinstance(scene, dict)]
    if not scenes:
        raise RuntimeError("Le Scene Planner n'a retourné aucune scène exploitable")
    scenes = _canonical_scene_plan_ids(scenes, project)
    errors = _scene_plan_errors(
        scenes,
        project=project,
        episode=episode,
        expected_events=expected_events,
    )
    if errors:
        raise ValueError("Scene Plan refusé: " + "; ".join(errors))
    if persist:
        script = episode.scripts.order_by("-version").first()
        if script is None:
            raise ValueError("Écris le script avant de planifier les scènes")
        latest_plan = script.scene_plans.order_by("-version").first()
        version = (latest_plan.version + 1) if latest_plan else 1
        ScenePlan.objects.create(episode=episode, script=script, version=version, payload=scenes, locked=False)
    return scenes


def lock_scene_plan(episode: Episode, scene_plan_id: int | None = None) -> ScenePlan:
    script = episode.scripts.order_by("-version").first()
    if script is None:
        raise ValueError("Écris le script avant de verrouiller le Scene Plan")
    plans = script.scene_plans.all()
    plan = plans.filter(pk=scene_plan_id).first() if scene_plan_id else plans.order_by("-version").first()
    if plan is None:
        raise ValueError("Génère d'abord un Scene Plan")
    project = episode.season.project
    contract = narrative_contract_payload(project)
    expected_events = {event["key"] for event in contract.get("events", []) if event.get("episode_number") == episode.number}
    errors = _scene_plan_errors(plan.payload, project=project, episode=episode, expected_events=expected_events)
    if errors:
        raise ValueError("Scene Plan refusé: " + "; ".join(errors))
    with transaction.atomic():
        plans.exclude(pk=plan.pk).filter(locked=True).update(locked=False)
        plan.locked = True
        plan.save(update_fields=["locked"])
    return plan


def _beat_scene_plan_errors(chunks: list[dict], scene_plan: list[dict]) -> list[str]:
    errors = []
    planned = {}
    for scene in scene_plan:
        try:
            index = int(scene.get("index"))
        except (TypeError, ValueError):
            continue
        planned[index] = {
            "location_id": str(scene.get("location_id") or "").strip(),
            "time_of_day": str(scene.get("time_of_day") or "").strip().casefold(),
            "event_ids": {str(value).strip() for value in (scene.get("event_ids") or []) if str(value).strip()},
        }

    for position, row in enumerate(chunks, start=1):
        try:
            scene_index = int(row.get("scene_index"))
        except (TypeError, ValueError):
            errors.append(f"beat {position}: scene_index invalide")
            continue
        scene = planned.get(scene_index)
        if scene is None:
            errors.append(f"beat {position}: scène {scene_index} absente du Scene Plan")
            continue
        location_id = str(row.get("location_id") or "").strip()
        # Both the Scene Plan and segmenter may vary only in casing while
        # referring to the same canonical key. Compare canonical identifiers
        # case-insensitively; persist_beats resolves the actual DB entity.
        if location_id.casefold() != scene["location_id"].casefold():
            errors.append(
                f"beat {position}: location_id {location_id or 'vide'} différent du Scene Plan {scene['location_id']}"
            )
        time_of_day = str(row.get("time_of_day") or "").strip().casefold()
        if scene["time_of_day"] and time_of_day != scene["time_of_day"]:
            errors.append(f"beat {position}: time_of_day différent du Scene Plan")
        event_id = str(row.get("event_id") or "").strip()
        if event_id not in scene["event_ids"]:
            errors.append(f"beat {position}: {event_id or 'event_id vide'} non autorisé dans scène {scene_index}")
    return errors


def run_segment(episode: Episode, script_text: str | None = None) -> list[Beat]:
    latest = episode.scripts.order_by("-version").first()
    text = script_text or (latest.fountain if latest else None)
    if not text:
        raise ValueError("Écris le script avant de lancer la segmentation")

    project = episode.season.project
    bible = project.bibles.first()
    _ensure_script_speakers(project, bible, text)
    bible_payload = bible.payload if bible else {}
    script = latest
    if script is None:
        raise ValueError("Écris le script avant de lancer la segmentation")
    stored_plan = script.scene_plans.filter(locked=True).order_by("-version").first()
    if stored_plan is None:
        raise ValueError("Verrouille le Scene Plan avant de découper en beats")
    scene_plan = stored_plan.payload

    try:
        from agents.roles.segmenter import BeatSegmenter
        segmenter = BeatSegmenter()
        contract_payload = narrative_contract_payload(project)
        raw = segmenter.segment(
            text,
            form=project.delivery,
            bible=bible_payload,
            narrative_contract=contract_payload,
            scene_plan=scene_plan,
        )
    except Exception as exc:
        raise RuntimeError(f"La segmentation a échoué: {exc}") from exc

    chunks = _beat_chunks(raw, "")
    if not chunks:
        raise RuntimeError("Le segmenter n'a retourné aucun beat exploitable")
    resolver = CharacterResolver(project)
    chunks = normalize_beats(
        chunks,
        form=project.delivery,
        resolve_character_names=resolver.names_for_row,
    )

    errors = _segmentation_errors(chunks, form=project.delivery, project=project)
    if errors:
        feedback = (
            "La passe précédente est invalide. Corrige TOUT le découpage en conservant l'histoire et les scènes. "
            "Pour chaque dialogue, fournis speaker_id avec l'id canonique exact du locuteur ET mets explicitement "
            "NOM : réplique dans dialogue. character_ids contient les personnages visibles et ne remplace jamais "
            "speaker_id. Un beat est une unité NARRATIVE: conserve ensemble une action, une intention ou un échange cohérent, "
            "même au-delà de 24/32 mots. Ne le raccourcis jamais uniquement pour une limite vidéo; la production le divisera en shots. "
            "Erreurs détectées: " + "; ".join(errors)
        )
        try:
            raw = segmenter.segment(
                text,
                form=project.delivery,
                bible=bible_payload,
                feedback=feedback,
                narrative_contract=contract_payload,
                scene_plan=scene_plan,
            )
        except Exception as exc:
            raise RuntimeError(f"La correction automatique de la segmentation a échoué: {exc}") from exc
        chunks = _beat_chunks(raw, "")
        chunks = normalize_beats(
            chunks,
            form=project.delivery,
            resolve_character_names=resolver.names_for_row,
        )

    scene_plan_errors = _beat_scene_plan_errors(chunks, scene_plan)
    if scene_plan_errors:
        raise ValueError("Segmentation hors Scene Plan: " + "; ".join(scene_plan_errors))

    contract_payload = narrative_contract_payload(project)
    expected_events = {
        event["key"] for event in contract_payload.get("events", [])
        if event.get("episode_number") == episode.number
    }
    if expected_events:
        used_events = {str(row.get("event_id") or "").strip() for row in chunks}
        unknown = sorted(used_events - expected_events - {""})
        missing = sorted(expected_events - used_events)
        untagged = [str(i + 1) for i, row in enumerate(chunks) if not str(row.get("event_id") or "").strip()]
        ledger_errors = []
        if unknown:
            ledger_errors.append("event_id inconnus: " + ", ".join(unknown))
        if missing:
            ledger_errors.append("événements non couverts: " + ", ".join(missing))
        if untagged:
            ledger_errors.append("beats sans event_id: " + ", ".join(untagged))
        if ledger_errors:
            raise ValueError("Narrative Contract refusé: " + "; ".join(ledger_errors))

    # Narrative correction and timing correction are deliberately separate.
    # The LLM may merge/remove only genuine narrative redundancies. Duration itself is
    # fitted deterministically afterwards so no dialogue, event or action is lost.
    redundancy_errors = _event_redundancy_errors(chunks)
    if redundancy_errors:
        feedback = (
            "Corrige uniquement les répétitions narratives sans changer le script ni le Scene Plan. "
            "Le SCENE PLAN est une frontière stricte: conserve chaque scene_index et utilise uniquement les event_ids "
            "autorisés dans cette scène. Ne supprime aucune information narrative unique, aucun dialogue nécessaire, "
            "aucune action nécessaire et aucun EVxx. Ne corrige PAS la durée en supprimant du contenu. Erreurs: "
            + "; ".join(redundancy_errors)
        )
        try:
            raw = segmenter.segment(
                text,
                form=project.delivery,
                bible=bible_payload,
                feedback=feedback,
                narrative_contract=contract_payload,
                scene_plan=scene_plan,
            )
        except Exception as exc:
            raise RuntimeError(f"La correction des répétitions de la segmentation a échoué: {exc}") from exc
        chunks = normalize_beats(
            _beat_chunks(raw, ""),
            form=project.delivery,
            resolve_character_names=resolver.names_for_row,
        )
        scene_plan_errors = _beat_scene_plan_errors(chunks, scene_plan)
        if scene_plan_errors:
            raise ValueError("Segmentation hors Scene Plan après correction: " + "; ".join(scene_plan_errors))

    chunks = _fit_scene_durations_without_loss(chunks, scene_plan)

    _validate_segmented_beats(chunks, form=project.delivery, project=project, scene_plan=scene_plan)
    return persist_beats(episode, chunks, script=script, scene_plan=stored_plan)


def _veo_shot_durations(total_seconds: float) -> list[int]:
    """Return Veo reference-to-video clips.

    Veo 3.1 reference_to_video currently accepts only 8-second outputs, so every
    production shot must be 8 seconds. The final clip may contain intentional
    hold/reaction time instead of requesting an unsupported 4s/6s render.
    """
    import math

    total = max(0.1, float(total_seconds or 0))
    return [8] * max(1, math.ceil(total / 8.0))


def plan_beat_shots(beat: Beat, *, max_shot_seconds: float = 8.0) -> list[Shot]:
    """Create semantically distinct Veo-ready shots without modifying the narrative Beat."""
    if beat.shots.exists():
        return list(beat.shots.order_by("index"))

    from agents.roles.shot_planner import ShotPlanner

    text = str(beat.text or "").strip()
    durations = _veo_shot_durations(float(beat.duration_seconds or 1))
    rows = []
    if len(durations) == 1:
        rows = [{
            "index": 1,
            "text": text,
            "video_prompt": beat.video_prompt or text,
            "camera": beat.camera or {},
            "continuity": beat.continuity or {},
        }]
    else:
        bible = beat.episode.season.project.bibles.order_by("-version").first()
        bible_payload = bible.payload if bible else {}
        payload = ShotPlanner().plan(
            beat={
                "text": text,
                "dialogue": beat.dialogue,
                "video_prompt": beat.video_prompt,
                "camera": beat.camera,
                "continuity": beat.continuity,
                "emotion": beat.emotion,
                "scene_index": beat.scene.index if beat.scene_id else None,
                "narrative_event_id": beat.narrative_event.key if beat.narrative_event_id else None,
            },
            durations=durations,
            bible=bible_payload,
        )
        rows = payload.get("shots") if isinstance(payload, dict) else None
        if not isinstance(rows, list) or len(rows) != len(durations):
            raise ValueError(
                f"Shot Planner invalide: {len(durations)} shots attendus, "
                f"{len(rows) if isinstance(rows, list) else 0} reçus"
            )

    shots = []
    for index, (seconds, row) in enumerate(zip(durations, rows), start=1):
        shot_text = str(row.get("text") or "").strip()
        video_prompt = str(row.get("video_prompt") or "").strip()
        if not shot_text:
            raise ValueError(f"Shot Planner invalide: shot {index} sans contenu")
        # A silent visual shot may legitimately omit video_prompt. In that case
        # the canonical shot text itself is the visual directing instruction.
        if not video_prompt:
            video_prompt = shot_text
        from apps.projects.continuity import resolve_ingredients
        reference_uids = [
            item["reference_uid"]
            for item in resolve_ingredients(beat)["items"]
            if item.get("reference_uid")
        ]
        shots.append(Shot.objects.create(
            beat=beat,
            index=index,
            text=shot_text,
            duration_seconds=seconds,
            video_prompt=video_prompt,
            negative_prompt=beat.negative_prompt,
            camera=row.get("camera") if isinstance(row.get("camera"), dict) else (beat.camera or {}),
            continuity={
                **(beat.continuity or {}),
                **(row.get("continuity") if isinstance(row.get("continuity"), dict) else {}),
                "narrative_beat_seconds": float(beat.duration_seconds or 0),
                "production_shot_seconds": seconds,
                "shot_part": index,
                "shot_parts": len(durations),
                "source_beat_text": text,
            },
            reference_uids=reference_uids,
        ))
    return shots

def review_shot(shot: Shot, decision: str, comment: str = "", take_id: int | None = None) -> Shot:
    from apps.production.models import Review
    if decision not in {"approve", "reject", "revise"}:
        raise ValueError("decision must be approve, reject or revise")
    take = shot.takes.filter(pk=take_id).first() if take_id is not None else shot.takes.order_by("-number").first()
    if take_id is not None and take is None:
        raise ValueError("Ce take n'appartient pas à ce shot")
    if decision == "approve":
        if take is None or not take.uri:
            raise ValueError("Impossible de verrouiller un take sans vidéo")
        shot.takes.exclude(pk=take.pk).filter(status=ShotTake.Status.LOCKED).update(status=ShotTake.Status.REVIEW)
        take.status = ShotTake.Status.LOCKED
        take.save(update_fields=["status"])
        shot.status = Beat.Status.LOCKED
    elif decision == "reject":
        if take is not None:
            take.status = ShotTake.Status.REJECTED
            take.save(update_fields=["status"])
        shot.status = Beat.Status.REJECTED
    else:
        shot.status = Beat.Status.DRAFT
    shot.save(update_fields=["status"])
    Review.objects.create(episode=shot.beat.episode, beat=shot.beat, shot=shot, shot_take=take, decision=decision, comment=comment)
    return shot


def render_shot(
    shot: Shot,
    *,
    adjustment_prompt: str = "",
    adjustment_reference_uri: str = "",
    adjustment_mode: str = "custom",
) -> Shot:
    from agents.backends import get_video
    from apps.production.models import Asset
    from apps.projects.continuity import shot_render_package

    package = shot_render_package(shot, adjustment_prompt=adjustment_prompt)
    if not package["ready"]:
        raise ValueError("Rendu vidéo refusé: " + "; ".join(package["errors"]))

    shot.status = Beat.Status.RENDERING
    shot.save(update_fields=["status"])
    number = (shot.takes.order_by("-number").values_list("number", flat=True).first() or 0) + 1
    prompt = package["prompt"]
    pack = package["ingredients"]
    take = ShotTake.objects.create(
        shot=shot,
        number=number,
        prompt=prompt,
        negative_prompt=shot.negative_prompt,
        status=ShotTake.Status.RENDERING,
        generation_meta={
            "ingredients": pack["items"],
            "media_items": pack.get("media_items", []),
            "veo_reference_items": pack.get("media_items", [])[:3],
            "reference_uids": list(shot.reference_uids or []),
            "continuity": package["context"],
            "previous_take": package.get("previous_take"),
            "language_locked": bool(shot.beat.dialogue),
            "dialogue_language_policy": "exact_original_language",
            "adjustment_prompt": str(adjustment_prompt or "").strip(),
            "adjustment_mode": str(adjustment_mode or "custom"),
            "adjustment_reference_uri": str(adjustment_reference_uri or "").strip() or None,
            "previous_take_frame": None,
            "scene_frame": package.get("scene_frame"),
        },
    )
    backend = get_video()
    take.backend = getattr(backend, "provider_id", "")
    take.save(update_fields=["backend"])
    project = package["project"]
    project_key = f"{project.id}-{project.slug}"
    previous_take = package.get("previous_take")
    scene_frame = package.get("scene_frame") or {}
    baseline_frame = str(adjustment_reference_uri or "").strip() or None
    if not baseline_frame and not str(adjustment_prompt or "").strip():
        baseline_frame = str(scene_frame.get("uri") or "").strip() or None
    if not baseline_frame and str(adjustment_prompt or "").strip() and previous_take and previous_take.get("uri"):
        # For a re-adjustment, extract a real frame from the previous take so
        # the new generation is visually anchored to the take being revised.
        # This is kept separate from Veo asset references because Veo cannot
        # combine reference_images with a source/start image in one request.
        try:
            baseline_frame = backend.extract_reference_frame(
                previous_take["uri"],
                project_key=project_key,
            )
        except (AttributeError, RuntimeError, ValueError):
            baseline_frame = None
    if baseline_frame:
        take.generation_meta = {
            **(take.generation_meta or {}),
            "previous_take_frame": baseline_frame if not adjustment_reference_uri else None,
            "adjustment_reference_uri": str(adjustment_reference_uri or "").strip() or None,
        }
        take.save(update_fields=["generation_meta"])
    try:
        uri = backend.render(
            prompt,
            start_frame=baseline_frame or pack["start_frame"],
            ingredients=[] if baseline_frame else pack["uris"],
            duration_seconds=float(shot.duration_seconds),
            aspect_ratio=project.aspect_ratio,
            project_key=project_key,
        )
    except Exception as exc:
        take.status = ShotTake.Status.FAILED
        take.generation_meta = {**(take.generation_meta or {}), "error": str(exc)}
        take.save(update_fields=["status", "generation_meta"])
        shot.status = Beat.Status.REJECTED
        shot.save(update_fields=["status"])
        raise
    take.uri = uri
    take.status = ShotTake.Status.REVIEW
    take.save(update_fields=["uri", "status"])
    Asset.objects.create(
        project=project, beat=shot.beat, shot=shot, shot_take=take,
        kind=Asset.Kind.VIDEO, role=Asset.Role.CLIP, uri=uri, provider=take.backend,
        meta={
            "prompt": prompt,
            "shot_index": shot.index,
            "ingredients": pack["items"],
            "media_items": pack.get("media_items", []),
            "veo_reference_items": pack.get("media_items", [])[:3],
            "reference_uids": list(shot.reference_uids or []),
            "continuity": package["context"],
            "previous_take": package.get("previous_take"),
            "language_locked": bool(shot.beat.dialogue),
            "dialogue_language_policy": "exact_original_language",
        },
    )
    shot.status = Beat.Status.REVIEW
    shot.save(update_fields=["status"])
    return shot

def review_beat(beat: Beat, decision: str, comment: str = "", take_id: int | None = None) -> Beat:
    from apps.production.models import Review

    allowed = {"approve", "reject", "revise"}
    if decision not in allowed:
        raise ValueError("decision must be approve, reject or revise")

    take = None
    if take_id is not None:
        take = beat.takes.filter(pk=take_id).first()
        if take is None:
            raise ValueError("Ce take n'appartient pas à ce beat")
    elif decision in {"approve", "reject"}:
        take = beat.takes.order_by("-number").first()

    if decision == "approve" and take is not None:
        if not take.uri:
            raise ValueError("Impossible de verrouiller un take sans vidéo")
        beat.takes.exclude(pk=take.pk).filter(status=BeatTake.Status.LOCKED).update(status=BeatTake.Status.REVIEW)
        take.status = BeatTake.Status.LOCKED
        take.save(update_fields=["status"])
        beat.take = take.number
        beat.status = Beat.Status.LOCKED
        beat.save(update_fields=["take", "status"])
    elif decision == "reject":
        if take is not None:
            take.status = BeatTake.Status.REJECTED
            take.save(update_fields=["status"])
        beat.status = Beat.Status.REJECTED
        beat.save(update_fields=["status"])
    elif decision == "approve":
        beat.status = Beat.Status.APPROVED_TEXT
        beat.save(update_fields=["status"])
    else:
        beat.status = Beat.Status.DRAFT
        beat.save(update_fields=["status"])

    if beat.narrative_event_id:
        latest_script = beat.episode.scripts.order_by("-version").first()
        event_beats = Beat.objects.filter(
            script=latest_script,
            narrative_event_id=beat.narrative_event_id,
        )
        if event_beats.exists() and not event_beats.exclude(
            status__in=[Beat.Status.APPROVED_TEXT, Beat.Status.LOCKED]
        ).exists():
            NarrativeEvent.objects.filter(pk=beat.narrative_event_id).update(
                status=NarrativeEvent.Status.CONSUMED
            )
        elif decision in {"reject", "revise"}:
            NarrativeEvent.objects.filter(pk=beat.narrative_event_id).update(
                status=NarrativeEvent.Status.SCRIPTED
            )

    Review.objects.create(
        beat=beat,
        beat_take=take,
        episode=beat.episode,
        decision=decision,
        comment=comment,
    )
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
    Asset.objects.create(project=beat.episode.season.project, beat=beat, kind=Asset.Kind.VIDEO, role=Asset.Role.CLIP, uri=uri, provider=getattr(backend, "provider_id", ""), meta={"prompt": prompt})
    Job.objects.create(project=beat.episode.season.project, kind=Job.Kind.VIDEO, status=Job.Status.SUCCEEDED, agent_role="cinematographer", backend=getattr(backend, "provider_id", ""), result={"beat_id": beat.id, "uri": uri})
    beat.status = Beat.Status.REVIEW
    beat.save(update_fields=["status"])
    return beat
