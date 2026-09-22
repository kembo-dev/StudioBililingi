from __future__ import annotations

from agents.backends import get_image


class ArtDirector:
    role = "art_director"

    def __init__(self):
        self.image = get_image()

    def character_ref(self, *, name: str, look: str, role: str, project_key: str | None = None) -> str:
        return self.image.generate(
            "Create ONE professional photorealistic cinematic CHARACTER REFERENCE SHEET for production continuity. "
            "The sheet must depict ONE AND THE SAME person in every panel: identical facial identity, apparent age, "
            "skin tone, body proportions, hairstyle, hair color, facial hair, eye color and distinctive features. "
            "Use a clean premium studio lookbook/contact-sheet layout on a neutral gray background. "
            "MANDATORY VIEWS: front close-up portrait; front waist-up; full-body front; 3/4 right; 3/4 left; "
            "right profile; left profile; full-body back view. "
            "Also include several expression close-ups while preserving exact identity: neutral, slight smile, serious, "
            "worried/surprised, determined. Include useful wardrobe/detail crops when relevant (jewelry, watch, sleeves, "
            "belt, shoes or other signature accessories). "
            "WARDROBE LOCK: use exactly the same canonical outfit, colors, accessories and grooming in all turnaround "
            "views unless the character description explicitly requires variants. "
            "COMPOSITION: clearly separated panels, consistent scale where appropriate, sharp face and clothing detail, "
            "realistic anatomy, realistic skin texture, no duplicated person inside a single panel, no unrelated people. "
            "This image will be used as an identity reference for later video generation, so prioritize identity "
            "consistency and readable angles over artistic experimentation. "
            "Do not invent logos or watermarks. Avoid long generated prose; if labels are rendered, keep them minimal. "
            f"CHARACTER NAME: {name}. ROLE: {role}. CANONICAL LOOK: {look}.",
            project_key=project_key,
        )

    def location_ref(self, *, name: str, look: str, time_of_day: str, project_key: str | None = None) -> str:
        return self.image.generate(
            "Cinematic establishing plate, empty of named characters, no text. "
            f"Place: {name}. Time: {time_of_day or 'unspecified'}. Look: {look}.",
            project_key=project_key,
        )

    def prop_ref(self, *, name: str, look: str, project_key: str | None = None) -> str:
        return self.image.generate(
            "Product-style hero shot of a story prop, plain background, no text. "
            f"Object: {name}. Look: {look}.",
            project_key=project_key,
        )
