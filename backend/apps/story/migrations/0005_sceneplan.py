from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("story", "0004_beat_narrative_event"),
    ]

    operations = [
        migrations.CreateModel(
            name="ScenePlan",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("version", models.PositiveIntegerField(default=1)),
                ("payload", models.JSONField(default=list)),
                ("locked", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("episode", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="scene_plans", to="story.episode")),
                ("script", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="scene_plans", to="story.script")),
            ],
            options={"ordering": ["-version"], "unique_together": {("script", "version")}},
        ),
    ]
