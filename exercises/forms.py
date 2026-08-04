from django import forms

from .models import Exercise, UserExerciseAlias


class ExerciseForm(forms.ModelForm):
    class Meta:
        model = Exercise
        fields = ("name", "instructions_ru", "body_part", "equipment", "target", "load_kind")
        widgets = {"instructions_ru": forms.Textarea(attrs={"rows": 4})}


class AliasForm(forms.ModelForm):
    class Meta:
        model = UserExerciseAlias
        fields = ("alias",)
