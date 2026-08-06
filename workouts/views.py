from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import (
    Count,
    DecimalField,
    ExpressionWrapper,
    F,
    Max,
    OuterRef,
    Prefetch,
    Q,
    Subquery,
    Sum,
    Value,
)
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from exercises.models import UserExerciseAlias, UserExerciseUsage
from exercises.views import visible_exercises

from .forms import WorkoutForm, WorkoutSetForm
from .models import Workout, WorkoutExercise, WorkoutSet


def _item_metrics_queryset():
    volume = ExpressionWrapper(
        F("sets__reps") * F("sets__load_kg"),
        output_field=DecimalField(max_digits=16, decimal_places=2),
    )
    return (
        WorkoutExercise.objects.select_related("exercise")
        .annotate(
            working_reps=Coalesce(
                Sum(
                    "sets__reps",
                    filter=Q(sets__completed=True, sets__is_working=True),
                ),
                Value(0),
            ),
            tonnage=Coalesce(
                Sum(volume, filter=Q(sets__completed=True)),
                Value(Decimal("0")),
                output_field=DecimalField(max_digits=16, decimal_places=2),
            ),
        )
        .prefetch_related(
            Prefetch("sets", queryset=_sets_with_previous_values())
        )
        .order_by("position", "pk")
    )


def _sets_with_previous_values():
    previous_sets = (
        WorkoutSet.objects.filter(
            workout_exercise__workout__user=OuterRef(
                "workout_exercise__workout__user"
            ),
            workout_exercise__exercise=OuterRef("workout_exercise__exercise"),
            workout_exercise__workout__status=Workout.Status.COMPLETED,
            position=OuterRef("position"),
            completed=True,
        )
        .filter(
            Q(
                workout_exercise__workout__started_at__lt=OuterRef(
                    "workout_exercise__workout__started_at"
                )
            )
            | Q(
                workout_exercise__workout__started_at=OuterRef(
                    "workout_exercise__workout__started_at"
                ),
                workout_exercise__workout__pk__lt=OuterRef(
                    "workout_exercise__workout__pk"
                ),
            )
        )
        .order_by("-workout_exercise__workout__started_at", "-pk")
    )
    return WorkoutSet.objects.annotate(
        previous_reps=Subquery(previous_sets.values("reps")[:1]),
        previous_load_kg=Subquery(previous_sets.values("load_kg")[:1]),
    ).order_by("position", "pk")


def _set_with_previous_values(pk):
    return _sets_with_previous_values().get(pk=pk)


def _user_workout(request, pk):
    return get_object_or_404(
        Workout.objects.prefetch_related(
            Prefetch("items", queryset=_item_metrics_queryset())
        ),
        pk=pk,
        user=request.user,
    )


def _available_exercises(user, workout):
    return visible_exercises(user).exclude(workout_items__workout=workout)


def _exercise_options(user, workout, query=""):
    last_selected_at = UserExerciseUsage.objects.filter(
        user=user,
        exercise=OuterRef("pk"),
    ).values("last_selected_at")[:1]
    exercises = _available_exercises(user, workout).annotate(
        last_selected_at=Subquery(last_selected_at)
    )
    if query:
        exercises = (
            exercises.filter(
                Q(name__icontains=query)
                | Q(aliases__user=user, aliases__alias__icontains=query)
            )
            .distinct()
            .order_by("name", "pk")[:60]
        )
    else:
        exercises = exercises.filter(last_selected_at__isnull=False).order_by(
            "-last_selected_at", "name", "pk"
        )[:10]
    exercises = list(exercises)
    alias_map = dict(
        UserExerciseAlias.objects.filter(
            user=user, exercise_id__in=[exercise.pk for exercise in exercises]
        ).values_list("exercise_id", "alias")
    )
    return exercises, alias_map


def _record_exercise_selection(user, exercise):
    UserExerciseUsage.objects.update_or_create(
        user=user,
        exercise=exercise,
        defaults={"last_selected_at": timezone.now()},
    )


def _selection_redirect(request, workout):
    url = reverse("workout_detail", args=[workout.pk])
    if request.headers.get("HX-Request"):
        response = HttpResponse(status=204)
        response["HX-Redirect"] = url
        return response
    return redirect(url)


@login_required
def workout_list(request):
    volume = ExpressionWrapper(
        F("items__sets__reps") * F("items__sets__load_kg"),
        output_field=DecimalField(max_digits=16, decimal_places=2),
    )
    workouts = request.user.workouts.annotate(
        tonnage=Coalesce(
            Sum(volume, filter=Q(items__sets__completed=True)),
            Value(Decimal("0")),
            output_field=DecimalField(max_digits=16, decimal_places=2),
        ),
        completed_sets=Count(
            "items__sets", filter=Q(items__sets__completed=True)
        ),
        completed_reps=Coalesce(
            Sum("items__sets__reps", filter=Q(items__sets__completed=True)),
            Value(0),
        ),
    ).order_by("-started_at", "-pk")
    return render(request, "workouts/list.html", {"workouts": workouts})


@login_required
def create(request):
    form = WorkoutForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        workout = form.save(commit=False)
        workout.user = request.user
        if not workout.title:
            workout.title = f"Тренировка {timezone.localtime(workout.started_at):%d.%m.%Y}"
        workout.save()
        return redirect("workout_detail", pk=workout.pk)
    return render(request, "form_page.html", {"form": form, "title": "Новая тренировка"})


@login_required
def detail(request, pk):
    workout = _user_workout(request, pk)
    recent_exercises, recent_alias_map = [], {}
    if any(item.exercise_id is None for item in workout.items.all()):
        recent_exercises, recent_alias_map = _exercise_options(
            request.user, workout
        )
    return render(
        request,
        "workouts/detail.html",
        {
            "workout": workout,
            "workout_form": WorkoutForm(instance=workout),
            "recent_exercises": recent_exercises,
            "recent_alias_map": recent_alias_map,
        },
    )


@login_required
def edit(request, pk):
    workout = _user_workout(request, pk)
    if request.method == "POST":
        form = WorkoutForm(request.POST, instance=workout)
        if form.is_valid():
            form.save()
        else:
            return render(
                request, "workouts/detail.html", {"workout": workout, "workout_form": form}
            )
    return redirect("workout_detail", pk=pk)


@login_required
def exercise_picker(request, pk):
    workout = _user_workout(request, pk)
    query = request.GET.get("q", "").strip()
    exercises = visible_exercises(request.user).exclude(workout_items__workout=workout)
    if query:
        exercises = exercises.filter(
            Q(name__icontains=query)
            | Q(aliases__user=request.user, aliases__alias__icontains=query)
        ).distinct()
    alias_map = dict(
        UserExerciseAlias.objects.filter(user=request.user).values_list("exercise_id", "alias")
    )
    return render(
        request,
        "workouts/exercise_picker.html",
        {
            "workout": workout,
            "exercises": exercises[:60],
            "query": query,
            "alias_map": alias_map,
        },
    )


@login_required
@require_POST
def add_empty_exercise(request, pk):
    workout = _user_workout(request, pk)
    position = (workout.items.aggregate(value=Max("position"))["value"] or 0) + 1
    WorkoutExercise.objects.create(workout=workout, position=position)
    return redirect("workout_detail", pk=pk)


@login_required
@require_GET
def exercise_options(request, pk, item_pk):
    workout = _user_workout(request, pk)
    get_object_or_404(workout.items, pk=item_pk, exercise__isnull=True)
    query = request.GET.get("q", "").strip()
    exercises, alias_map = _exercise_options(request.user, workout, query)
    return render(
        request,
        "workouts/_exercise_options.html",
        {
            "workout": workout,
            "item_pk": item_pk,
            "exercises": exercises,
            "alias_map": alias_map,
            "query": query,
        },
    )


@login_required
@require_POST
@transaction.atomic
def select_exercise(request, pk, item_pk, exercise_pk):
    workout = get_object_or_404(Workout, pk=pk, user=request.user)
    item = get_object_or_404(
        WorkoutExercise.objects.select_for_update(),
        pk=item_pk,
        workout=workout,
        exercise__isnull=True,
    )
    exercise = get_object_or_404(visible_exercises(request.user), pk=exercise_pk)
    if WorkoutExercise.objects.filter(workout=workout, exercise=exercise).exists():
        messages.error(request, "Это упражнение уже добавлено в тренировку.")
        return _selection_redirect(request, workout)

    item.exercise = exercise
    item.save(update_fields=["exercise"])
    WorkoutSet.objects.get_or_create(
        workout_exercise=item,
        position=1,
        defaults={"load_kg": 0},
    )
    _record_exercise_selection(request.user, exercise)
    return _selection_redirect(request, workout)


@login_required
def add_exercise(request, pk, exercise_pk):
    workout = _user_workout(request, pk)
    exercise = get_object_or_404(visible_exercises(request.user), pk=exercise_pk)
    if request.method == "POST":
        position = (workout.items.aggregate(value=Max("position"))["value"] or 0) + 1
        item, created = WorkoutExercise.objects.get_or_create(
            workout=workout, exercise=exercise, defaults={"position": position}
        )
        if created:
            WorkoutSet.objects.create(workout_exercise=item, position=1, load_kg=0)
            _record_exercise_selection(request.user, exercise)
    return redirect("workout_detail", pk=pk)


@login_required
def remove_exercise(request, pk, item_pk):
    workout = _user_workout(request, pk)
    if request.method == "POST":
        get_object_or_404(workout.items, pk=item_pk).delete()
    return redirect("workout_detail", pk=pk)


@login_required
@transaction.atomic
def move_exercise(request, pk, item_pk, direction):
    workout = _user_workout(request, pk)
    item = get_object_or_404(workout.items, pk=item_pk)
    if request.method == "POST":
        if direction == "up":
            neighbor = (
                workout.items.filter(position__lt=item.position).order_by("-position").first()
            )
        else:
            neighbor = workout.items.filter(position__gt=item.position).order_by("position").first()
        if neighbor:
            item.position, neighbor.position = neighbor.position, item.position
            WorkoutExercise.objects.bulk_update([item, neighbor], ["position"])
    return redirect("workout_detail", pk=pk)


@login_required
def add_set(request, pk, item_pk):
    workout = _user_workout(request, pk)
    item = get_object_or_404(workout.items, pk=item_pk, exercise__isnull=False)
    if request.method == "POST":
        last = item.sets.order_by("-position").first()
        WorkoutSet.objects.create(
            workout_exercise=item,
            position=(last.position + 1 if last else 1),
            reps=last.reps if last else None,
            load_kg=last.load_kg if last and last.load_kg is not None else 0,
        )
    return redirect("workout_detail", pk=pk)


@login_required
def save_set(request, pk, set_pk):
    workout = _user_workout(request, pk)
    workout_set = get_object_or_404(WorkoutSet, pk=set_pk, workout_exercise__workout=workout)
    if request.method == "POST":
        form = WorkoutSetForm(request.POST, instance=workout_set)
        if form.is_valid():
            form.save()
            if request.headers.get("HX-Request"):
                workout_set = _set_with_previous_values(workout_set.pk)
                return render(
                    request, "workouts/_set_row.html", {"set": workout_set, "workout": workout}
                )
        elif request.headers.get("HX-Request"):
            return render(
                request,
                "workouts/_set_row.html",
                {"set": workout_set, "workout": workout, "form": form},
                status=422,
            )
    return redirect("workout_detail", pk=pk)


@login_required
def delete_set(request, pk, set_pk):
    workout = _user_workout(request, pk)
    if request.method == "POST":
        get_object_or_404(WorkoutSet, pk=set_pk, workout_exercise__workout=workout).delete()
        if request.headers.get("HX-Request"):
            from django.http import HttpResponse

            return HttpResponse("")
    return redirect("workout_detail", pk=pk)


@login_required
def finish(request, pk):
    workout = _user_workout(request, pk)
    if request.method == "POST":
        if not workout.items.exists():
            messages.error(request, "Добавьте хотя бы одно упражнение.")
        elif workout.items.filter(sets__completed=True).exists():
            workout.status = Workout.Status.COMPLETED
            workout.completed_at = timezone.now()
            workout.save(update_fields=["status", "completed_at"])
            messages.success(request, "Тренировка завершена.")
            return redirect("workout_list")
        else:
            messages.error(request, "Отметьте хотя бы один выполненный подход.")
    return redirect("workout_detail", pk=pk)


@login_required
@transaction.atomic
def clone(request, pk):
    source = _user_workout(request, pk)
    if request.method != "POST":
        return redirect("workout_detail", pk=pk)
    target = Workout.objects.create(
        user=request.user,
        title=source.title,
        started_at=timezone.now(),
        note=source.note,
    )
    for source_item in source.items.all():
        target_item = WorkoutExercise.objects.create(
            workout=target,
            exercise=source_item.exercise,
            position=source_item.position,
            note=source_item.note,
        )
        WorkoutSet.objects.bulk_create(
            [
                WorkoutSet(
                    workout_exercise=target_item,
                    position=item.position,
                    reps=item.reps,
                    load_kg=item.load_kg,
                    is_working=item.is_working,
                    completed=False,
                )
                for item in source_item.sets.all()
            ]
        )
    return redirect("workout_detail", pk=target.pk)


@login_required
def delete(request, pk):
    workout = _user_workout(request, pk)
    if request.method == "POST":
        workout.delete()
        return redirect("workout_list")
    return redirect("workout_detail", pk=pk)
