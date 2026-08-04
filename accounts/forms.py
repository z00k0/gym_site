from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.utils import timezone

from .models import BodyWeightMeasurement, HealthProfile, User


class RegistrationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("email",)


class HealthProfileForm(forms.ModelForm):
    class Meta:
        model = HealthProfile
        fields = ("birth_date", "height_cm")
        widgets = {"birth_date": forms.DateInput(attrs={"type": "date"})}

    def clean_birth_date(self):
        value = self.cleaned_data.get("birth_date")
        if value and value > timezone.localdate():
            raise forms.ValidationError("Дата рождения не может быть в будущем.")
        return value


class BodyWeightForm(forms.ModelForm):
    class Meta:
        model = BodyWeightMeasurement
        fields = ("weight_kg", "measured_at", "note")
        widgets = {"measured_at": forms.DateTimeInput(attrs={"type": "datetime-local"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.is_bound:
            self.initial["measured_at"] = timezone.localtime().strftime("%Y-%m-%dT%H:%M")
