from decimal import Decimal
from pathlib import Path

import pytest
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from exercises.models import Exercise
from workouts.models import Workout


@pytest.mark.django_db
def test_dataset_import_is_idempotent():
    fixture_root = Path(__file__).parent / "fixtures" / "dataset"
    call_command("import_exercises", path=fixture_root)
    call_command("import_exercises", path=fixture_root)

    assert Exercise.objects.count() == 1
    exercise = Exercise.objects.get()
    assert exercise.load_kind == Exercise.LoadKind.BODYWEIGHT
    assert exercise.instructions_ru == "Подтянитесь."


@pytest.mark.django_db
def test_catalog_renders_imported_media_and_alias(client):
    user = User.objects.create_user("catalog@example.com", "test-password-123")
    exercise = Exercise.objects.create(
        source_id="media",
        name="Pull-up",
        equipment="body weight",
        load_kind=Exercise.LoadKind.BODYWEIGHT,
        image_path="images/pull-up.jpg",
    )
    exercise.aliases.create(user=user, alias="Подтягивания")
    client.force_login(user)
    response = client.get(reverse("exercise_catalog"), {"q": "Подтягивания"})
    assert response.status_code == 200
    assert "Подтягивания" in response.content.decode()
    assert "dataset/images/pull-up.jpg" in response.content.decode()


@pytest.mark.django_db
def test_detail_shows_most_reps_at_best_weight(client):
    user = User.objects.create_user("progress@example.com", "test-password-123")
    exercise = Exercise.objects.create(name="Bench press", load_kind=Exercise.LoadKind.EXTERNAL)
    workout = user.workouts.create(started_at=timezone.now(), status=Workout.Status.COMPLETED)
    item = workout.items.create(exercise=exercise)
    for weight, reps, completed in [(60, 12, True), (80, 4, True), (80, 6, True), (90, 8, False)]:
        item.sets.create(load_kg=weight, reps=reps, completed=completed)
    client.force_login(user)

    response = client.get(reverse("exercise_detail", args=[exercise.pk]))

    assert response.status_code == 200
    assert response.context["progress"] == {
        "best_load": Decimal("80"),
        "best_reps": 6,
        "volume": Decimal("1520"),
    }
