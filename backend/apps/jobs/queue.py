from django.conf import settings

from apps.jobs.models import Job
from apps.projects.models import Project


def enqueue(*, project: Project, kind: str, agent_role: str, payload: dict) -> Job:
    job = Job.objects.create(
        project=project,
        kind=kind,
        status=Job.Status.QUEUED,
        agent_role=agent_role,
        payload=payload,
    )
    from apps.jobs.tasks import run_studio_job

    run_studio_job.delay(job.id)
    job.refresh_from_db()
    return job


def is_eager() -> bool:
    return bool(getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False))
