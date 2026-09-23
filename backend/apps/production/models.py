from django.conf import settings
from django.db import models

from apps.projects.models import Project
from apps.story.models import Beat, BeatTake, Episode, Shot, ShotTake


class Asset(models.Model):
    class Kind(models.TextChoices):
        IMAGE = "image"
        VIDEO = "video"
        AUDIO = "audio"
        OTHER = "other"

    class Role(models.TextChoices):
        CHARACTER_REF = "character_ref"
        LOCATION_REF = "location_ref"
        PROP_REF = "prop_ref"
        START_FRAME = "start_frame"
        END_FRAME = "end_frame"
        CLIP = "clip"
        SCORE = "score"
        VOICE = "voice"
        EPISODE_CUT = "episode_cut"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="assets")
    beat = models.ForeignKey(
        Beat, on_delete=models.SET_NULL, null=True, blank=True, related_name="assets"
    )
    beat_take = models.ForeignKey(BeatTake, on_delete=models.SET_NULL, null=True, blank=True, related_name="assets")
    shot = models.ForeignKey(Shot, on_delete=models.SET_NULL, null=True, blank=True, related_name="assets")
    shot_take = models.ForeignKey(ShotTake, on_delete=models.SET_NULL, null=True, blank=True, related_name="assets")
    kind = models.CharField(max_length=16, choices=Kind.choices)
    role = models.CharField(max_length=32, choices=Role.choices)
    uri = models.CharField(max_length=1024)
    provider = models.CharField(max_length=64, blank=True)
    meta = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)


class Review(models.Model):
    class Decision(models.TextChoices):
        APPROVE = "approve"
        REJECT = "reject"
        REVISE = "revise"

    episode = models.ForeignKey(
        Episode, on_delete=models.CASCADE, null=True, blank=True, related_name="reviews"
    )
    beat = models.ForeignKey(
        Beat, on_delete=models.CASCADE, null=True, blank=True, related_name="reviews"
    )
    beat_take = models.ForeignKey(BeatTake, on_delete=models.CASCADE, null=True, blank=True, related_name="reviews")
    shot = models.ForeignKey(Shot, on_delete=models.CASCADE, null=True, blank=True, related_name="reviews")
    shot_take = models.ForeignKey(ShotTake, on_delete=models.CASCADE, null=True, blank=True, related_name="reviews")
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    decision = models.CharField(max_length=16, choices=Decision.choices)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
