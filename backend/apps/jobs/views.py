from rest_framework import viewsets

from apps.jobs.models import Job
from apps.jobs.serializers import JobSerializer


class JobViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Job.objects.order_by("-created_at")
    serializer_class = JobSerializer
