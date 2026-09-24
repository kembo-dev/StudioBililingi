from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.projects.models import Project
from apps.projects.serializers import BeatSerializer, EpisodeSerializer, ProjectCreateSerializer, ProjectSerializer
from apps.projects.services import (
    assist_concept,
    create_project,
    lock_bible,
    lock_scene_plan,
    plan_scenes,
    persist_narrative_contract,
    review_beat,
    review_shot,
    plan_beat_shots,
    run_bible,
    run_segment,
    run_showrunner,
    write_script,
)
from apps.story.models import Beat, Episode, Shot


class ProjectViewSet(viewsets.ModelViewSet):
    http_method_names = ["get", "post", "delete", "head", "options"]
    queryset = Project.objects.prefetch_related(
        "seasons__episodes__beats__assets",
        "bibles__characters",
        "bibles__locations",
        "bibles__props",
        "assets",
    ).order_by("-created_at")
    serializer_class = ProjectSerializer

    @action(detail=False, methods=["post"], url_path="assist-concept")
    def assist_concept_action(self, request):
        idea = str(request.data.get("idea") or "").strip()
        delivery = str(request.data.get("delivery") or "storytell").strip()
        if delivery not in {"storytell", "voix_off", "conversation", "rencontre"}:
            return Response({"detail": "Mode de livraison invalide"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            result = assist_concept(idea=idea, delivery=delivery)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            message = str(exc)
            code = status.HTTP_429_TOO_MANY_REQUESTS if "429" in message and "RESOURCE_EXHAUSTED" in message else status.HTTP_400_BAD_REQUEST
            return Response({"detail": message, "retryable": code == status.HTTP_429_TOO_MANY_REQUESTS}, status=code)
        if bool(request.data.get("persist")):
            project_id = request.data.get("project_id")
            if not project_id:
                return Response({"detail": "project_id est requis pour persister le contrat"}, status=status.HTTP_400_BAD_REQUEST)
            project = self.get_queryset().filter(pk=project_id).first()
            if project is None:
                return Response({"detail": "Projet introuvable"}, status=status.HTTP_404_NOT_FOUND)
            persist_narrative_contract(
                project,
                events=result["events"],
                story_type=result["story_type"],
                recommended_episode_count=result["recommended_episode_count"],
            )
        return Response(result)

    def create(self, request):
        ser = ProjectCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        project = create_project(**ser.validated_data)
        try:
            # The Bible establishes canonical identities first. The Showrunner
            # must plan episodes from those exact names/locations, never invent
            # a parallel cast before the Bible exists.
            run_bible(project)
            run_showrunner(project)
        except RuntimeError as exc:
            message = str(exc)
            code = status.HTTP_429_TOO_MANY_REQUESTS if "429" in message and "RESOURCE_EXHAUSTED" in message else status.HTTP_400_BAD_REQUEST
            return Response(
                {"detail": message, "project_id": project.id, "retryable": code == status.HTTP_429_TOO_MANY_REQUESTS},
                status=code,
            )
        project = self.get_queryset().get(pk=project.pk)
        return Response(ProjectSerializer(project).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="generate-bible")
    def generate_bible(self, request, pk=None):
        project = self.get_object()
        try:
            run_bible(project)
        except RuntimeError as exc:
            message = str(exc)
            code = status.HTTP_429_TOO_MANY_REQUESTS if "429" in message and "RESOURCE_EXHAUSTED" in message else status.HTTP_400_BAD_REQUEST
            return Response({"detail": message, "retryable": code == status.HTTP_429_TOO_MANY_REQUESTS}, status=code)
        project = self.get_queryset().get(pk=project.pk)
        return Response(ProjectSerializer(project).data)

    @action(detail=True, methods=["post"], url_path="plan-season")
    def plan_season(self, request, pk=None):
        project = self.get_object()
        try:
            run_showrunner(project)
        except RuntimeError as exc:
            message = str(exc)
            code = status.HTTP_429_TOO_MANY_REQUESTS if "429" in message and "RESOURCE_EXHAUSTED" in message else status.HTTP_400_BAD_REQUEST
            return Response({"detail": message, "retryable": code == status.HTTP_429_TOO_MANY_REQUESTS}, status=code)
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

    @action(detail=True, methods=["post"], url_path="add-reference")
    def add_reference_action(self, request, pk=None):
        from apps.projects.visuals import add_manual_ref

        project = self.get_object()
        try:
            entity = add_manual_ref(
                project,
                entity_type=request.data.get("entity_type", ""),
                name=request.data.get("name", ""),
                look=request.data.get("look", ""),
                role=request.data.get("role", ""),
                time_of_day=request.data.get("time_of_day", ""),
                story_function=request.data.get("story_function", ""),
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        project = self.get_queryset().get(pk=project.pk)
        return Response(ProjectSerializer(project).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="delete-reference")
    def delete_reference_action(self, request, pk=None):
        from apps.projects.visuals import delete_visual_ref

        project = self.get_object()
        asset_id = request.data.get("asset_id")
        if not asset_id:
            return Response({"detail": "asset_id est requis"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            delete_visual_ref(project, int(asset_id))
        except (TypeError, ValueError) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        project = self.get_queryset().get(pk=project.pk)
        return Response(ProjectSerializer(project).data)

    @action(detail=True, methods=["post"], url_path="regenerate-reference")
    def regenerate_reference_action(self, request, pk=None):
        from apps.projects.visuals import regenerate_visual_ref

        project = self.get_object()
        entity_type = str(request.data.get("entity_type") or "").strip()
        entity_key = str(request.data.get("entity_key") or "").strip()
        if not entity_type or not entity_key:
            return Response({"detail": "entity_type et entity_key sont requis"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            asset = regenerate_visual_ref(project, entity_type, entity_key, custom_prompt=request.data.get("custom_prompt", ""))
        except Exception as exc:
            message = str(exc)
            if "429" in message and ("RESOURCE_EXHAUSTED" in message or "Resource exhausted" in message):
                return Response(
                    {"detail": "Quota/capacité Vertex AI temporairement épuisé. L'ancienne référence est conservée.", "retryable": True},
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )
            if isinstance(exc, (ValueError, RuntimeError)):
                return Response({"detail": message}, status=status.HTTP_400_BAD_REQUEST)
            raise
        return Response({
            "id": asset.id, "role": asset.role, "uri": asset.uri,
            "provider": asset.provider, "meta": asset.meta,
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="regenerate-character-ref")
    def regenerate_character_ref_action(self, request, pk=None):
        from apps.projects.visuals import regenerate_character_ref

        project = self.get_object()
        character_key = str(request.data.get("character_key") or "").strip()
        if not character_key:
            return Response({"detail": "character_key est requis"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            asset = regenerate_character_ref(project, character_key)
        except Exception as exc:
            message = str(exc)
            if "429" in message and ("RESOURCE_EXHAUSTED" in message or "Resource exhausted" in message):
                return Response(
                    {
                        "detail": "Quota/capacité Vertex AI temporairement épuisé. L'ancienne référence est conservée.",
                        "retryable": True,
                    },
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )
            if isinstance(exc, (ValueError, RuntimeError)):
                return Response({"detail": message}, status=status.HTTP_400_BAD_REQUEST)
            raise
        return Response({
            "id": asset.id,
            "role": asset.role,
            "uri": asset.uri,
            "provider": asset.provider,
            "meta": asset.meta,
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="generate-refs")
    def generate_refs_action(self, request, pk=None):
        from apps.jobs.models import Job
        from apps.jobs.queue import enqueue, is_eager

        project = self.get_object()
        bible = project.bibles.first()
        if bible is None or not bible.locked:
            return Response({"detail": "Verrouille la bible avant les références visuelles"}, status=status.HTTP_400_BAD_REQUEST)
        job = enqueue(project=project, kind=Job.Kind.IMAGE, agent_role="art_director", payload={"project_id": project.id})
        if is_eager() and job.status == Job.Status.FAILED:
            return Response({"detail": job.error}, status=status.HTTP_400_BAD_REQUEST)
        if is_eager():
            project = self.get_queryset().get(pk=project.pk)
            return Response({
                "job_id": job.id,
                "status": job.status,
                "project": ProjectSerializer(project).data,
            })
        return Response(
            {"job_id": job.id, "status": job.status},
            status=status.HTTP_202_ACCEPTED,
        )


class EpisodeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Episode.objects.prefetch_related("beats", "scripts").select_related("season__project")
    serializer_class = EpisodeSerializer

    @action(detail=True, methods=["post"], url_path="write-script")
    def write_script_action(self, request, pk=None):
        episode = self.get_object()
        try:
            write_script(episode)
        except (ValueError, RuntimeError) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        episode = self.get_queryset().get(pk=episode.pk)
        return Response(EpisodeSerializer(episode).data)

    @action(detail=True, methods=["post"], url_path="plan-scenes")
    def plan_scenes_action(self, request, pk=None):
        episode = self.get_object()
        project = episode.season.project
        try:
            contract = getattr(project, "narrative_contract", None)
            has_episode_events = bool(
                contract and contract.events.filter(episode_number=episode.number).exists()
            )
            if not has_episode_events:
                # Legacy projects created before the narrative ledger existed are
                # repaired from the locked Bible. Re-plan first so canonical
                # character identities cannot drift, then rewrite this script.
                run_showrunner(project)
                episode.refresh_from_db()
                write_script(episode)
            script = episode.scripts.order_by("-version").first()
            if script is None:
                return Response({"detail": "Écris le script avant de planifier les scènes"}, status=status.HTTP_400_BAD_REQUEST)
            plan_scenes(episode, script.fountain, persist=True)
        except (ValueError, RuntimeError) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        episode = self.get_queryset().get(pk=episode.pk)
        return Response(EpisodeSerializer(episode).data)

    @action(detail=True, methods=["post"], url_path="lock-scene-plan")
    def lock_scene_plan_action(self, request, pk=None):
        episode = self.get_object()
        try:
            lock_scene_plan(episode, request.data.get("scene_plan_id"))
        except (TypeError, ValueError) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        episode = self.get_queryset().get(pk=episode.pk)
        return Response(EpisodeSerializer(episode).data)

    @action(detail=True, methods=["post"])
    def segment(self, request, pk=None):
        episode = self.get_object()
        script = request.data.get("script")
        try:
            run_segment(episode, script)
        except (ValueError, RuntimeError) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        episode = self.get_queryset().get(pk=episode.pk)
        return Response(EpisodeSerializer(episode).data)

    @action(detail=True, methods=["post"])
    def assemble(self, request, pk=None):
        from apps.jobs.models import Job
        from apps.jobs.queue import enqueue, is_eager
        from apps.projects.assembly import assemble_episode

        episode = self.get_object()
        # Validate the complete locked-shot timeline before creating a queue job.
        # This gives the editor an immediate, precise error instead of spending a
        # worker slot on an episode that cannot yet be assembled.
        try:
            if not is_eager():
                latest_script = episode.scripts.order_by("-version").first()
                if latest_script is None:
                    raise ValueError("Aucun script à assembler")
                segmentation = latest_script.segmentations.order_by("-version").first()
                beats_qs = segmentation.beats if segmentation else latest_script.beats
                from apps.story.models import ShotTake
                for beat in beats_qs.order_by("index").prefetch_related("shots__takes"):
                    shots = list(beat.shots.order_by("index"))
                    if not shots:
                        raise ValueError(f"Beat {beat.index}: aucun shot de production")
                    for shot in shots:
                        if not shot.takes.filter(status=ShotTake.Status.LOCKED).exclude(uri="").exists():
                            raise ValueError(f"Beat {beat.index} / Shot {shot.index}: aucun take verrouillé")
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        job = enqueue(
            project=episode.season.project,
            kind=Job.Kind.ASSEMBLY,
            agent_role="editor",
            payload={"episode_id": episode.id},
        )
        if is_eager() and job.status == Job.Status.FAILED:
            return Response({"detail": job.error}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"job_id": job.id, "status": job.status, "result": job.result})


class ShotViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Shot.objects.select_related("beat__episode__season__project").prefetch_related("takes")
    serializer_class = __import__("apps.projects.serializers", fromlist=["ShotSerializer"]).ShotSerializer

    @action(detail=True, methods=["post"])
    def review(self, request, pk=None):
        shot = self.get_object()
        try:
            review_shot(shot, request.data.get("decision", "approve"), request.data.get("comment", ""), take_id=request.data.get("take_id"))
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.serializer_class(self.get_queryset().get(pk=shot.pk)).data)

    @action(detail=True, methods=["post"], url_path="upload-adjustment-reference")
    def upload_adjustment_reference(self, request, pk=None):
        import uuid
        from pathlib import Path
        from django.conf import settings

        shot = self.get_object()
        upload = request.FILES.get("file")
        if upload is None:
            return Response({"detail": "Ajoute une image de référence"}, status=status.HTTP_400_BAD_REQUEST)
        content_type = str(getattr(upload, "content_type", "") or "")
        if not content_type.startswith("image/"):
            return Response({"detail": "La pièce jointe doit être une image"}, status=status.HTTP_400_BAD_REQUEST)
        if getattr(upload, "size", 0) > 15 * 1024 * 1024:
            return Response({"detail": "La pièce jointe est limitée à 15 Mo"}, status=status.HTTP_400_BAD_REQUEST)
        suffix = Path(str(upload.name or "")).suffix.lower()
        if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
            suffix = ".jpg"
        project = shot.beat.episode.season.project
        relative = Path("adjustment-refs") / f"{project.id}-{project.slug}" / f"shot-{shot.id}"
        directory = Path(settings.MEDIA_ROOT) / relative
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / f"{uuid.uuid4().hex}{suffix}"
        with target.open("wb") as handle:
            for chunk in upload.chunks():
                handle.write(chunk)
        uri = f"/media/{relative.as_posix()}/{target.name}"
        return Response({"uri": uri, "name": upload.name}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def render(self, request, pk=None):
        from apps.jobs.models import Job
        from apps.jobs.queue import enqueue, is_eager
        shot = self.get_object()
        adjustment_prompt = str(request.data.get("prompt") or request.data.get("adjustment_prompt") or "").strip()
        adjustment_reference_uri = str(request.data.get("adjustment_reference_uri") or "").strip()
        adjustment_mode = str(request.data.get("adjustment_mode") or "custom").strip()
        if adjustment_mode == "language":
            adjustment_prompt = (
                "LANGUAGE REPAIR: keep the exact same visual shot, identities, framing and story action. "
                "Correct only the spoken audio. Speak ONLY the canonical dialogue from the script, verbatim, "
                "in its original language. If the canonical dialogue is French, speak French only. "
                "Never translate to English or another language and never add narration."
            )
        elif adjustment_mode == "script":
            adjustment_prompt = (
                "SCRIPT REPAIR: regenerate this take to follow the canonical script exactly. "
                "Preserve character identities and visual continuity. Perform only the canonical action and "
                "speak only the canonical dialogue verbatim. Do not invent, omit, translate, paraphrase or narrate."
            )
        active = Job.objects.filter(
            project=shot.beat.episode.season.project,
            kind=Job.Kind.VIDEO,
            status__in=[Job.Status.QUEUED, Job.Status.RUNNING],
            payload__shot_id=shot.id,
        ).order_by("-created_at").first()
        if active is not None:
            active_prompt = str((active.payload or {}).get("adjustment_prompt") or "").strip()
            if active_prompt != adjustment_prompt:
                return Response(
                    {"detail": "Un take est déjà en génération pour ce shot. Attends sa fin avant de lancer un nouveau réajustement."},
                    status=status.HTTP_409_CONFLICT,
                )
            return Response({"job_id": active.id, "status": active.status, "result": active.result})
        if len(adjustment_prompt) > 4000:
            return Response({"detail": "Le prompt de réajustement est limité à 4000 caractères"}, status=status.HTTP_400_BAD_REQUEST)
        job = enqueue(
            project=shot.beat.episode.season.project,
            kind=Job.Kind.VIDEO,
            agent_role="cinematographer",
            payload={
                "shot_id": shot.id,
                "adjustment_prompt": adjustment_prompt,
                "adjustment_reference_uri": adjustment_reference_uri,
                "adjustment_mode": adjustment_mode,
            },
        )
        if is_eager() and job.status == Job.Status.FAILED:
            return Response({"detail": job.error}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"job_id": job.id, "status": job.status, "result": job.result})


class BeatViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Beat.objects.prefetch_related("assets").select_related("episode__season__project")
    serializer_class = BeatSerializer

    @action(detail=True, methods=["post"], url_path="plan-shots")
    def plan_shots(self, request, pk=None):
        beat = self.get_object()
        shots = plan_beat_shots(beat)
        from apps.projects.serializers import ShotSerializer
        return Response(ShotSerializer(shots, many=True).data)

    @action(detail=True, methods=["post"], url_path="recontextualize")
    def recontextualize(self, request, pk=None):
        from apps.projects.rewrite import recontextualize_beat

        beat = self.get_object()
        try:
            recontextualize_beat(beat, request.data.get("prompt") or request.data.get("instruction") or "", form=beat.episode.season.project.delivery)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        beat = self.get_queryset().get(pk=beat.pk)
        return Response(BeatSerializer(beat).data)

    @action(detail=True, methods=["post"])
    def review(self, request, pk=None):
        beat = self.get_object()
        decision = request.data.get("decision", "approve")
        comment = request.data.get("comment", "")
        try:
            review_beat(beat, decision, comment, take_id=request.data.get("take_id"))
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        beat = self.get_queryset().get(pk=beat.pk)
        return Response(BeatSerializer(beat).data)

    @action(detail=True, methods=["get"], url_path="render-readiness")
    def render_readiness(self, request, pk=None):
        from apps.projects.continuity import validate_render_readiness

        beat = self.get_object()
        readiness = validate_render_readiness(beat)
        pack = readiness["ingredients"]
        return Response({
            "ready": readiness["ready"],
            "errors": readiness["errors"],
            "prompt": readiness["prompt"],
            "continuity": readiness["context"],
            "ingredients": pack["items"],
            "start_frame": pack["start_frame"],
            "duration_seconds": float(beat.duration_seconds),
            "aspect_ratio": beat.episode.season.project.aspect_ratio,
        })

    @action(detail=True, methods=["post"])
    def render(self, request, pk=None):
        from apps.jobs.models import Job
        from apps.jobs.queue import enqueue, is_eager

        beat = self.get_object()
        from apps.projects.continuity import validate_render_readiness
        readiness = validate_render_readiness(beat)
        if not readiness["ready"]:
            return Response(
                {"detail": "Rendu vidéo refusé", "errors": readiness["errors"]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        beat.status = beat.Status.RENDERING
        beat.save(update_fields=["status"])
        job = enqueue(
            project=beat.episode.season.project,
            kind=Job.Kind.VIDEO,
            agent_role="cinematographer",
            payload={"beat_id": beat.id},
        )
        if is_eager() and job.status == Job.Status.FAILED:
            return Response({"detail": job.error}, status=status.HTTP_400_BAD_REQUEST)
        beat = self.get_queryset().get(pk=beat.pk)
        return Response(BeatSerializer(beat).data)
