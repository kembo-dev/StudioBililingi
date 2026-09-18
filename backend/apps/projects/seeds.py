import re


def _names(concept: str) -> list[str]:
    found = re.findall(r"\b([A-ZÉÈÀ][a-zàâéèêëïîôùûçA-Z]{2,})\b", concept or "")
    skip = {"Le", "La", "Les", "Un", "Une", "Des", "Sur", "Dans", "Pour", "Avec", "Aller", "Apprendre"}
    names = []
    for name in found:
        if name not in skip and name not in names:
            names.append(name)
    for raw in re.findall(r"\b(mbelu|ngalu)\b", (concept or "").lower()):
        pretty = raw[:1].upper() + raw[1:]
        if pretty not in names:
            names.append(pretty)
    return names


def seed_bible(concept: str) -> dict:
    text = concept.strip() or "Une histoire sans titre"
    lower = text.lower()
    names = _names(text)
    work = any(w in lower for w in ("travaille", "travail", "bureau", "collègue", "collegeu"))
    school = (not work) and any(w in lower for w in ("élève", "eleve", "école", "ecole", "professeur", "cartable"))
    hero = names[0] if names else "Le héros"
    other = names[1] if len(names) > 1 else ("Le collègue" if work else "La figure d'arrivée")
    if work:
        hero_look, other_look = "adulte, tenue de travail simple", "collègue au bureau"
        place, extra = ("La route vers le travail", "rue le matin"), ("Le lieu de travail", "entrée du bureau")
        prop, tone = ("Le sac de travail", "sacoche"), "quotidien, chaleureux"
    elif school:
        hero_look, other_look = "enfant ou ado, cartable", "adulte à la porte de l'école"
        place, extra = ("La route vers l'école", "rue le matin"), ("La cour de l'école", "portail")
        prop, tone = ("Le cartable", "sac d'école"), "lumineux, simple"
    else:
        hero_look, other_look = text[:80], "personne à l'arrivée"
        place, extra = ("Le chemin", "extérieur"), ("Le lieu d'arrivée", "destination")
        prop, tone = ("L'objet du trajet", "objet porté"), "narratif"
    return {
        "version": 1,
        "logline": text[:180],
        "tone": tone,
        "locked": False,
        "characters": [
            {"id": "protag", "name": hero, "role": "protagoniste", "want": "arriver", "need": "saluer", "look": hero_look, "voice": "chaleureux", "locked": False},
            {"id": "welcome", "name": other, "role": "accueil / collègue", "want": "recevoir", "need": "", "look": other_look, "voice": "posé", "locked": False},
        ],
        "locations": [
            {"id": "chemin", "name": place[0], "look": place[1], "time_of_day": "matin", "locked": False},
            {"id": "arrivee", "name": extra[0], "look": extra[1], "time_of_day": "matin", "locked": False},
        ],
        "props": [{"id": "objet", "name": prop[0], "look": prop[1], "story_function": "trajet", "locked": False}],
        "source": "stub-from-concept",
        "concept": text,
    }


def seed_season_plan(concept: str) -> list[dict]:
    names = _names(concept)
    hero = names[0] if names else "Le héros"
    other = names[1] if len(names) > 1 else "la personne à l'arrivée"
    return [
        {"number": 1, "title": "Le départ", "logline": f"{hero} se prépare et part.", "function_in_arc": "déclencheur"},
        {"number": 2, "title": "La route", "logline": f"{hero} salue les gens sur le chemin.", "function_in_arc": "progression"},
        {"number": 3, "title": "Presque arrivé", "logline": f"Le lieu de {hero} apparaît.", "function_in_arc": "point médian"},
        {"number": 4, "title": "L'arrivée", "logline": f"{hero} arrive et salue {other}.", "function_in_arc": "climax"},
    ]


def seed_script(episode) -> str:
    return f"{episode.title}. {episode.logline} {episode.season.project.concept} Il avance, salue, continue. Il arrive et dit bonjour."
