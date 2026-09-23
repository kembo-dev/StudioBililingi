from django.db import models
import secrets


def new_reference_uid():
    return secrets.token_hex(8)  # 16 stable characters

from apps.projects.models import Project


class WorldBible(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="bibles")
    version = models.PositiveIntegerField(default=1)
    payload = models.JSONField(default=dict)
    locked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("project", "version")
        ordering = ["-version"]


class Character(models.Model):
    reference_uid = models.CharField(max_length=32, unique=True, editable=False, default=new_reference_uid)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="characters")
    bible = models.ForeignKey(
        WorldBible, on_delete=models.SET_NULL, null=True, blank=True, related_name="characters"
    )
    key = models.SlugField()
    name = models.CharField(max_length=160)
    role = models.CharField(max_length=160, blank=True)
    want = models.TextField(blank=True)
    need = models.TextField(blank=True)
    look = models.TextField()
    voice = models.TextField(blank=True)
    locked = models.BooleanField(default=False)

    class Meta:
        unique_together = ("project", "key")


class Location(models.Model):
    reference_uid = models.CharField(max_length=32, unique=True, editable=False, default=new_reference_uid)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="locations")
    bible = models.ForeignKey(
        WorldBible, on_delete=models.SET_NULL, null=True, blank=True, related_name="locations"
    )
    key = models.SlugField()
    name = models.CharField(max_length=160)
    look = models.TextField()
    time_of_day = models.CharField(max_length=80, blank=True)
    locked = models.BooleanField(default=False)

    class Meta:
        unique_together = ("project", "key")


class Prop(models.Model):
    reference_uid = models.CharField(max_length=32, unique=True, editable=False, default=new_reference_uid)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="props")
    bible = models.ForeignKey(
        WorldBible, on_delete=models.SET_NULL, null=True, blank=True, related_name="props"
    )
    key = models.SlugField()
    name = models.CharField(max_length=160)
    look = models.TextField()
    story_function = models.CharField(max_length=200, blank=True)
    locked = models.BooleanField(default=False)

    class Meta:
        unique_together = ("project", "key")
