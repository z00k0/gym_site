from pathlib import Path

import pytest
from django.core.management import call_command
from django.urls import reverse

from accounts.models import User
from exercises.models import Exercise


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
