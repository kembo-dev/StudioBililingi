from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("story", "0006_segmentation"),
    ]

    operations = [
        migrations.AlterField(
            model_name="beat",
            name="text",
            field=models.TextField(help_text="Narrative beat; length follows story meaning, not video clip limits."),
        ),
        migrations.CreateModel(
            name="Shot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("index", models.PositiveSmallIntegerField()),
                ("text", models.TextField()),
                ("duration_seconds", models.DecimalField(decimal_places=1, default=6, max_digits=4)),
                ("video_prompt", models.TextField(blank=True)),
                ("negative_prompt", models.TextField(blank=True)),
                ("camera", models.JSONField(default=dict)),
                ("continuity", models.JSONField(default=dict)),
                ("status", models.CharField(choices=[("draft", "Draft"), ("approved_text", "Approved Text"), ("ready_to_render", "Ready To Render"), ("rendering", "Rendering"), ("review", "Review"), ("rejected", "Rejected"), ("locked", "Locked")], default="draft", max_length=24)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("beat", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="shots", to="story.beat")),
            ],
            options={"ordering": ["index"], "unique_together": {("beat", "index")}},
        ),
        migrations.CreateModel(
            name="ShotTake",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("number", models.PositiveIntegerField()),
                ("prompt", models.TextField(blank=True)),
                ("negative_prompt", models.TextField(blank=True)),
                ("backend", models.CharField(blank=True, max_length=64)),
                ("uri", models.CharField(blank=True, max_length=1024)),
                ("status", models.CharField(choices=[("queued", "Queued"), ("rendering", "Rendering"), ("review", "Review"), ("rejected", "Rejected"), ("locked", "Locked"), ("failed", "Failed")], default="queued", max_length=24)),
                ("generation_meta", models.JSONField(default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("shot", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="takes", to="story.shot")),
            ],
            options={"ordering": ["number"], "unique_together": {("shot", "number")}},
        ),
    ]
