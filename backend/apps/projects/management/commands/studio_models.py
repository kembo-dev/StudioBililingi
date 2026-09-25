from django.core.management.base import BaseCommand

from agents.backends.registry import _config, _selection


ROLE_MODALITIES = {
    "world_bible": "text",
    "showrunner": "text",
    "screenwriter": "text",
    "scene_planner": "text",
    "beat_segmenter": "text",
    "shot_planner": "text",
    "beat_rewriter": "text",
    "art_director": "image",
}


class Command(BaseCommand):
    help = "Affiche le provider et le modèle résolus pour chaque rôle StudioBililingi."

    def handle(self, *args, **options):
        cfg = _config()
        self.stdout.write("StudioBililingi model registry")
        self.stdout.write("=" * 72)
        for role, modality in ROLE_MODALITIES.items():
            choice = _selection(modality, role)
            provider = choice.get("provider") or "stub"
            model = choice.get("model") or "-"
            self.stdout.write(f"{role:20} {modality:7} -> {provider} / {model}")

        for modality in ("video", "audio"):
            choice = _selection(modality)
            provider = choice.get("provider") or "stub"
            model = choice.get("model") or "-"
            self.stdout.write(f"{modality:20} {modality:7} -> {provider} / {model}")

        path = __import__("agents.backends.registry", fromlist=["_CONFIG_PATH"])._CONFIG_PATH
        self.stdout.write("-" * 72)
        self.stdout.write(f"config: {path}")
        self.stdout.write(f"providers: {', '.join(sorted((cfg.get('providers') or {}).keys()))}")
