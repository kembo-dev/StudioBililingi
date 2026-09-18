import os
import sys
from pathlib import Path

from celery import Celery
from dotenv import load_dotenv

# The reusable AI agents live at the repository root (../agents), while
# Celery is normally launched from backend/. Make that package importable
# for both local workers and container workers.
REPO_DIR = Path(__file__).resolve().parents[2]
if str(REPO_DIR) not in sys.path:
    sys.path.insert(0, str(REPO_DIR))

load_dotenv(REPO_DIR / ".env")
load_dotenv(REPO_DIR / "backend" / ".env")

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("studiobililingi")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
