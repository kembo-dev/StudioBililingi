from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("projects", "0002_project_delivery"),
    ]

    operations = [
        migrations.AddField(
            model_name="project",
            name="visual_style",
            field=models.CharField(
                choices=[
                    ("realistic", "Réaliste cinématographique"),
                    ("realistic_imperfect", "Réaliste avec imperfections réelles"),
                    ("cartoon", "Cartoon"),
                    ("manga", "Manga / Anime"),
                    ("3d_animation", "Animation 3D"),
                    ("comic", "Bande dessinée / Comic"),
                    ("watercolor", "Aquarelle"),
                    ("claymation", "Claymation"),
                    ("pixel_art", "Pixel art"),
                    ("film_noir", "Film noir"),
                    ("fantasy", "Fantasy stylisée"),
                ],
                default="realistic",
                help_text="Direction visuelle canonique appliquée aux références et aux rendus.",
                max_length=32,
            ),
        ),
    ]
