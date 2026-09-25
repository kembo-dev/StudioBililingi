from __future__ import annotations

from agents.backends import get_text


class Showrunner:
    """Root role. Builds a story-specific season arc and stops at HITL checkpoints."""

    role = "showrunner"

    def __init__(self):
        self.text = get_text(role=self.role)

    def plan(self, concept: str, *, delivery: str = "storytell", bible: dict | None = None) -> dict:
        return self.text.generate_json(
            system=(
                "Tu es le showrunner de StudioBililingi. Construis un plan de saison STRICTEMENT spécifique au concept "
                "fourni. Réponds en JSON avec: logline, tone, episode_count, episodes, checkpoints. "
                "episodes est une liste d'objets {number,title,logline,function_in_arc,events}. events contient les faits/actions "
                "concrets, ordonnés et non redondants réservés exclusivement à cet épisode. "
                "Les CONTRAINTES PROJET VERROUILLEES éventuellement fournies sont canoniques: respecte genre, sous-genre, cadre géographique/culturel, durée cible et mode. Si episode_count_target contient un nombre, produis exactement ce nombre d'épisodes sans répéter les événements: répartis et approfondis uniquement la matière réellement présente. Si la cible est absente, choisis le NOMBRE NATUREL D'EPISODES selon la quantité réelle d'événements du concept. Une histoire "
                "courte et linéaire doit rester UN SEUL épisode; ne l'étire jamais artificiellement. Si plusieurs épisodes "
                "sont réellement nécessaires, attribue chaque événement du concept à UN SEUL épisode et ne le rejoue jamais. "
                "Chaque épisode doit faire avancer le même arc causal: situation initiale -> découverte/décision -> "
                "complication/transformation -> résolution fidèle à la fin donnée par le concept. "
                "N'importe jamais des motifs d'un autre genre (appel mystérieux, prédiction, catastrophe, enquête, etc.) "
                "s'ils ne sont pas dans le concept. Ne transforme pas les libellés du concept comme Début, Accroche, "
                "Fin ou Twist en noms de personnages. Utilise les vrais personnages et enjeux du concept. "
                f"Le mode de livraison est {delivery}; il influence la mise en scène, pas l'intrigue. Français naturel."
            ),
            user=concept + f"\n\nBIBLE CANONIQUE VERROUILLEE:\n{bible or {}}",
        )
