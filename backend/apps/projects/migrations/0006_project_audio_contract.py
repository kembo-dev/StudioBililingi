from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("projects", "0007_project_auto_episode_duration"),
    ]

    operations = [
        migrations.AddField(
            model_name="project",
            name="audio_contract",
            field=models.JSONField(blank=True, default=dict, help_text="Contrat canonique de langue, narration et identité vocale du projet."),
        ),
    ]
