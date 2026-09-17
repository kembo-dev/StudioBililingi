from __future__ import annotations

from agents.backends import get_image


class ArtDirector:
    role = "art_director"

    def __init__(self):
        self.image = get_image()

    def character_ref(self, *, name: str, look: str, role: str) -> str:
        return self.image.generate(
            "Photoreal cinematic character reference, single person, consistent wardrobe, "
            "neutral studio lighting, no text. "
            f"Name: {name}. Role: {role}. Look: {look}."
        )

    def location_ref(self, *, name: str, look: str, time_of_day: str) -> str:
        return self.image.generate(
            "Cinematic establishing plate, empty of named characters, no text. "
            f"Place: {name}. Time: {time_of_day or 'unspecified'}. Look: {look}."
        )

    def prop_ref(self, *, name: str, look: str) -> str:
        return self.image.generate(
            "Product-style hero shot of a story prop, plain background, no text. "
            f"Object: {name}. Look: {look}."
        )
