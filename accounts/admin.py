from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import BodyWeightMeasurement, HealthProfile, User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    ordering = ("email",)
    list_display = ("email", "is_staff", "is_active")
    fieldsets = ((None, {"fields": ("email", "password")}),) + UserAdmin.fieldsets[2:]
    add_fieldsets = ((None, {"fields": ("email", "password1", "password2")}),)


admin.site.register(HealthProfile)
admin.site.register(BodyWeightMeasurement)
