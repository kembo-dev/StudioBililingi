from django.apps import AppConfig


class ProjectsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.projects"
    label = "projects"

    def ready(self):
        from apps.projects import seeds, services

        services.seed_bible = seeds.seed_bible
        services.seed_season_plan = seeds.seed_season_plan
        services.seed_script = seeds.seed_script
