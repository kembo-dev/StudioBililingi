import re

SKIP_CAP = {"Le", "La", "Les", "Un", "Une", "Des", "Sur", "Dans", "Pour", "Avec", "Mais", "Lorsque", "Chaque", "Lors", "Genre", "Concept", "Début", "Debut", "Fin", "Twist", "Thriller", "Fantastique", "Psychologique", "Appel"}


def parse_concept(raw: str) -> dict:
    text = (raw or "").strip()
    parts = {"genre": "", "concept": "", "start": "", "end": "", "body": text}

    def grab(*labels):
        for label in labels:
            pattern = rf"{label}\s*[:\-\u2013/]\s*(.+?)(?=(?:Genre|Concept|Logline|Début|Debut|Fin|Twist)\s*[:\-\u2013/]|$ )"
            match = re.search(pattern, text, flags=re.I | re.S)
            if match:
                return re.sub(r"\s+", " ", match.group(1)).strip()
        return ""

    parts["genre"] = grab("Genre")
    parts["concept"] = grab("Concept", "Logline")
    parts["start"] = grab("Début", "Debut")
    parts["end"] = grab("Fin", "Twist")
    if not parts["concept"]:
        parts["concept"] = text
    parts["body"] = parts["concept"] or text
    return parts


def _names(text: str):
    found = re.findall(r"\b([A-ZÉÈÀÂ][a-zàâéèêëïîôùûç]{2,})\b", text or "")
    names = []
    for name in found:
        if name not in SKIP_CAP and name not in names:
            names.append(name)
    return names


def seed_bible(concept: str) -> dict:
    parsed = parse_concept(concept)
    source = " ".join(p for p in (parsed["start"], parsed["body"], parsed["end"]) if p)
    names = _names(source)
    hero = names[0] if names else "Le protagoniste"
    night = any(w in source.lower() for w in ("appel", "03h", "téléphone", "telephone"))
    characters = [
        {"id": "protag", "name": hero, "role": "protagoniste", "want": "empêcher les catastrophes", "need": "accepter le prix", "look": "archiviste solitaire, nuit" if "archiviste" in source.lower() else source[:80], "voice": "intériorisé", "locked": False},
        {"id": "voice", "name": "La voix au téléphone" if night else "L'autre", "role": "oracle", "want": "être entendu", "need": "", "look": "hors champ, 30 secondes", "voice": "calme", "locked": False},
    ]
    if "sauvé" in source.lower() or "sauver" in source.lower():
        characters.append({"id": "saved", "name": "L'homme sauvé", "role": "dette / twist", "want": "vivre", "need": "", "look": "visage vu trop tard", "voice": "ordinaire", "locked": False})
    locations = [
        {"id": "appart", "name": "L'appartement la nuit", "look": "03h14, écran de téléphone", "time_of_day": "nuit", "locked": False},
        {"id": "ville", "name": "La ville, le lendemain", "look": "jour, lieu de la prédiction", "time_of_day": "jour", "locked": False},
    ]
    if "pont" in source.lower():
        locations.append({"id": "pont", "name": "Le pont", "look": "structure qui cède", "time_of_day": "jour", "locked": False})
    return {"version": 1, "logline": (parsed["concept"] or parsed["body"])[:220], "tone": parsed["genre"] or "dramatique", "locked": False, "characters": characters, "locations": locations, "props": [{"id": "phone", "name": "Le téléphone", "look": "sonne à 03h14", "story_function": "oracle", "locked": False}], "source": "stub-from-concept", "concept": concept, "genre": parsed["genre"], "start": parsed["start"], "end": parsed["end"]}


def seed_season_plan(concept: str):
    parsed = parse_concept(concept)
    names = _names(" ".join((parsed["start"], parsed["body"], parsed["end"])))
    hero = names[0] if names else "Le protagoniste"
    return [
        {"number": 1, "title": "L'appel", "logline": (parsed["start"] or f"{hero} reçoit le premier signe et n'y croit pas.")[:220], "function_in_arc": "déclencheur"},
        {"number": 2, "title": "La preuve", "logline": f"{hero} voit la première prédiction se réaliser sous ses yeux.", "function_in_arc": "confirmation"},
        {"number": 3, "title": "L'intervention", "logline": f"{hero} intervient et change le cours d'un événement annoncé.", "function_in_arc": "action"},
        {"number": 4, "title": "Le dernier appel", "logline": (parsed["end"] or f"{hero} entend sa propre fin et choisit.")[:220], "function_in_arc": "climax"},
    ]


def seed_script(episode) -> str:
    parsed = parse_concept(episode.season.project.concept)
    names = _names(" ".join((parsed["start"], parsed["body"], parsed["end"])))
    hero = names[0] if names else "Marc"
    n = episode.number
    if n == 1:
        return f"{hero} ne dort pas. 03h13. Le téléphone vibre. Numéro inconnu. Il décroche. Une voix décrit un pont qui va céder demain. {hero} raccroche. Canular, se dit-il. Il n'y croit pas encore."
    if n == 2:
        return f"Le lendemain {hero} traverse la ville. Le pont est là. Un craquement. La structure cède sous ses yeux. Il reconnaît la phrase de la nuit. Ce n'était pas un canular."
    if n == 3:
        return f"Une autre nuit. 03h14. La voix décrit un nouvel événement. {hero} sort avant l'aube. Il écarte quelqu'un. L'événement manque sa cible. {hero} comprend qu'il peut empêcher."
    return f"Dernière nuit. Le téléphone sonne. La voix décrit la mort de {hero} demain. Cause : l'homme qu'il a sauvé. {hero} ne brise pas la chaîne. Il pose le téléphone. Il accepte."
