from apps.production.models import Asset
from apps.projects.models import Project


def generate_refs(project: Project) -> list:
    bible = project.bibles.first()
    if bible is None or not bible.locked:
        raise ValueError("Verrouille la bible avant les références visuelles")

    from agents.roles.art_director import ArtDirector

    artist = ArtDirector()
    created = []

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
        save(
            Asset.Role.CHARACTER_REF,
            artist.character_ref(name=char.name, look=char.look, role=char.role),
            {"key": char.key, "name": char.name, "entity": "character"},
        )
    for loc in project.locations.all():
        save(
            Asset.Role.LOCATION_REF,
            artist.location_ref(name=loc.name, look=loc.look, time_of_day=loc.time_of_day),
            {"key": loc.key, "name": loc.name, "entity": "location"},
        )
    for prop in project.props.all():
        save(
            Asset.Role.PROP_REF,
            artist.prop_ref(name=prop.name, look=prop.look),
            {"key": prop.key, "name": prop.name, "entity": "prop"},
        )
    return created
