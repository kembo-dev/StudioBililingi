from django.db import models

from apps.bible.models import Character, Location, Prop
from apps.projects.models import NarrativeEvent, Season


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


class ScenePlan(models.Model):
    episode = models.ForeignKey(Episode, on_delete=models.CASCADE, related_name="scene_plans")
    script = models.ForeignKey(Script, on_delete=models.CASCADE, related_name="scene_plans")
    version = models.PositiveIntegerField(default=1)
    payload = models.JSONField(default=list)
    locked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("script", "version")
        ordering = ["-version"]


class Scene(models.Model):
    episode = models.ForeignKey(Episode, on_delete=models.CASCADE, related_name="scenes")
    script = models.ForeignKey(Script, on_delete=models.CASCADE, related_name="scenes")
    index = models.PositiveIntegerField()
    heading = models.CharField(max_length=240, blank=True)
    summary = models.TextField(blank=True)
    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=True)
    time_of_day = models.CharField(max_length=80, blank=True)
    lighting = models.TextField(blank=True)
    continuity_state = models.JSONField(default=dict)
    characters = models.ManyToManyField(Character, blank=True)
    props = models.ManyToManyField(Prop, blank=True)

    class Meta:
        unique_together = ("script", "index")
        ordering = ["index"]


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
    script = models.ForeignKey(Script, on_delete=models.SET_NULL, null=True, blank=True, related_name="beats")
    scene = models.ForeignKey(Scene, on_delete=models.SET_NULL, null=True, blank=True, related_name="beats")
    index = models.PositiveIntegerField()
    text = models.TextField(help_text="~24 words of action / dialogue")
    word_count = models.PositiveSmallIntegerField(default=0)
    duration_seconds = models.DecimalField(max_digits=4, decimal_places=1, default=8)
    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=True)
    characters = models.ManyToManyField(Character, blank=True)
    props = models.ManyToManyField(Prop, blank=True)
    camera = models.JSONField(default=dict)
    continuity = models.JSONField(default=dict)
    emotion = models.CharField(max_length=80, blank=True)
    dialogue = models.TextField(blank=True)
    speaker = models.ForeignKey(
        Character,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="spoken_beats",
        help_text="Canonical character speaking in this beat.",
    )
    narrative_event = models.ForeignKey(
        NarrativeEvent,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="beats",
        help_text="Canonical narrative event advanced by this beat.",
    )
    video_prompt = models.TextField(blank=True)
    negative_prompt = models.TextField(blank=True)
    backend = models.CharField(max_length=64, default="google-veo-3.1")
    take = models.PositiveIntegerField(default=1, help_text="Legacy display field; generations are stored in BeatTake.")
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.DRAFT)

    class Meta:
        unique_together = ("script", "index")
        ordering = ["index"]


class BeatTake(models.Model):
    class Status(models.TextChoices):
        QUEUED = "queued"
        RENDERING = "rendering"
        REVIEW = "review"
        REJECTED = "rejected"
        LOCKED = "locked"
        FAILED = "failed"

    beat = models.ForeignKey(Beat, on_delete=models.CASCADE, related_name="takes")
    number = models.PositiveIntegerField()
    prompt = models.TextField(blank=True)
    negative_prompt = models.TextField(blank=True)
    backend = models.CharField(max_length=64, blank=True)
    uri = models.CharField(max_length=1024, blank=True)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.QUEUED)
    generation_meta = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("beat", "number")
        ordering = ["number"]
