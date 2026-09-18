from apps.projects.models import Project
from apps.projects.services import persist_beats
from apps.story.models import Episode

BEATS = {
    1: [
        "Marc : Allô ? Qui est là ?",
        "La voix : Demain le pont cède. Tu seras là.",
        "Marc : C'est un canular. Ne rappelle plus.",
        "La voix : Trente secondes. Tu as entendu.",
    ],
    2: [
        "Marc : Ce pont, c'est la phrase de la nuit.",
        "Un passant : Ça bouge ! Courez !",
        "Marc : Ce n'était pas un canular.",
        "La voix : Demain le pont cède.",
    ],
    3: [
        "La voix : Une autre vie. Ce soir.",
        "Marc : Pas cette fois.",
        "L'homme : Mais qui êtes-vous ?",
        "Marc : Éloigne-toi. Maintenant.",
    ],
    4: [
        "La voix : Demain tu meurs. Par celui que tu as sauvé.",
        "Marc : Lui ? Le pont ?",
        "La voix : La chaîne ne se brise pas.",
        "Marc : Alors je reste. Je ne décroche plus.",
    ],
}

LOGLINES = {
    1: "Marc décroche à 03h14. Il croit à un canular.",
    2: "Le pont cède sous ses yeux.",
    3: "Marc écarte l'homme annoncé.",
    4: "La voix annonce sa mort. Il accepte.",
}


def apply(project=None):
    project = project or Project.objects.filter(title__icontains="Appel").order_by("-id").first()
    if project is None:
        raise ValueError("Projet L'Appel introuvable")
    project.delivery = "conversation"
    project.save(update_fields=["delivery"])
    season = project.seasons.order_by("number").first()
    for ep in Episode.objects.filter(season=season).order_by("number"):
        ep.logline = LOGLINES.get(ep.number, ep.logline)
        ep.save(update_fields=["logline"])
        persist_beats(ep, BEATS[ep.number])
    return project
