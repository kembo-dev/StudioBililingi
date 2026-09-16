from django.db import models

from apps.projects.models import Project


class Job(models.Model):
    class Kind(models.TextChoices):
        BIBLE = "bible"
        SCRIPT = "script"
        SEGMENT = "segment"
        IMAGE = "image"
        VIDEO = "video"
        AUDIO = "audio"
        ASSEMBLY = "assembly"

    class Status(models.TextChoices):
        QUEUED = "queued"
        RUNNING = "running"
        SUCCEEDED = "succeeded"
        FAILED = "failed"
        CANCELLED = "cancelled"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="jobs")
    kind = models.CharField(max_length=24, choices=Kind.choices)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.QUEUED)
    agent_role = models.CharField(max_length=64, blank=True)
    backend = models.CharField(max_length=64, blank=True)
    payload = models.JSONField(default=dict)
    result = models.JSONField(default=dict)
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
