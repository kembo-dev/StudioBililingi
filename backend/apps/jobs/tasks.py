from celery import shared_task


@shared_task(
    bind=True,
    autoretry_for=(),
    max_retries=5,
)
def run_studio_job(self, job_id: int) -> dict:
    from apps.jobs.models import Job
    from apps.projects.continuity import render_beat
    from apps.projects.services import render_shot
    from apps.projects.models import Project
    from apps.projects.visuals import generate_refs
    from apps.story.models import Beat, Shot

    job = Job.objects.get(pk=job_id)
    job.status = Job.Status.RUNNING
    job.save(update_fields=["status", "updated_at"])
    try:
        payload = job.payload or {}
        if job.kind == Job.Kind.VIDEO:
            if payload.get("shot_id"):
                shot = Shot.objects.get(pk=payload["shot_id"])
                render_shot(
                    shot,
                    adjustment_prompt=payload.get("adjustment_prompt", ""),
                    adjustment_reference_uri=payload.get("adjustment_reference_uri", ""),
                    adjustment_mode=payload.get("adjustment_mode", "custom"),
                )
                job.result = {"beat_id": shot.beat_id, "shot_id": shot.id, "status": shot.status}
            else:
                # Legacy jobs remain executable during the migration window.
                beat = Beat.objects.get(pk=payload["beat_id"])
                render_beat(beat)
                job.result = {"beat_id": beat.id, "status": beat.status}
        elif job.kind == Job.Kind.IMAGE:
            project = Project.objects.get(pk=job.project_id)
            refs = generate_refs(project)
            job.result = {"assets": len(refs)}
        elif job.kind == Job.Kind.ASSEMBLY:
            from apps.projects.assembly import assemble_episode
            from apps.story.models import Episode

            episode = Episode.objects.get(pk=payload["episode_id"])
            asset = assemble_episode(episode)
            job.result = {"episode_id": episode.id, "asset_id": asset.id, "uri": asset.uri}
        else:
            raise ValueError(f"unsupported job kind: {job.kind}")
        job.status = Job.Status.SUCCEEDED
        job.save(update_fields=["status", "result", "updated_at"])
        return job.result
    except Exception as exc:
        message = str(exc)
        quota_exhausted = "429" in message and (
            "RESOURCE_EXHAUSTED" in message or "Resource exhausted" in message
        )
        if quota_exhausted and self.request.retries < self.max_retries:
            # Keep the durable Job retryable instead of marking it failed while
            # Vertex is temporarily out of capacity. Celery will retry the same
            # resumable job; generate_refs skips assets already persisted.
            countdown = min(900, 60 * (2 ** self.request.retries))
            job.status = Job.Status.QUEUED
            job.error = (
                f"Vertex AI temporairement saturé; nouvelle tentative dans {countdown}s "
                f"({self.request.retries + 1}/{self.max_retries})."
            )
            job.save(update_fields=["status", "error", "updated_at"])
            raise self.retry(exc=exc, countdown=countdown)

        job.status = Job.Status.FAILED
        job.error = message
        job.save(update_fields=["status", "error", "updated_at"])
        raise
