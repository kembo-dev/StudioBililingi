from django.db import migrations, models
import secrets


def fill_uids(apps, schema_editor):
    for name in ("Character", "Location", "Prop"):
        model = apps.get_model("bible", name)
        for row in model.objects.all().iterator():
            row.reference_uid = secrets.token_hex(8)
            row.save(update_fields=["reference_uid"])


class Migration(migrations.Migration):
    dependencies = [("bible", "0001_initial")]
    operations = [
        migrations.AddField(model_name="character", name="reference_uid", field=models.CharField(blank=True, max_length=32, null=True)),
        migrations.AddField(model_name="location", name="reference_uid", field=models.CharField(blank=True, max_length=32, null=True)),
        migrations.AddField(model_name="prop", name="reference_uid", field=models.CharField(blank=True, max_length=32, null=True)),
        migrations.RunPython(fill_uids, migrations.RunPython.noop),
        migrations.AlterField(model_name="character", name="reference_uid", field=models.CharField(editable=False, max_length=32, unique=True)),
        migrations.AlterField(model_name="location", name="reference_uid", field=models.CharField(editable=False, max_length=32, unique=True)),
        migrations.AlterField(model_name="prop", name="reference_uid", field=models.CharField(editable=False, max_length=32, unique=True)),
    ]
