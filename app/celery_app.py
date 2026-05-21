from celery import Celery

from app.config import settings

celery_app = Celery(
    "gatekeepify",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    beat_schedule_filename="/tmp/celerybeat-schedule",
    beat_max_loop_interval=60,
    beat_schedule={
        "poll-recent-listens": {
            "task": "app.tasks.poll_recent_listens",
            "schedule": settings.poll_interval_seconds,
        },
        "backfill-track-metadata": {
            "task": "app.tasks.backfill_track_metadata",
            "schedule": settings.backfill_interval_seconds,
        },
        "compute-award-snapshots": {
            "task": "app.tasks.compute_award_snapshots",
            "schedule": 21600,
        },
        "cleanup-old-records": {
            "task": "app.tasks.cleanup_old_records",
            "schedule": 86400,
        },
    },
)
