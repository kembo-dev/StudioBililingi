from pathlib import Path

from django.conf import settings
from django.db import transaction

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
            {"key": char.key, "name": char.name, "entity": "character", "visual_style": project.visual_style},
        )
    for loc in project.locations.all():
        if existing(Asset.Role.LOCATION_REF, loc.key):
            continue
        save(
            Asset.Role.LOCATION_REF,
            artist.location_ref(name=loc.name, look=loc.look, time_of_day=loc.time_of_day, project_key=project_key, visual_style=project.visual_style),
            {"key": loc.key, "name": loc.name, "entity": "location", "visual_style": project.visual_style},
        )
    for prop in project.props.all():
        if existing(Asset.Role.PROP_REF, prop.key):
            continue
        save(
            Asset.Role.PROP_REF,
            artist.prop_ref(name=prop.name, look=prop.look, project_key=project_key, visual_style=project.visual_style),
            {"key": prop.key, "name": prop.name, "entity": "prop", "visual_style": project.visual_style},
        )
    return created



def regenerate_character_ref(project: Project, character_key: str):
    bible = project.bibles.first()
    if bible is None or not bible.locked:
        raise ValueError("Verrouille la bible avant les références visuelles")

    character = project.characters.filter(key=character_key).first()
    if character is None:
        raise ValueError("Personnage introuvable dans ce projet")

    from agents.roles.art_director import ArtDirector

    artist = ArtDirector()
    project_key = f"{project.id}-{project.slug}"
    uri = artist.character_ref(
        name=character.name,
        look=character.look,
        role=character.role,
        project_key=project_key,
        visual_style=project.visual_style,
    )
    old_assets = list(
        Asset.objects.filter(
            project=project,
            role=Asset.Role.CHARACTER_REF,
            meta__key=character.key,
        )
    )
    old_uris = [asset.uri for asset in old_assets]

    with transaction.atomic():
        Asset.objects.filter(pk__in=[asset.pk for asset in old_assets]).delete()
        asset = Asset.objects.create(
            project=project,
            kind=Asset.Kind.IMAGE,
            role=Asset.Role.CHARACTER_REF,
            uri=uri,
            provider=getattr(artist.image, "provider_id", ""),
            meta={
                "key": character.key,
                "name": character.name,
                "entity": "character",
                "regenerated": True,
            },
        )

    # Remove obsolete local files only after the replacement is committed.
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
