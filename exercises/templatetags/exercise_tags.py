from django import template

from exercises.models import UserExerciseAlias

register = template.Library()


@register.filter
def exercise_name(exercise, user):
    alias = (
        UserExerciseAlias.objects.filter(user=user, exercise=exercise)
        .values_list("alias", flat=True)
        .first()
    )
    return alias or exercise.name


@register.filter
def get_item(mapping, key):
    return mapping.get(key)
