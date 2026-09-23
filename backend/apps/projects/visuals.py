from pathlib import Path

from django.conf import settings
from django.db import transaction

from django.utils.text import slugify

from apps.bible.models import Character, Location, Prop
from apps.production.models import Asset
from apps.projects.models import Project


def generate_refs(project: Project) -> list:
    bible = project.bibles.first()
    if bible is None or not bible.locked:
        raise ValueError("Verrouille la bible avant les références visuelles")

    from agents.roles.art_director import ArtDirector

    artist = ArtDirector()
    project_key = f"{project.id}-{project.slug}"
    created = []

    def existing(role: str, key: str):
        return (
            Asset.objects.filter(project=project, role=role, meta__key=key)
            .order_by("-created_at")
            .first()
        )

    def save(role: str, uri: str, meta: dict) -> None:
        created.append(
            Asset.objects.create(
                project=project,
                kind=Asset.Kind.IMAGE,
                role=role,
                uri=uri,
                provider=getattr(artist.image, "provider_id", ""),
                meta=meta,
            )
        )

    for char in project.characters.all():
        if existing(Asset.Role.CHARACTER_REF, char.key):
            continue
        save(
            Asset.Role.CHARACTER_REF,
            artist.character_ref(name=char.name, look=char.look, role=char.role, project_key=project_key, visual_style=project.visual_style),
            {"key": char.key, "reference_uid": char.reference_uid, "name": char.name, "entity": "character", "visual_style": project.visual_style},
        )
    for loc in project.locations.all():
        if existing(Asset.Role.LOCATION_REF, loc.key):
            continue
        save(
            Asset.Role.LOCATION_REF,
            artist.location_ref(name=loc.name, look=loc.look, time_of_day=loc.time_of_day, project_key=project_key, visual_style=project.visual_style),
            {"key": loc.key, "reference_uid": loc.reference_uid, "name": loc.name, "entity": "location", "visual_style": project.visual_style},
        )
    for prop in project.props.all():
        if existing(Asset.Role.PROP_REF, prop.key):
            continue
        save(
            Asset.Role.PROP_REF,
            artist.prop_ref(name=prop.name, look=prop.look, project_key=project_key, visual_style=project.visual_style),
            {"key": prop.key, "reference_uid": prop.reference_uid, "name": prop.name, "entity": "prop", "visual_style": project.visual_style},
        )
    return created



def regenerate_visual_ref(project: Project, entity_type: str, entity_key: str, custom_prompt: str = ""):
    bible = project.bibles.first()
    if bible is None or not bible.locked:
        raise ValueError("Verrouille la bible avant les références visuelles")

    entity_type = str(entity_type or "").strip().lower()
    entity_key = str(entity_key or "").strip()
    custom_prompt = str(custom_prompt or "").strip()
    if len(custom_prompt) > 4000:
        raise ValueError("Le prompt complémentaire est limité à 4000 caractères")
    models = {"character": Character, "location": Location, "prop": Prop}
    if entity_type not in models:
        raise ValueError("Type de référence invalide")

    entity = models[entity_type].objects.filter(project=project, key=entity_key).first()
    if entity is None:
        raise ValueError("Élément introuvable dans ce projet")

    from agents.roles.art_director import ArtDirector

    artist = ArtDirector()
    project_key = f"{project.id}-{project.slug}"
    if entity_type == "character":
        role = Asset.Role.CHARACTER_REF
        uri = artist.character_ref(
            name=entity.name, look=entity.look, role=entity.role,
            project_key=project_key, visual_style=project.visual_style, custom_prompt=custom_prompt,
        )
    elif entity_type == "location":
        role = Asset.Role.LOCATION_REF
        uri = artist.location_ref(
            name=entity.name, look=entity.look, time_of_day=entity.time_of_day,
            project_key=project_key, visual_style=project.visual_style, custom_prompt=custom_prompt,
        )
    else:
        role = Asset.Role.PROP_REF
        uri = artist.prop_ref(
            name=entity.name, look=entity.look,
            project_key=project_key, visual_style=project.visual_style, custom_prompt=custom_prompt,
        )

    old_assets = list(Asset.objects.filter(project=project, role=role, meta__key=entity.key))
    old_uris = [asset.uri for asset in old_assets]
    with transaction.atomic():
        Asset.objects.filter(pk__in=[asset.pk for asset in old_assets]).delete()
        asset = Asset.objects.create(
            project=project,
            kind=Asset.Kind.IMAGE,
            role=role,
            uri=uri,
            provider=getattr(artist.image, "provider_id", ""),
            meta={
                "key": entity.key,
                "reference_uid": entity.reference_uid,
                "name": entity.name,
                "entity": entity_type,
                "visual_style": project.visual_style,
                "custom_prompt": custom_prompt,
                "regenerated": True,
            },
        )

    media_root = Path(getattr(settings, "MEDIA_ROOT", "") or "").resolve()
    for old_uri in old_uris:
        if not old_uri or old_uri == uri or not str(old_uri).startswith("/media/"):
            continue
        candidate = (media_root / str(old_uri)[len("/media/"):]).resolve()
        try:
            candidate.relative_to(media_root)
        except ValueError:
            continue
        try:
            candidate.unlink(missing_ok=True)
        except OSError:
            pass
    return asset


def regenerate_character_ref(project: Project, character_key: str):
    # Backward-compatible wrapper for existing callers.
    return regenerate_visual_ref(project, "character", character_key)



def add_manual_ref(
    project: Project,
    *,
    entity_type: str,
    name: str,
    look: str,
    role: str = "",
    time_of_day: str = "",
    story_function: str = "",
):
    bible = project.bibles.first()
    if bible is None or not bible.locked:
        raise ValueError("Verrouille la bible avant d'ajouter une référence")

    entity_type = str(entity_type or "").strip().lower()
    name = str(name or "").strip()
    look = str(look or "").strip()
    if entity_type not in {"character", "location", "prop"}:
        raise ValueError("Type de référence invalide")
    if not name or not look:
        raise ValueError("Le nom et la description visuelle sont requis")

    model = {"character": Character, "location": Location, "prop": Prop}[entity_type]
    base_key = slugify(name)[:45] or entity_type
    key = base_key
    suffix = 2
    while model.objects.filter(project=project, key=key).exists():
        key = f"{base_key[:40]}-{suffix}"
        suffix += 1

    with transaction.atomic():
        if entity_type == "character":
            entity = Character.objects.create(
                project=project,
                bible=bible,
                key=key,
                name=name,
                role=str(role or "Personnage secondaire").strip(),
                look=look,
                locked=True,
            )
        elif entity_type == "location":
            entity = Location.objects.create(
                project=project,
                bible=bible,
                key=key,
                name=name,
                look=look,
                time_of_day=str(time_of_day or "").strip(),
                locked=True,
            )
        else:
            entity = Prop.objects.create(
                project=project,
                bible=bible,
                key=key,
                name=name,
                look=look,
                story_function=str(story_function or "").strip(),
                locked=True,
            )

        payload = dict(bible.payload or {})
        bucket = {"character": "characters", "location": "locations", "prop": "props"}[entity_type]
        rows = list(payload.get(bucket) or [])
        row = {"id": key, "name": name, "look": look}
        if entity_type == "character":
            row["role"] = entity.role
        elif entity_type == "location":
            row["time_of_day"] = entity.time_of_day
        else:
            row["story_function"] = entity.story_function
        rows.append(row)
        payload[bucket] = rows
        bible.payload = payload
        bible.save(update_fields=["payload"])

    return entity



def delete_visual_ref(project: Project, asset_id: int) -> None:
    asset = Asset.objects.filter(
        project=project,
        pk=asset_id,
        role__in=(Asset.Role.CHARACTER_REF, Asset.Role.LOCATION_REF, Asset.Role.PROP_REF),
    ).first()
    if asset is None:
        raise ValueError("Référence visuelle introuvable dans ce projet")

    uri = asset.uri
    asset.delete()

    # Delete only Studio-managed local media. The canonical Bible entity stays
    # intact, so "Générer les refs" can recreate the missing image later.
    if uri and str(uri).startswith("/media/"):
        media_root = Path(getattr(settings, "MEDIA_ROOT", "") or "").resolve()
        candidate = (media_root / str(uri)[len("/media/"):]).resolve()
        try:
            candidate.relative_to(media_root)
        except ValueError:
            return
        try:
            candidate.unlink(missing_ok=True)
        except OSError:
            pass
