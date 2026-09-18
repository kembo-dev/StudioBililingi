from celery import shared_task


@shared_task
def run_studio_job(job_id: int) -> dict:
    from apps.jobs.models import Job
    from apps.projects.continuity import render_beat
    from apps.projects.models import Project
    from apps.projects.visuals import generate_refs
    from apps.story.models import Beat

    job = Job.objects.get(pk=job_id)
    job.status = Job.Status.RUNNING
    job.save(update_fields=["status", "updated_at"])
    try:
        payload = job.payload or {}
        if job.kind == Job.Kind.VIDEO:
            beat = Beat.objects.get(pk=payload["beat_id"])
            render_beat(beat)
            job.result = {"beat_id": beat.id, "status": beat.status}
        elif job.kind == Job.Kind.IMAGE:
            project = Project.objects.get(pk=job.project_id)
            refs = generate_refs(project)
            job.result = {"assets": len(refs)}
        else:
            raise ValueError(f"unsupported job kind: {job.kind}")
        job.status = Job.Status.SUCCEEDED
        job.save(update_fields=["status", "result", "updated_at"])
        return job.result
    except Exception as exc:
        job.status = Job.Status.FAILED
        job.error = str(exc)
        job.save(update_fields=["status", "error", "updated_at"])
        raise
