from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import BodyWeightForm, HealthProfileForm, RegistrationForm
from .models import BodyWeightMeasurement, HealthProfile


def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = RegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect("dashboard")
    return render(request, "registration/register.html", {"form": form})


@login_required
def dashboard(request):
    return render(
        request,
        "dashboard.html",
        {
            "recent_workouts": request.user.workouts.select_related().order_by("-started_at")[:5],
            "latest_weight": request.user.body_weights.first(),
        },
    )


def _chart_points(measurements):
    ordered = list(reversed(measurements))
    if not ordered:
        return ""
    values = [float(item.weight_kg) for item in ordered]
    low, high = min(values), max(values)
    span = max(high - low, 1)
    width = 100
    return " ".join(
        f"{(index / max(len(values) - 1, 1)) * width:.1f},{95 - ((value - low) / span) * 85:.1f}"
        for index, value in enumerate(values)
    )


@login_required
def health(request):
    profile, _ = HealthProfile.objects.get_or_create(user=request.user)
    measurements = list(request.user.body_weights.all()[:100])
    return render(
        request,
        "accounts/health.html",
        {
            "profile": profile,
            "measurements": measurements,
            "chart_points": _chart_points(measurements),
            "profile_form": HealthProfileForm(instance=profile),
            "weight_form": BodyWeightForm(),
        },
    )


@login_required
def update_profile(request):
    profile, _ = HealthProfile.objects.get_or_create(user=request.user)
    form = HealthProfileForm(request.POST, instance=profile)
    if form.is_valid():
        form.save()
    return redirect("health")


@login_required
def add_weight(request):
    form = BodyWeightForm(request.POST)
    if form.is_valid():
        measurement = form.save(commit=False)
        measurement.user = request.user
        measurement.save()
    return redirect("health")


@login_required
def delete_weight(request, pk):
    if request.method == "POST":
        get_object_or_404(BodyWeightMeasurement, pk=pk, user=request.user).delete()
    return redirect("health")
