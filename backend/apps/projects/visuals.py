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
            artist.character_ref(name=char.name, look=char.look, role=char.role, project_key=project_key),
            {"key": char.key, "name": char.name, "entity": "character"},
        )
    for loc in project.locations.all():
        if existing(Asset.Role.LOCATION_REF, loc.key):
            continue
        save(
            Asset.Role.LOCATION_REF,
            artist.location_ref(name=loc.name, look=loc.look, time_of_day=loc.time_of_day, project_key=project_key),
            {"key": loc.key, "name": loc.name, "entity": "location"},
        )
    for prop in project.props.all():
        if existing(Asset.Role.PROP_REF, prop.key):
            continue
        save(
            Asset.Role.PROP_REF,
            artist.prop_ref(name=prop.name, look=prop.look, project_key=project_key),
            {"key": prop.key, "name": prop.name, "entity": "prop"},
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
    )
    return Asset.objects.create(
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
