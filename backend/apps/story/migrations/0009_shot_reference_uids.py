from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("story", "0008_segmentation_scene_plan_cascade"),
    ]

    operations = [
        migrations.AddField(
            model_name="shot",
            name="reference_uids",
            field=models.JSONField(
                default=list,
                help_text="Ordered canonical media UIDs required by this shot.",
            ),
        ),
    ]
