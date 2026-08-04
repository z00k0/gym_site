import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.db.models import Max


def backfill_exercise_usage(apps, schema_editor):
    WorkoutExercise = apps.get_model("workouts", "WorkoutExercise")
    UserExerciseUsage = apps.get_model("exercises", "UserExerciseUsage")

    selections = (
        WorkoutExercise.objects.exclude(exercise_id=None)
        .values("workout__user_id", "exercise_id")
        .annotate(last_selected_at=Max("workout__started_at"))
    )
    UserExerciseUsage.objects.bulk_create(
        [
            UserExerciseUsage(
                user_id=item["workout__user_id"],
                exercise_id=item["exercise_id"],
                last_selected_at=item["last_selected_at"],
            )
            for item in selections
        ]
    )


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("exercises", "0001_initial"),
        ("workouts", "0002_workoutset_is_working"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserExerciseUsage",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "last_selected_at",
                    models.DateTimeField(db_index=True, verbose_name="последний выбор"),
                ),
                (
                    "exercise",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="user_usage",
                        to="exercises.exercise",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="exercise_usage",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-last_selected_at", "-pk"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("user", "exercise"),
                        name="unique_usage_per_user_exercise",
                    )
                ],
            },
        ),
        migrations.RunPython(backfill_exercise_usage, migrations.RunPython.noop),
    ]
