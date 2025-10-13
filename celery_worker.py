# app/celery_worker.py
import os
from celery import Celery

# Create a Celery instance
celery_app = Celery(
    "tasks",
    broker=os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
    backend=os.environ.get("REDIS_URL", "redis://localhost:6379/0")
)

celery_app.conf.update(
    task_track_started=True,
)

# Tell Celery to look for tasks in the 'tasks.py' file
celery_app.autodiscover_tasks(['app.tasks'])