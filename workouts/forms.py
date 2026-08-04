from django import forms
from django.utils import timezone

from .models import Workout, WorkoutSet


class WorkoutForm(forms.ModelForm):
    class Meta:
        model = Workout
        fields = ("title", "started_at", "note")
        widgets = {
            "started_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "note": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.is_bound and not self.instance.pk:
            self.initial["started_at"] = timezone.localtime().strftime("%Y-%m-%dT%H:%M")


class WorkoutSetForm(forms.ModelForm):
    class Meta:
        model = WorkoutSet
        fields = ("reps", "load_kg", "is_working", "completed")
        widgets = {
            "reps": forms.NumberInput(attrs={"min": 1, "inputmode": "numeric"}),
            "load_kg": forms.NumberInput(attrs={"step": "0.5", "inputmode": "decimal"}),
        }
