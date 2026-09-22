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
    tone = models.CharField(max_length=80, blank=True)
    ending_intent = models.TextField(blank=True)
    aspect_ratio = models.CharField(max_length=16, default="16:9")
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
