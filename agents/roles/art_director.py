from __future__ import annotations

from agents.backends import get_image


VISUAL_STYLE_PROMPTS = {
    "realistic": "Photorealistic cinematic live-action, realistic skin, materials, anatomy and lens behavior.",
    "cartoon": "Premium 2D cartoon animation, clean expressive shapes, polished production design, consistent stylization.",
    "manga": "High-quality manga/anime visual language, clean line art, expressive faces, cinematic anime lighting.",
    "3d_animation": "Premium stylized 3D animated-film look, dimensional materials, cinematic lighting, coherent character modeling.",
    "comic": "Graphic novel/comic-book illustration, confident ink work, controlled shading, cinematic panel-ready design.",
    "watercolor": "Elegant watercolor illustration, painterly washes and paper texture while preserving precise character identity.",
    "claymation": "Handcrafted claymation/stop-motion aesthetic, tactile clay materials, miniature-set lighting, consistent sculpted identity.",
    "pixel_art": "High-detail cinematic pixel-art aesthetic, coherent sprite proportions and palette, production-quality environments.",
    "film_noir": "Classic film-noir visual language, dramatic monochrome lighting, deep shadows, cinematic composition.",
    "fantasy": "Premium stylized fantasy illustration/cinema aesthetic, rich production design, coherent magical atmosphere.",
}


def visual_style_prompt(style: str | None) -> str:
    return VISUAL_STYLE_PROMPTS.get(style or "realistic", VISUAL_STYLE_PROMPTS["realistic"])


class ArtDirector:
    role = "art_director"

    def __init__(self):
        self.image = get_image()

    def character_ref(self, *, name: str, look: str, role: str, project_key: str | None = None, visual_style: str = "realistic") -> str:
        return self.image.generate(
            f"VISUAL STYLE LOCK: {visual_style_prompt(visual_style)} "
            "Create ONE professional cinematic CHARACTER REFERENCE SHEET for production continuity in that exact visual style. "
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
            "coherent anatomy and material treatment appropriate to the selected visual style, no duplicated person inside a single panel, no unrelated people. "
            "This image will be used as an identity reference for later video generation, so prioritize identity "
            "consistency and readable angles over artistic experimentation. "
            "Do not invent logos or watermarks. Avoid long generated prose; if labels are rendered, keep them minimal. "
            f"CHARACTER NAME: {name}. ROLE: {role}. CANONICAL LOOK: {look}.",
            project_key=project_key,
        )

    def location_ref(self, *, name: str, look: str, time_of_day: str, project_key: str | None = None, visual_style: str = "realistic") -> str:
        return self.image.generate(
            f"VISUAL STYLE LOCK: {visual_style_prompt(visual_style)} Cinematic establishing plate in that exact style, empty of named characters, no text. "
            f"Place: {name}. Time: {time_of_day or 'unspecified'}. Look: {look}.",
            project_key=project_key,
        )

    def prop_ref(self, *, name: str, look: str, project_key: str | None = None, visual_style: str = "realistic") -> str:
        return self.image.generate(
            f"VISUAL STYLE LOCK: {visual_style_prompt(visual_style)} Product-style hero shot of a story prop in that exact style, plain background, no text. "
            f"Object: {name}. Look: {look}.",
            project_key=project_key,
        )
