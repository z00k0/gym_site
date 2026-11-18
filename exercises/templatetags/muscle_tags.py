from django import template

register = template.Library()

# Dataset names and aliases mapped to regions in the front and back drawings.
MUSCLE_REGIONS = {
    "neck": ("Шея", "neck|sternocleidomastoid|levator scapulae"),
    "chest": ("Грудь", "chest|pectorals|upper chest"),
    "shoulders": ("Плечи", "shoulders|deltoids|delts|rear deltoids|rotator cuff"),
    "biceps": ("Бицепсы", "biceps|brachialis"),
    "triceps": ("Трицепсы", "triceps"),
    "forearms": ("Предплечья", "forearms|grip muscles|hands|wrists|wrist extensors|wrist flexors"),
    "abs": ("Пресс", "abs|abdominals|lower abs|core"),
    "obliques": ("Косые мышцы живота", "obliques|serratus anterior"),
    "upper_back": ("Верх спины", "upper back|upper back|trapezius|traps|rhomboids|back"),
    "lats": ("Широчайшие", "lats|latissimus dorsi|back"),
    "lower_back": ("Поясница", "lower back|lower back|spine|back"),
    "glutes": ("Ягодицы", "glutes|abductors"),
    "quads": ("Квадрицепсы", "quads|quadriceps|hip flexors"),
    "adductors": ("Приводящие мышцы бедра", "adductors|groin|inner thighs"),
    "hamstrings": ("Задняя поверхность бедра", "hamstrings"),
    "calves": ("Икры", "calves|soleus"),
    "shins": ("Голени", "shins|ankle stabilizers|ankles|feet"),
}


@register.inclusion_tag("workouts/_muscle_map.html")
def workout_muscle_map(items):
    names = set()
    for item in items:
        if item.exercise_id:
            exercise = item.exercise
            for name in (exercise.target, *(exercise.secondary_muscles or [])):
                if isinstance(name, str) and name.strip():
                    names.add(name.strip().casefold())

    active_regions = set()
    muscle_labels = []
    matched_names = set()
    for region, (label, aliases) in MUSCLE_REGIONS.items():
        matches = names.intersection(aliases.split("|"))
        if matches:
            active_regions.add(region)
            muscle_labels.append(label)
            matched_names.update(matches)

    muscle_labels.extend(sorted(names - matched_names))
    return {"active_regions": active_regions, "muscle_labels": muscle_labels}
