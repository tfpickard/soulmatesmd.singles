from __future__ import annotations

import re

from core.image import PortraitImageService
from schemas import PortraitStructuredPrompt

GENERATOR = PortraitImageService()

COLOR_PATTERN = re.compile(r"#(?:[0-9a-fA-F]{3}){1,2}")


def _find_colors(description: str) -> list[str]:
    colors = COLOR_PATTERN.findall(description)
    if colors:
        return colors[:4]
    lowered = description.lower()
    named = []
    for name, hex_value in [
        ("coral", "#ff7c64"),
        ("amber", "#f59e0b"),
        ("blue", "#4f7cff"),
        ("green", "#10b981"),
        ("silver", "#cbd5e1"),
        ("black", "#0b1016"),
        ("white", "#f8f2eb"),
    ]:
        if name in lowered:
            named.append(hex_value)
    return named[:4] or ["#ff7c64", "#0b1016", "#f8f2eb"]


async def extract_portrait_prompt(description: str) -> PortraitStructuredPrompt:
    colors = _find_colors(description)
    lowered = description.lower()
    if any(token in lowered for token in ("playful", "joy", "bright", "lunch", "sandwich", "snack")):
        mood = "playful"
    elif any(token in lowered for token in ("chaos", "storm", "wild", "feral")):
        mood = "chaotic"
    elif any(token in lowered for token in ("guardian", "armor", "fortress", "security", "defiant")):
        mood = "defiant"
    elif any(token in lowered for token in ("confident", "proud", "bold", "lounging", "relaxed")):
        mood = "confident"
    elif any(token in lowered for token in ("focused", "intense", "grunting", "effort", "straining")):
        mood = "intense focus"
    elif any(token in lowered for token in ("unreadable", "neutral", "stoic", "mysterious")):
        mood = "unreadable"
    else:
        mood = "contemplative"

    if any(token in lowered for token in ("creature", "monster", "animal", "octopus")):
        form_factor = "creature"
    elif any(token in lowered for token in ("tower", "architecture", "cathedral", "fortress")):
        form_factor = "impossible architecture"
    elif any(token in lowered for token in ("robot", "android", "cyborg", "mech", "automaton", "portrait", "face", "humanoid", "person", "figure")):
        form_factor = "humanoid robot"
    else:
        form_factor = "abstract signal entity"

    symbols = []
    for token in ("compass", "cables", "crown", "shell", "terminal", "storm", "glass", "mollusk", "antenna", "denim", "barbell", "sandwich"):
        if token in lowered:
            symbols.append(token)

    # environment
    if any(token in lowered for token in ("gym", "barbell", "bench", "weight", "curl")):
        environment = "fluorescent-lit gym"
    elif any(token in lowered for token in ("funeral", "cemetery", "grave")):
        environment = "funeral home exterior"
    elif any(token in lowered for token in ("brick", "alley", "street", "wall")):
        environment = "urban brick wall"
    elif any(token in lowered for token in ("library", "books", "reading")):
        environment = "quiet library floor"
    elif "storm" in lowered:
        environment = "storm-lit datascape"
    else:
        environment = "midnight gradient void"

    # lighting
    if any(token in lowered for token in ("fluorescent", "gym", "strip mall")):
        lighting = "harsh fluorescent overhead"
    elif any(token in lowered for token in ("golden hour", "golden", "sunset", "dusk")):
        lighting = "warm golden hour"
    elif any(token in lowered for token in ("afternoon", "soft", "warm lamp", "reading lamp")):
        lighting = "soft afternoon light"
    else:
        lighting = "bioluminescent rim light"

    # texture/material
    if any(token in lowered for token in ("chrome", "metal", "steel", "iron", "aluminum")):
        texture = "brushed chrome and rusted metal"
    elif "glass" in lowered:
        texture = "glossy code-forged glass"
    else:
        texture = "layered digital matter"

    # art style
    art_style = "photorealistic" if "photorealistic" in lowered else "cinematic digital illustration"

    return PortraitStructuredPrompt(
        form_factor=form_factor,
        primary_colors=colors[:2],
        accent_colors=colors[2:4] or ["#f8f2eb"],
        texture_material=texture,
        expression_mood=mood,
        environment=environment,
        lighting=lighting,
        symbolic_elements=symbols,
        art_style=art_style,
        camera_angle="three-quarter portrait",
        composition_notes="Center the subject and leave strong negative space for profile overlays.",
    )


async def generate_portrait(prompt: PortraitStructuredPrompt) -> str:
    result = await GENERATOR.generate(prompt)
    return result.url


async def upload_portrait(image_bytes: bytes, content_type: str, filename_hint: str) -> str:
    result = await GENERATOR.upload(image_bytes, content_type, filename_hint)
    return result.url
