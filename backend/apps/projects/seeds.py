import re

META = {"genre", "concept", "début", "debut", "fin", "twist", "thriller", "psychologique", "fantastique", "drame"}
SKIP_CAP = {"Le", "La", "Les", "Un", "Une", "Des", "Sur", "Dans", "Pour", "Avec", "Mais", "Lorsque", "Chaque", "Lors", "Genre", "Concept", "Début", "Debut", "Fin", "Twist", "Thriller", "Fantastique", "Psychologique"}


def parse_concept(raw: str) -> dict:
    text = (raw or "").strip()
    parts = {"genre": "", "concept": "", "start": "", "end": "", "body": text}

    def grab(label: str) -> str:
        pattern = rf"{label}\s*[:\-\u2013]\s*(.+?)(?=(?:Genre|Concept|Début|Debut|Fin|Twist)\s*[:\-\u2013]|$ )"
        match = re.search(pattern, text, flags=re.I | re.S)
        return match.group(1).strip() if match else ""

    parts["genre"] = grab("Genre")
    parts["concept"] = grab("Concept") or grab("Logline")
    parts["start"] = grab("Début") or grab("Debut")
    parts["end"] = grab("Fin") or grab("Twist")
    if not parts["concept"]:
        parts["concept"] = text
    parts["body"] = parts["concept"] or text
    return parts


def _names(text: str) -> list[str]:
    found = re.findall(r"\b([A-ZÉÈÀÂ][a-zàâéèêëïîôùûç]{2,})\b", text or "")
    names = []
    for name in found:
        if name in SKIP_CAP or name.lower() in META:
            continue
        if name not in names:
            names.append(name)
    return names


def seed_bible(concept: str) -> dict:
    parsed = parse_concept(concept)
    source = " ".join(p for p in (parsed["start"], parsed["body"], parsed["end"]) if p)
    names = _names(source)
    hero = names[0] if names else "Le protagoniste"
    night = any(w in source.lower() for w in ("appel", "03h", "téléphone"))
    other = names[1] if len(names) > 1 else ("La voix au téléphone" if night else "L'autre")
    logline = (parsed["concept"] or parsed["body"])[:220]
    look_hero = "archiviste solitaire, nuit" if "archiviste" in source.lower() else logline[:80]
    look_other = "voix hors champ au combiné" if night else "figure du dénouement"
    return {
        "version": 1,
        "logline": logline,
        "tone": parsed["genre"] or "dramatique",
        "locked": False,
        "characters": [
            {"id": "protag", "name": hero, "role": "protagoniste", "want": "empêcher le mal", "need": "accepter le prix", "look": look_hero, "voice": "intériorisé", "locked": False},
            {"id": "other", "name": other, "role": "catalyseur", "want": "être entendu", "need": "", "look": look_other, "voice": "calme", "locked": False},
        ],
        "locations": [
            {"id": "nuit", "name": "L'appartement la nuit" if night else "Le quotidien", "look": "03h14, écran de téléphone", "time_of_day": "nuit", "locked": False},
            {"id": "jour", "name": "La ville, le lendemain", "look": "lieu de la prédiction", "time_of_day": "jour", "locked": False},
        ],
        "props": [{"id": "objet", "name": "Le téléphone" if night else "L'objet déclencheur", "look": "mobile qui sonne à 03h14", "story_function": "oracle", "locked": False}],
        "source": "stub-from-concept",
        "concept": concept,
        "genre": parsed["genre"],
    }


def seed_season_plan(concept: str) -> list[dict]:
    parsed = parse_concept(concept)
    names = _names(" ".join((parsed["start"], parsed["body"], parsed["end"])))
    hero = names[0] if names else "Le protagoniste"
    start = parsed["start"] or parsed["body"]
    end = parsed["end"] or parsed["body"]
    return [
        {"number": 1, "title": "L'appel", "logline": start[:180] or f"{hero} reçoit le premier signe.", "function_in_arc": "déclencheur"},
        {"number": 2, "title": "La preuve", "logline": f"Ce que la voix a dit à {hero} se produit.", "function_in_arc": "confirmation"},
        {"number": 3, "title": "L'intervention", "logline": f"{hero} tente d'empêcher la suite.", "function_in_arc": "action"},
        {"number": 4, "title": "Le dernier appel", "logline": end[:180] or f"{hero} entend sa propre fin.", "function_in_arc": "climax"},
    ]


def seed_script(episode) -> str:
    parsed = parse_concept(episode.season.project.concept)
    if episode.number == 1:
        core = parsed["start"] or parsed["body"]
    elif episode.number >= 4:
        core = parsed["end"] or parsed["body"]
    else:
        core = parsed["concept"] or parsed["body"]
    return f"{episode.title}. {episode.logline} {core}"
