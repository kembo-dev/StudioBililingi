from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("projects", "0001_initial")]
    operations = [
        migrations.AddField(
            model_name="project",
            name="delivery",
            field=models.CharField(default="storytell", help_text="storytell | voix_off | conversation | rencontre", max_length=24),
        ),
    ]
