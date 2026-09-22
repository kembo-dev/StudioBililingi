from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("projects", "0005_narrative_contract"),
    ]

    operations = [
        migrations.AddField(model_name="project", name="subgenre", field=models.CharField(blank=True, max_length=80)),
        migrations.AddField(model_name="project", name="setting", field=models.CharField(blank=True, help_text="Cadre géographique/culturel canonique du projet.", max_length=160)),
        migrations.AddField(model_name="project", name="episode_count_target", field=models.PositiveSmallIntegerField(blank=True, help_text="Nombre d'épisodes souhaité; vide = automatique.", null=True)),
        migrations.AddField(model_name="project", name="episode_duration_seconds", field=models.PositiveSmallIntegerField(default=60, help_text="Durée cible approximative par épisode.")),
    ]
