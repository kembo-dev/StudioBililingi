from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.projects.models import Project
from apps.projects.serializers import BeatSerializer, EpisodeSerializer, ProjectCreateSerializer, ProjectSerializer
from apps.projects.services import (
    create_project,
    lock_bible,
    render_beat,
    review_beat,
    run_bible,
    run_segment,
    run_showrunner,
    write_script,
)
from apps.story.models import Beat, Episode


class ProjectViewSet(viewsets.ModelViewSet):
    http_method_names = ["get", "post", "head", "options"]
    queryset = Project.objects.prefetch_related(
        "seasons__episodes__beats__assets",
        "bibles__characters",
        "bibles__locations",
        "bibles__props",
    ).order_by("-created_at")
    serializer_class = ProjectSerializer

    def create(self, request):
        ser = ProjectCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        project = create_project(**ser.validated_data)
        run_showrunner(project)
        run_bible(project)
        project = self.get_queryset().get(pk=project.pk)
        return Response(ProjectSerializer(project).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="generate-bible")
    def generate_bible(self, request, pk=None):
        project = self.get_object()
        run_bible(project)
        project = self.get_queryset().get(pk=project.pk)
        return Response(ProjectSerializer(project).data)

    @action(detail=True, methods=["post"], url_path="plan-season")
    def plan_season(self, request, pk=None):
        project = self.get_object()
        run_showrunner(project)
        project = self.get_queryset().get(pk=project.pk)
        return Response(ProjectSerializer(project).data)

    @action(detail=True, methods=["post"], url_path="lock-bible")
    def lock_bible_action(self, request, pk=None):
        project = self.get_object()
        try:
            lock_bible(project)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        project = self.get_queryset().get(pk=project.pk)
        return Response(ProjectSerializer(project).data)


class EpisodeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Episode.objects.prefetch_related("beats", "scripts").select_related("season__project")
    serializer_class = EpisodeSerializer

    @action(detail=True, methods=["post"], url_path="write-script")
    def write_script_action(self, request, pk=None):
        episode = self.get_object()
        try:
            write_script(episode)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        episode = self.get_queryset().get(pk=episode.pk)
        return Response(EpisodeSerializer(episode).data)

    @action(detail=True, methods=["post"])
    def segment(self, request, pk=None):
        episode = self.get_object()
        script = request.data.get("script")
        run_segment(episode, script)
        episode = self.get_queryset().get(pk=episode.pk)
        return Response(EpisodeSerializer(episode).data)


class BeatViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Beat.objects.prefetch_related("assets").select_related("episode__season__project")
    serializer_class = BeatSerializer

    @action(detail=True, methods=["post"])
    def review(self, request, pk=None):
        beat = self.get_object()
        decision = request.data.get("decision", "approve")
        comment = request.data.get("comment", "")
        try:
            review_beat(beat, decision, comment)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        beat = self.get_queryset().get(pk=beat.pk)
        return Response(BeatSerializer(beat).data)

    @action(detail=True, methods=["post"])
    def render(self, request, pk=None):
        beat = self.get_object()
        render_beat(beat)
        beat = self.get_queryset().get(pk=beat.pk)
        return Response(BeatSerializer(beat).data)
