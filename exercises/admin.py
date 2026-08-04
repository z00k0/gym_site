from django.contrib import admin

from .models import Exercise, UserExerciseAlias, UserExerciseUsage


@admin.register(Exercise)
class ExerciseAdmin(admin.ModelAdmin):
    list_display = ("name", "equipment", "load_kind", "owner", "is_active")
    search_fields = ("name", "source_id")
    list_filter = ("load_kind", "body_part", "is_active")


admin.site.register(UserExerciseAlias)
admin.site.register(UserExerciseUsage)
