from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("story", "0007_shot_shottake"),
    ]

    operations = [
        migrations.AlterField(
            model_name="segmentation",
            name="scene_plan",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="segmentations",
                to="story.sceneplan",
            ),
        ),
    ]
