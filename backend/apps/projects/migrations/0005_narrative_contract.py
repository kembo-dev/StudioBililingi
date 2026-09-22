from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("projects", "0004_project_visual_style"),
    ]

    operations = [
        migrations.CreateModel(
            name="NarrativeContract",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("point_of_view", models.CharField(choices=[("third_person", "Troisième personne"), ("first_person", "Première personne"), ("dialogue", "Dialogue / sans narrateur")], default="third_person", max_length=24)),
                ("narrator", models.CharField(default="external", max_length=80)),
                ("tense", models.CharField(default="present", max_length=24)),
                ("story_type", models.CharField(blank=True, max_length=40)),
                ("recommended_episode_count", models.PositiveSmallIntegerField(default=1)),
                ("rules", models.JSONField(blank=True, default=dict)),
                ("locked", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("project", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="narrative_contract", to="projects.project")),
            ],
        ),
        migrations.CreateModel(
            name="NarrativeEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("key", models.CharField(max_length=32)),
                ("position", models.PositiveSmallIntegerField()),
                ("description", models.TextField()),
                ("episode_number", models.PositiveSmallIntegerField(default=1)),
                ("status", models.CharField(choices=[("planned", "Planifié"), ("scripted", "Scénarisé"), ("consumed", "Consommé")], default="planned", max_length=16)),
                ("contract", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="events", to="projects.narrativecontract")),
            ],
            options={"ordering": ["position"], "unique_together": {("contract", "key"), ("contract", "position")}},
        ),
    ]
