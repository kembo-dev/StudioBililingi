from django.db import models

from apps.bible.models import Character, Location, Prop
from apps.projects.models import Season


class Episode(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft"
        OUTLINED = "outlined"
        SCRIPTED = "scripted"
        SEGMENTED = "segmented"
        IN_PRODUCTION = "in_production"
        REVIEW = "review"
        LOCKED = "locked"

    season = models.ForeignKey(Season, on_delete=models.CASCADE, related_name="episodes")
    number = models.PositiveSmallIntegerField()
    title = models.CharField(max_length=200)
    logline = models.TextField()
    function_in_arc = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.DRAFT)
    characters = models.ManyToManyField(Character, blank=True)
    locations = models.ManyToManyField(Location, blank=True)
    props = models.ManyToManyField(Prop, blank=True)

    class Meta:
        unique_together = ("season", "number")
        ordering = ["number"]


class Script(models.Model):
    episode = models.ForeignKey(Episode, on_delete=models.CASCADE, related_name="scripts")
    version = models.PositiveIntegerField(default=1)
    fountain = models.TextField(blank=True)
    payload = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("episode", "version")
        ordering = ["-version"]


class Beat(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft"
        APPROVED_TEXT = "approved_text"
        READY_TO_RENDER = "ready_to_render"
        RENDERING = "rendering"
        REVIEW = "review"
        REJECTED = "rejected"
        LOCKED = "locked"

    episode = models.ForeignKey(Episode, on_delete=models.CASCADE, related_name="beats")
    script = models.ForeignKey(
        Script, on_delete=models.SET_NULL, null=True, blank=True, related_name="beats"
    )
    index = models.PositiveIntegerField()
    text = models.TextField(help_text="~24 words of action / dialogue")
    word_count = models.PositiveSmallIntegerField(default=0)
    duration_seconds = models.DecimalField(max_digits=4, decimal_places=1, default=8)
    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=True)
    characters = models.ManyToManyField(Character, blank=True)
    props = models.ManyToManyField(Prop, blank=True)
    camera = models.JSONField(default=dict)
    emotion = models.CharField(max_length=80, blank=True)
    dialogue = models.TextField(blank=True)
    video_prompt = models.TextField(blank=True)
    negative_prompt = models.TextField(blank=True)
    backend = models.CharField(max_length=64, default="google-veo-3.1")
    take = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.DRAFT)

    class Meta:
        unique_together = ("episode", "index", "take")
        ordering = ["index", "take"]
