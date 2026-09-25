from __future__ import annotations

from agents.backends import get_image


VISUAL_STYLE_PROMPTS = {
    "realistic": "Photorealistic cinematic live-action, realistic skin, materials, anatomy and lens behavior.",
    "realistic_imperfect": "Authentic photorealistic live-action with believable real-world imperfections: natural skin texture, pores, subtle blemishes, asymmetry, flyaway hair, fabric wrinkles, lived-in clothing and environments, small wear marks, imperfect practical lighting and physically plausible lens behavior. Preserve attractiveness and identity without beauty-filter smoothing, plastic skin, excessive retouching or artificial perfection.",
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
        self.image = get_image(role=self.role)

    def character_ref(self, *, name: str, look: str, role: str, project_key: str | None = None, visual_style: str = "realistic", custom_prompt: str = "") -> str:
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
            f"CHARACTER NAME: {name}. ROLE: {role}. CANONICAL LOOK: {look}. "
            f"USER REFINEMENT: {custom_prompt.strip() if custom_prompt.strip() else 'None. Follow the canonical look exactly.'}",
            project_key=project_key,
        )

    def location_ref(self, *, name: str, look: str, time_of_day: str, project_key: str | None = None, visual_style: str = "realistic", custom_prompt: str = "") -> str:
        return self.image.generate(
            f"VISUAL STYLE LOCK: {visual_style_prompt(visual_style)} Cinematic establishing plate in that exact style, empty of named characters, no text. "
            f"Place: {name}. Time: {time_of_day or 'unspecified'}. Look: {look}. "
            f"USER REFINEMENT: {custom_prompt.strip() if custom_prompt.strip() else 'None. Follow the canonical look exactly.'}",
            project_key=project_key,
        )

    def scene_frame(self, *, beat_text: str, characters: list[dict], location: dict | None, props: list[dict], refs: list[str] | None = None, camera: dict | None = None, emotion: str = "", project_key: str | None = None, visual_style: str = "realistic", custom_prompt: str = "") -> str:
        character_text = "; ".join(f"{row.get('name')}: {row.get('look')}" for row in characters) or "No named character"
        prop_text = "; ".join(f"{row.get('name')}: {row.get('look')}" for row in props) or "No important prop"
        location_text = f"{location.get('name')}: {location.get('look')}" if location else "Canonical story location"
        return self.image.generate(
            f"VISUAL STYLE LOCK: {visual_style_prompt(visual_style)} "
            "Create ONE cinematic production frame for this exact narrative beat. This is a master scene frame for later video generation, not a character sheet, collage, storyboard or poster. "
            "Compose a single coherent film still with physically plausible blocking, lens perspective, lighting and depth. "
            "Preserve the exact canonical identity, wardrobe and appearance described for every named character; preserve the exact set and prop identity. "
            "Show the precise story moment visually. Do not render dialogue, captions, labels, subtitles, logos or watermarks. "
            f"BEAT: {beat_text}. LOCATION: {location_text}. CHARACTERS: {character_text}. PROPS: {prop_text}. "
            f"CAMERA INTENT: {camera or {}}. PERFORMANCE/EMOTION: {emotion or 'natural to the beat'}. "
            f"USER REFINEMENT: {custom_prompt.strip() if custom_prompt.strip() else 'None. Stage the canonical beat professionally.'}",
            refs=refs or [],
            project_key=project_key,
        )

    def prop_ref(self, *, name: str, look: str, project_key: str | None = None, visual_style: str = "realistic", custom_prompt: str = "") -> str:
        return self.image.generate(
            f"VISUAL STYLE LOCK: {visual_style_prompt(visual_style)} Product-style hero shot of a story prop in that exact style, plain background, no text. "
            f"Object: {name}. Look: {look}. "
            f"USER REFINEMENT: {custom_prompt.strip() if custom_prompt.strip() else 'None. Follow the canonical look exactly.'}",
            project_key=project_key,
        )
