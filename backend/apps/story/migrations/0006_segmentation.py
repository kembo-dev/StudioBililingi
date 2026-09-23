from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("story", "0005_sceneplan"),
    ]

    operations = [
        migrations.CreateModel(
            name="Segmentation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("version", models.PositiveIntegerField(default=1)),
                ("payload", models.JSONField(default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("episode", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="segmentations", to="story.episode")),
                ("scene_plan", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="segmentations", to="story.sceneplan")),
                ("script", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="segmentations", to="story.script")),
            ],
            options={"ordering": ["-version"], "unique_together": {("script", "version")}},
        ),
        migrations.AddField(
            model_name="scene",
            name="segmentation",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="scenes", to="story.segmentation"),
        ),
        migrations.AddField(
            model_name="beat",
            name="segmentation",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="beats", to="story.segmentation"),
        ),
        migrations.AlterUniqueTogether(name="scene", unique_together={("segmentation", "index")}),
        migrations.AlterUniqueTogether(name="beat", unique_together={("segmentation", "index")}),
    ]
