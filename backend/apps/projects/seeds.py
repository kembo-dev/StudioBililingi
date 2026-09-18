def seed_bible(concept: str) -> dict:
    text = concept.strip() or "Une histoire sans titre"
    lower = text.lower()
    school = any(word in lower for word in ("élève", "eleve", "ecole", "école", "professeur", "salut"))
    if school:
        hero, hero_look = "L'élève", "enfant ou ado, cartable, sourire, vêtements simples"
        other, other_look = "Le professeur", "adulte, tenue sobre, accueil à la porte de l'école"
        place, place_look = "La route vers l'école", "rue animée le matin, maisons, passants"
        extra, extra_look = "La cour de l'école", "portail, bâtiment clair, élèves qui arrivent"
        prop = ("Le cartable", "sac d'école usé")
        tone = "lumineux, simple"
    else:
        hero, hero_look = "Le héros", f"personnage principal : {text[:80]}"
        other, other_look = "La figure d'arrivée", "personne rencontrée à la fin"
        place, place_look = "Le chemin", "extérieur, lumière du jour"
        extra, extra_look = "Le lieu d'arrivée", "destination du concept"
        prop = ("L'objet du trajet", "objet porté par le héros")
        tone = "narratif"
    return {
        "version": 1,
        "logline": text[:180],
        "tone": tone,
        "locked": False,
        "characters": [
            {"id": "protag", "name": hero, "role": "protagoniste", "want": "arriver au bout du chemin", "need": "rester ouvert aux autres", "look": hero_look, "voice": "chaleureux", "locked": False},
            {"id": "welcome", "name": other, "role": "accueil / figure finale", "want": "recevoir le héros", "need": "", "look": other_look, "voice": "posé", "locked": False},
        ],
        "locations": [
            {"id": "chemin", "name": place, "look": place_look, "time_of_day": "matin", "locked": False},
            {"id": "arrivee", "name": extra, "look": extra_look, "time_of_day": "matin", "locked": False},
        ],
        "props": [{"id": "objet", "name": prop[0], "look": prop[1], "story_function": "compagnon de route", "locked": False}],
        "source": "stub-from-concept",
        "concept": text,
    }


def seed_season_plan(concept: str) -> list[dict]:
    text = concept.strip()
    return [
        {"number": 1, "title": "Le départ", "logline": text[:140] or "Le héros part.", "function_in_arc": "déclencheur"},
        {"number": 2, "title": "La route", "logline": "Sur le chemin, il salue ceux qu'il croise.", "function_in_arc": "progression"},
        {"number": 3, "title": "Presque arrivé", "logline": "Le lieu d'arrivée se dessine.", "function_in_arc": "point médian"},
        {"number": 4, "title": "L'arrivée", "logline": "Il arrive et salue la figure qui l'attend.", "function_in_arc": "climax / fermeture"},
    ]


def seed_script(episode) -> str:
    concept = episode.season.project.concept
    return f"{episode.title}. {episode.logline} {concept} Il avance, salue, continue. La destination se rapproche. Il arrive et dit bonjour."
