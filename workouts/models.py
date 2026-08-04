from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from exercises.models import Exercise


class Workout(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Черновик"
        COMPLETED = "completed", "Завершена"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="workouts"
    )
    title = models.CharField("название", max_length=200, blank=True)
    started_at = models.DateTimeField("начало")
    completed_at = models.DateTimeField("завершение", null=True, blank=True)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.DRAFT, db_index=True
    )
    note = models.TextField("заметка", blank=True)

    class Meta:
        ordering = ["-started_at", "-pk"]

    def __str__(self):
        return self.title or f"Тренировка {self.started_at:%d.%m.%Y}"


class WorkoutExercise(models.Model):
    workout = models.ForeignKey(Workout, on_delete=models.CASCADE, related_name="items")
    exercise = models.ForeignKey(
        Exercise,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="workout_items",
    )
    position = models.PositiveIntegerField(default=0)
    note = models.CharField("заметка", max_length=300, blank=True)

    class Meta:
        ordering = ["position", "pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["workout", "exercise"], name="one_exercise_once_per_workout"
            )
        ]


class WorkoutSet(models.Model):
    workout_exercise = models.ForeignKey(
        WorkoutExercise, on_delete=models.CASCADE, related_name="sets"
    )
    position = models.PositiveIntegerField(default=0)
    reps = models.PositiveIntegerField(
        "повторения", null=True, blank=True, validators=[MinValueValidator(1)]
    )
    load_kg = models.DecimalField(
        "нагрузка, кг", max_digits=7, decimal_places=2, null=True, blank=True
    )
    is_working = models.BooleanField("рабочий подход", default=False)
    completed = models.BooleanField("выполнен", default=False)

    class Meta:
        ordering = ["position", "pk"]

    def clean(self):
        errors = {}
        if self.completed and self.reps is None:
            errors["reps"] = "У выполненного подхода укажите повторения."
        if self.completed and self.load_kg is None:
            errors["load_kg"] = "У выполненного подхода укажите нагрузку."
        if (
            self.load_kg is not None
            and self.workout_exercise.exercise is not None
            and self.workout_exercise.exercise.load_kind == Exercise.LoadKind.EXTERNAL
            and self.load_kg < Decimal("0")
        ):
            errors["load_kg"] = "Внешняя нагрузка не может быть отрицательной."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.reps or '—'} × {self.load_kg if self.load_kg is not None else '—'} кг"
