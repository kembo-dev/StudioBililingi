from rest_framework import serializers

from apps.jobs.models import Job


class JobSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = ("id", "kind", "status", "agent_role", "backend", "payload", "result", "error", "created_at", "updated_at")
