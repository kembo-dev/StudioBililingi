from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("projects", "0005_narrative_contract"),
        ("story", "0003_beat_speaker"),
    ]

    operations = [
        migrations.AddField(
            model_name="beat",
            name="narrative_event",
            field=models.ForeignKey(
                blank=True,
                help_text="Canonical narrative event advanced by this beat.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="beats",
                to="projects.narrativeevent",
            ),
        ),
    ]
