import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("workouts", "0002_workoutset_is_working"),
    ]

    operations = [
        migrations.AlterField(
            model_name="workoutexercise",
            name="exercise",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="workout_items",
                to="exercises.exercise",
            ),
        ),
    ]
