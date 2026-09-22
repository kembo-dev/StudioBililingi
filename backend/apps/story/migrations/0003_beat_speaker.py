import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("bible", "0001_initial"),
        ("story", "0002_alter_beat_options_alter_beat_unique_together_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="beat",
            name="speaker",
            field=models.ForeignKey(
                blank=True,
                help_text="Canonical character speaking in this beat.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="spoken_beats",
                to="bible.character",
            ),
        ),
    ]
