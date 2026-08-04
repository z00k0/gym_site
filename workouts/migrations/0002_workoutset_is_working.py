from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("workouts", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="workoutset",
            name="is_working",
            field=models.BooleanField(default=False, verbose_name="рабочий подход"),
        ),
    ]
