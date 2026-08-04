from django.conf import settings
from django.db import models


class Exercise(models.Model):
    class LoadKind(models.TextChoices):
        EXTERNAL = "external", "Внешнее отягощение"
        BODYWEIGHT = "bodyweight", "Собственный вес"

    source_id = models.CharField(max_length=32, unique=True, null=True, blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="custom_exercises",
    )
    name = models.CharField("название", max_length=255)
    instructions_ru = models.TextField("инструкция", blank=True)
    body_part = models.CharField("часть тела", max_length=100, blank=True, db_index=True)
    equipment = models.CharField("оборудование", max_length=100, blank=True, db_index=True)
    target = models.CharField("целевая мышца", max_length=100, blank=True)
    muscle_group = models.CharField("группа мышц", max_length=100, blank=True)
    secondary_muscles = models.JSONField(default=list, blank=True)
    load_kind = models.CharField(max_length=20, choices=LoadKind.choices, db_index=True)
    image_path = models.CharField(max_length=255, blank=True)
    gif_path = models.CharField(max_length=255, blank=True)
    attribution = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["name"])]

    @property
    def is_imported(self):
        return self.source_id is not None

    def display_name_for(self, user):
        alias = getattr(self, "current_alias", None)
        return alias.alias if alias else self.name

    def __str__(self):
        return self.name


class UserExerciseAlias(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="exercise_aliases"
    )
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE, related_name="aliases")
    alias = models.CharField("личное название", max_length=255)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "exercise"], name="unique_alias_per_user_exercise"
            )
        ]


class UserExerciseUsage(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="exercise_usage",
    )
    exercise = models.ForeignKey(
        Exercise,
        on_delete=models.CASCADE,
        related_name="user_usage",
    )
    last_selected_at = models.DateTimeField("последний выбор", db_index=True)

    class Meta:
        ordering = ["-last_selected_at", "-pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "exercise"], name="unique_usage_per_user_exercise"
            )
        ]
