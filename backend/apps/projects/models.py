from django.db import models

from apps.accounts.models import Organization


class Project(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft"
        ACTIVE = "active"
        ARCHIVED = "archived"

    class VisualStyle(models.TextChoices):
        REALISTIC = "realistic", "Réaliste cinématographique"
        REALISTIC_IMPERFECT = "realistic_imperfect", "Réaliste avec imperfections réelles"
        CARTOON = "cartoon", "Cartoon"
        MANGA = "manga", "Manga / Anime"
        THREE_D = "3d_animation", "Animation 3D"
        COMIC = "comic", "Bande dessinée / Comic"
        WATERCOLOR = "watercolor", "Aquarelle"
        CLAY = "claymation", "Claymation"
        PIXEL = "pixel_art", "Pixel art"
        NOIR = "film_noir", "Film noir"
        FANTASY = "fantasy", "Fantasy stylisée"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="projects"
    )
    title = models.CharField(max_length=200)
    slug = models.SlugField()
    concept = models.TextField(help_text="Histoire, début, fin voulue, contraintes")
    genre = models.CharField(max_length=80, blank=True)
    subgenre = models.CharField(max_length=80, blank=True)
    setting = models.CharField(max_length=160, blank=True, help_text="Cadre géographique/culturel canonique du projet.")
    episode_count_target = models.PositiveSmallIntegerField(null=True, blank=True, help_text="Nombre d'épisodes souhaité; vide = automatique.")
    episode_duration_seconds = models.PositiveSmallIntegerField(null=True, blank=True, default=None, help_text="Durée cible par épisode en secondes; vide = durée naturelle automatique par épisode.")
    tone = models.CharField(max_length=80, blank=True)
    ending_intent = models.TextField(blank=True)
    aspect_ratio = models.CharField(max_length=16, default="16:9")
    audio_contract = models.JSONField(
        default=dict,
        blank=True,
        help_text="Contrat canonique de langue, narration et identité vocale du projet.",
    )
    visual_style = models.CharField(
        max_length=32,
        choices=VisualStyle.choices,
        default=VisualStyle.REALISTIC,
        help_text="Direction visuelle canonique appliquée aux références et aux rendus.",
    )
    delivery = models.CharField(
        max_length=24,
        default="storytell",
        help_text="storytell | voix_off | conversation | rencontre",
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("organization", "slug")

    def __str__(self) -> str:
        return self.title


class Season(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="seasons")
    number = models.PositiveSmallIntegerField(default=1)
    title = models.CharField(max_length=200, blank=True)
    premise = models.TextField(blank=True)

    class Meta:
        unique_together = ("project", "number")
        ordering = ["number"]


class NarrativeContract(models.Model):
    class PointOfView(models.TextChoices):
        THIRD_PERSON = "third_person", "Troisième personne"
        FIRST_PERSON = "first_person", "Première personne"
        DIALOGUE = "dialogue", "Dialogue / sans narrateur"

    project = models.OneToOneField(Project, on_delete=models.CASCADE, related_name="narrative_contract")
    point_of_view = models.CharField(max_length=24, choices=PointOfView.choices, default=PointOfView.THIRD_PERSON)
    narrator = models.CharField(max_length=80, default="external")
    tense = models.CharField(max_length=24, default="present")
    story_type = models.CharField(max_length=40, blank=True)
    recommended_episode_count = models.PositiveSmallIntegerField(default=1)
    rules = models.JSONField(default=dict, blank=True)
    locked = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class NarrativeEvent(models.Model):
    class Status(models.TextChoices):
        PLANNED = "planned", "Planifié"
        SCRIPTED = "scripted", "Scénarisé"
        CONSUMED = "consumed", "Consommé"

    contract = models.ForeignKey(NarrativeContract, on_delete=models.CASCADE, related_name="events")
    key = models.CharField(max_length=32)
    position = models.PositiveSmallIntegerField()
    description = models.TextField()
    episode_number = models.PositiveSmallIntegerField(default=1)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PLANNED)

    class Meta:
        ordering = ["position"]
        unique_together = (("contract", "key"), ("contract", "position"))
