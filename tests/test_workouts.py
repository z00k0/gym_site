from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from exercises.models import Exercise, UserExerciseAlias, UserExerciseUsage
from workouts.models import Workout, WorkoutExercise, WorkoutSet


@pytest.fixture
def athlete(db):
    return User.objects.create_user("athlete@example.com", "test-password-123")


@pytest.fixture
def barbell_exercise(db):
    return Exercise.objects.create(
        source_id="bench",
        name="Bench press",
        equipment="barbell",
        load_kind=Exercise.LoadKind.EXTERNAL,
    )


@pytest.mark.django_db
def test_external_load_cannot_be_negative(athlete, barbell_exercise):
    workout = Workout.objects.create(user=athlete, started_at=timezone.now())
    item = WorkoutExercise.objects.create(workout=workout, exercise=barbell_exercise)
    workout_set = WorkoutSet(workout_exercise=item, reps=8, load_kg=Decimal("-1"), completed=True)
    with pytest.raises(ValidationError):
        workout_set.full_clean()


@pytest.mark.django_db
def test_bodyweight_load_can_represent_assistance(athlete):
    exercise = Exercise.objects.create(
        source_id="pullup",
        name="Pull-up",
        equipment="body weight",
        load_kind=Exercise.LoadKind.BODYWEIGHT,
    )
    workout = Workout.objects.create(user=athlete, started_at=timezone.now())
    item = WorkoutExercise.objects.create(workout=workout, exercise=exercise)
    workout_set = WorkoutSet(workout_exercise=item, reps=6, load_kg=Decimal("-20"), completed=True)
    workout_set.full_clean()


@pytest.mark.django_db
def test_complete_and_clone_workout(client, athlete, barbell_exercise):
    client.force_login(athlete)
    workout = Workout.objects.create(user=athlete, title="Грудь", started_at=timezone.now())
    item = WorkoutExercise.objects.create(workout=workout, exercise=barbell_exercise, position=1)
    workout_set = WorkoutSet.objects.create(workout_exercise=item, position=1, reps=8, load_kg="80")
    assert client.get(reverse("workout_detail", args=[workout.pk])).status_code == 200

    response = client.post(
        reverse("workout_save_set", args=[workout.pk, workout_set.pk]),
        {
            "reps": 8,
            "load_kg": "82.5",
            "is_working": "on",
            "completed": "on",
        },
    )
    assert response.status_code == 302
    workout_set.refresh_from_db()
    assert workout_set.completed and workout_set.is_working
    assert workout_set.load_kg == Decimal("82.50")

    finish_response = client.post(reverse("workout_finish", args=[workout.pk]))
    assert finish_response.status_code == 302
    assert finish_response.url == reverse("workout_list")
    workout.refresh_from_db()
    assert workout.status == Workout.Status.COMPLETED
    progress_response = client.get(reverse("exercise_detail", args=[barbell_exercise.pk]))
    assert progress_response.status_code == 200
    assert "660" in progress_response.content.decode()

    response = client.post(reverse("workout_clone", args=[workout.pk]))
    clone = Workout.objects.exclude(pk=workout.pk).get(user=athlete)
    assert response.status_code == 302
    assert clone.status == Workout.Status.DRAFT
    cloned_set = clone.items.get().sets.get()
    assert cloned_set.reps == 8 and cloned_set.load_kg == Decimal("82.50")
    assert cloned_set.is_working
    assert not cloned_set.completed


@pytest.mark.django_db
def test_workout_metrics_include_warmup_tonnage_and_only_working_reps(
    client, athlete, barbell_exercise
):
    client.force_login(athlete)
    workout = Workout.objects.create(
        user=athlete, title="Грудь", started_at=timezone.now()
    )
    item = WorkoutExercise.objects.create(
        workout=workout, exercise=barbell_exercise, position=1
    )
    WorkoutSet.objects.create(
        workout_exercise=item,
        position=1,
        reps=10,
        load_kg="20",
        completed=True,
    )
    WorkoutSet.objects.create(
        workout_exercise=item,
        position=2,
        reps=8,
        load_kg="80",
        is_working=True,
        completed=True,
    )
    WorkoutSet.objects.create(
        workout_exercise=item,
        position=3,
        reps=5,
        load_kg="90",
        is_working=True,
        completed=False,
    )

    detail = client.get(reverse("workout_detail", args=[workout.pk]))
    content = detail.content.decode()
    assert "Рабочих повторов: 8" in content
    assert "тоннаж: 840 кг" in content

    workout_list = client.get(reverse("workout_list"))
    list_content = workout_list.content.decode()
    assert " - Грудь" in list_content
    assert "Volume: 840, Sets: 2, Reps: 18" in list_content


@pytest.mark.django_db
def test_workout_list_is_ordered_by_start_time_descending(client, athlete):
    client.force_login(athlete)
    older = Workout.objects.create(
        user=athlete,
        title="Старая тренировка",
        started_at=timezone.now() - timedelta(days=1),
    )
    newer = Workout.objects.create(
        user=athlete,
        title="Последняя тренировка",
        started_at=timezone.now(),
    )

    content = client.get(reverse("workout_list")).content.decode()
    assert content.index(newer.title) < content.index(older.title)


@pytest.mark.django_db
def test_workout_shows_exercise_numbers_and_previous_set_values(
    client, athlete, barbell_exercise
):
    client.force_login(athlete)
    previous = Workout.objects.create(
        user=athlete,
        started_at=timezone.now() - timedelta(days=7),
        status=Workout.Status.COMPLETED,
    )
    previous_item = WorkoutExercise.objects.create(
        workout=previous, exercise=barbell_exercise, position=1
    )
    WorkoutSet.objects.create(
        workout_exercise=previous_item,
        position=1,
        reps=8,
        load_kg="82.5",
        completed=True,
    )

    current = Workout.objects.create(user=athlete, started_at=timezone.now())
    current_item = WorkoutExercise.objects.create(
        workout=current, exercise=barbell_exercise, position=2
    )
    current_set = WorkoutSet.objects.create(
        workout_exercise=current_item, position=1, reps=6, load_kg="80"
    )

    response = client.get(reverse("workout_detail", args=[current.pk]))
    content = response.content.decode()
    assert 'aria-label="Упражнение номер 1"' in content
    assert "Было: 8" in content
    assert "Было: 82,5" in content

    response = client.post(
        reverse("workout_save_set", args=[current.pk, current_set.pk]),
        {"reps": 7, "load_kg": "81", "completed": "on"},
        HTTP_HX_REQUEST="true",
    )
    assert response.status_code == 200
    assert "Было: 8" in response.content.decode()


@pytest.mark.django_db
def test_workout_exercises_render_in_position_order(
    client, athlete, barbell_exercise
):
    client.force_login(athlete)
    second_exercise = Exercise.objects.create(
        source_id="squat",
        name="Squat",
        equipment="barbell",
        load_kind=Exercise.LoadKind.EXTERNAL,
    )
    workout = Workout.objects.create(user=athlete, started_at=timezone.now())
    WorkoutExercise.objects.create(
        workout=workout, exercise=barbell_exercise, position=20
    )
    WorkoutExercise.objects.create(
        workout=workout, exercise=second_exercise, position=10
    )

    content = client.get(reverse("workout_detail", args=[workout.pk])).content.decode()
    assert content.index("Squat") < content.index("Bench press")
    assert content.index('Упражнение номер 1') < content.index('Упражнение номер 2')


@pytest.mark.django_db
def test_delete_set_renumbers_remaining_sets(client, athlete, barbell_exercise):
    client.force_login(athlete)
    workout = Workout.objects.create(user=athlete, started_at=timezone.now())
    item = WorkoutExercise.objects.create(
        workout=workout, exercise=barbell_exercise, position=1
    )
    first = WorkoutSet.objects.create(workout_exercise=item, position=1)
    second = WorkoutSet.objects.create(workout_exercise=item, position=2)
    third = WorkoutSet.objects.create(workout_exercise=item, position=4)

    response = client.post(reverse("workout_delete_set", args=[workout.pk, first.pk]))

    assert response.status_code == 302
    assert list(item.sets.values_list("pk", "position")) == [
        (second.pk, 1),
        (third.pk, 2),
    ]

    htmx_response = client.post(
        reverse("workout_delete_set", args=[workout.pk, second.pk]),
        HTTP_HX_REQUEST="true",
    )
    assert htmx_response.status_code == 204
    assert htmx_response.headers["HX-Redirect"] == reverse(
        "workout_detail", args=[workout.pk]
    )


@pytest.mark.django_db
def test_move_set_changes_order_and_previous_values(client, athlete, barbell_exercise):
    client.force_login(athlete)
    previous = Workout.objects.create(
        user=athlete,
        started_at=timezone.now() - timedelta(days=7),
        status=Workout.Status.COMPLETED,
    )
    previous_item = WorkoutExercise.objects.create(
        workout=previous, exercise=barbell_exercise, position=1
    )
    WorkoutSet.objects.create(
        workout_exercise=previous_item,
        position=1,
        reps=12,
        load_kg="50",
        completed=True,
    )

    workout = Workout.objects.create(user=athlete, started_at=timezone.now())
    item = WorkoutExercise.objects.create(
        workout=workout, exercise=barbell_exercise, position=1
    )
    first = WorkoutSet.objects.create(workout_exercise=item, position=1, reps=8)
    second = WorkoutSet.objects.create(workout_exercise=item, position=2, reps=6)

    response = client.post(
        reverse("workout_move_set", args=[workout.pk, second.pk, "up"])
    )

    assert response.status_code == 302
    first.refresh_from_db()
    second.refresh_from_db()
    assert (second.position, first.position) == (1, 2)
    content = client.get(reverse("workout_detail", args=[workout.pk])).content.decode()
    second_row = content[content.index(f'id="set-{second.pk}"') :]
    assert "Было: 12" in second_row.split("</form>", 1)[0]


@pytest.mark.django_db
def test_working_set_defaults_to_false(athlete, barbell_exercise):
    workout = Workout.objects.create(user=athlete, started_at=timezone.now())
    item = WorkoutExercise.objects.create(workout=workout, exercise=barbell_exercise)
    workout_set = WorkoutSet.objects.create(workout_exercise=item)
    assert not workout_set.is_working


@pytest.mark.django_db
def test_add_empty_exercise_then_select_exercise(client, athlete, barbell_exercise):
    client.force_login(athlete)
    workout = Workout.objects.create(user=athlete, started_at=timezone.now())

    response = client.post(reverse("workout_add_empty_exercise", args=[workout.pk]))
    assert response.status_code == 302
    item = workout.items.get()
    assert item.exercise is None
    assert not item.sets.exists()

    detail = client.get(reverse("workout_detail", args=[workout.pk]))
    assert "Выберите упражнение" in detail.content.decode()

    response = client.post(
        reverse(
            "workout_select_exercise",
            args=[workout.pk, item.pk, barbell_exercise.pk],
        )
    )
    assert response.status_code == 302
    item.refresh_from_db()
    assert item.exercise == barbell_exercise
    assert item.sets.count() == 1
    assert item.sets.get().load_kg == Decimal("0")
    assert UserExerciseUsage.objects.filter(
        user=athlete, exercise=barbell_exercise
    ).exists()


@pytest.mark.django_db
def test_recent_exercises_are_ordered_limited_and_searchable(client, athlete):
    client.force_login(athlete)
    workout = Workout.objects.create(user=athlete, started_at=timezone.now())
    empty_item = WorkoutExercise.objects.create(workout=workout, position=2)
    now = timezone.now()
    exercises = []
    for index in range(12):
        exercise = Exercise.objects.create(
            source_id=f"recent-{index}",
            name=f"Exercise {index:02d}",
            equipment="barbell",
            load_kind=Exercise.LoadKind.EXTERNAL,
        )
        UserExerciseUsage.objects.create(
            user=athlete,
            exercise=exercise,
            last_selected_at=now - timedelta(minutes=index),
        )
        exercises.append(exercise)

    WorkoutExercise.objects.create(
        workout=workout, exercise=exercises[0], position=1
    )
    UserExerciseAlias.objects.create(
        user=athlete, exercise=exercises[11], alias="Особое упражнение"
    )

    response = client.get(
        reverse("workout_exercise_options", args=[workout.pk, empty_item.pk])
    )
    content = response.content.decode()
    assert "Exercise 00" not in content
    assert "Exercise 01" in content
    assert "Exercise 10" in content
    assert "Особое упражнение" not in content
    assert content.index("Exercise 01") < content.index("Exercise 02")

    response = client.get(
        reverse("workout_exercise_options", args=[workout.pk, empty_item.pk]),
        {"q": "Особое"},
    )
    assert "Особое упражнение" in response.content.decode()


@pytest.mark.django_db
def test_empty_exercise_is_ignored_and_cloned(client, athlete, barbell_exercise):
    client.force_login(athlete)
    workout = Workout.objects.create(
        user=athlete, title="С пустой карточкой", started_at=timezone.now()
    )
    filled_item = WorkoutExercise.objects.create(
        workout=workout, exercise=barbell_exercise, position=1
    )
    WorkoutSet.objects.create(
        workout_exercise=filled_item,
        reps=5,
        load_kg=100,
        completed=True,
    )
    WorkoutExercise.objects.create(workout=workout, position=2)

    detail = client.get(reverse("workout_detail", args=[workout.pk]))
    assert "тоннаж: 500 кг" in detail.content.decode()

    client.post(reverse("workout_finish", args=[workout.pk]))
    workout.refresh_from_db()
    assert workout.status == Workout.Status.COMPLETED

    client.post(reverse("workout_clone", args=[workout.pk]))
    clone = Workout.objects.exclude(pk=workout.pk).get(user=athlete)
    empty_clone = clone.items.get(exercise__isnull=True)
    assert not empty_clone.sets.exists()


@pytest.mark.django_db
def test_cannot_select_duplicate_or_another_users_empty_item(
    client, athlete, barbell_exercise
):
    client.force_login(athlete)
    workout = Workout.objects.create(user=athlete, started_at=timezone.now())
    WorkoutExercise.objects.create(
        workout=workout, exercise=barbell_exercise, position=1
    )
    empty_item = WorkoutExercise.objects.create(workout=workout, position=2)

    response = client.post(
        reverse(
            "workout_select_exercise",
            args=[workout.pk, empty_item.pk, barbell_exercise.pk],
        )
    )
    assert response.status_code == 302
    empty_item.refresh_from_db()
    assert empty_item.exercise is None

    other = User.objects.create_user("empty-owner@example.com", "test-password-123")
    other_workout = Workout.objects.create(user=other, started_at=timezone.now())
    other_item = WorkoutExercise.objects.create(workout=other_workout)
    response = client.post(
        reverse(
            "workout_select_exercise",
            args=[other_workout.pk, other_item.pk, barbell_exercise.pk],
        )
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_user_cannot_open_another_users_workout(client, athlete):
    other = User.objects.create_user("other@example.com", "test-password-123")
    workout = Workout.objects.create(user=other, started_at=timezone.now())
    client.force_login(athlete)
    assert client.get(reverse("workout_detail", args=[workout.pk])).status_code == 404
