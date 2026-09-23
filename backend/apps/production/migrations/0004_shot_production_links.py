from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("story", "0007_shot_shottake"),
        ("production", "0002_asset_beat_take_review_beat_take_alter_asset_role"),
    ]

    operations = [
        migrations.AddField(model_name="asset", name="shot", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="assets", to="story.shot")),
        migrations.AddField(model_name="asset", name="shot_take", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="assets", to="story.shottake")),
        migrations.AddField(model_name="review", name="shot", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="reviews", to="story.shot")),
        migrations.AddField(model_name="review", name="shot_take", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="reviews", to="story.shottake")),
    ]
