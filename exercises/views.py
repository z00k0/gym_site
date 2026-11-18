from django.contrib.auth.decorators import login_required
from django.db.models import DecimalField, ExpressionWrapper, F, Prefetch, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render

from .forms import AliasForm, ExerciseForm
from .models import Exercise, UserExerciseAlias


def visible_exercises(user):
    return Exercise.objects.filter(Q(owner__isnull=True) | Q(owner=user), is_active=True)


@login_required
def catalog(request):
    query = request.GET.get("q", "").strip()
    exercises = visible_exercises(request.user).prefetch_related(
        Prefetch(
            "aliases",
            queryset=UserExerciseAlias.objects.filter(user=request.user),
            to_attr="current_alias",
        )
    )
    if query:
        exercises = exercises.filter(
            Q(name__icontains=query)
            | Q(aliases__user=request.user, aliases__alias__icontains=query)
        ).distinct()
    if request.GET.get("load_kind"):
        exercises = exercises.filter(load_kind=request.GET["load_kind"])
    if request.GET.get("body_part"):
        exercises = exercises.filter(body_part=request.GET["body_part"])
    body_parts = (
        Exercise.objects.filter(owner__isnull=True)
        .exclude(body_part="")
        .values_list("body_part", flat=True)
        .distinct()
        .order_by("body_part")
    )
    return render(
        request,
        "exercises/catalog.html",
        {
            "exercises": exercises[:100],
            "query": query,
            "body_parts": body_parts,
        },
    )


@login_required
def detail(request, pk):
    exercise = get_object_or_404(visible_exercises(request.user), pk=pk)
    alias = UserExerciseAlias.objects.filter(user=request.user, exercise=exercise).first()
    from workouts.models import WorkoutSet

    completed_sets = WorkoutSet.objects.filter(
        workout_exercise__workout__user=request.user,
        workout_exercise__exercise=exercise,
        completed=True,
        workout_exercise__workout__status="completed",
    )
    history = completed_sets.select_related("workout_exercise__workout").order_by(
        "-workout_exercise__workout__started_at"
    )[:30]
    best_set = (
        completed_sets.filter(load_kg__isnull=False, reps__isnull=False)
        .order_by("-load_kg", "-reps")
        .values("load_kg", "reps")
        .first()
    )
    progress = {"best_load": best_set["load_kg"], "best_reps": best_set["reps"]} if best_set else {}
    if exercise.load_kind == Exercise.LoadKind.EXTERNAL:
        progress["volume"] = completed_sets.aggregate(
            value=Sum(
                ExpressionWrapper(
                    F("reps") * F("load_kg"),
                    output_field=DecimalField(max_digits=14, decimal_places=2),
                )
            )
        )["value"]
    return render(
        request,
        "exercises/detail.html",
        {
            "exercise": exercise,
            "alias_form": AliasForm(instance=alias),
            "history": history,
            "progress": progress,
        },
    )


@login_required
def save_alias(request, pk):
    exercise = get_object_or_404(visible_exercises(request.user), pk=pk)
    alias = UserExerciseAlias.objects.filter(user=request.user, exercise=exercise).first()
    form = AliasForm(request.POST, instance=alias)
    if form.is_valid():
        value = form.save(commit=False)
        value.user, value.exercise = request.user, exercise
        if value.alias.strip():
            value.save()
    return redirect("exercise_detail", pk=pk)


@login_required
def create(request):
    form = ExerciseForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        exercise = form.save(commit=False)
        exercise.owner = request.user
        exercise.save()
        return redirect("exercise_detail", pk=exercise.pk)
    return render(request, "form_page.html", {"form": form, "title": "Новое упражнение"})


@login_required
def edit(request, pk):
    exercise = get_object_or_404(Exercise, pk=pk, owner=request.user, is_active=True)
    form = ExerciseForm(request.POST or None, instance=exercise)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("exercise_detail", pk=pk)
    return render(request, "form_page.html", {"form": form, "title": "Редактировать упражнение"})


@login_required
def archive(request, pk):
    exercise = get_object_or_404(Exercise, pk=pk, owner=request.user)
    if request.method == "POST":
        exercise.is_active = False
        exercise.save(update_fields=["is_active"])
    return redirect("exercise_catalog")
