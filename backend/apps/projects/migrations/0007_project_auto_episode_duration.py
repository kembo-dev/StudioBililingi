from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("projects", "0006_project_story_format"),
    ]

    operations = [
        migrations.AlterField(
            model_name="project",
            name="episode_duration_seconds",
            field=models.PositiveSmallIntegerField(
                blank=True,
                default=None,
                help_text="Durée cible par épisode en secondes; vide = durée naturelle automatique par épisode.",
                null=True,
            ),
        ),
    ]
