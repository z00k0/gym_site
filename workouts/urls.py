from django.urls import path

from . import views

urlpatterns = [
    path("", views.workout_list, name="workout_list"),
    path("new/", views.create, name="workout_create"),
    path("<int:pk>/", views.detail, name="workout_detail"),
    path("<int:pk>/edit/", views.edit, name="workout_edit"),
    path("<int:pk>/exercises/", views.exercise_picker, name="workout_exercise_picker"),
    path(
        "<int:pk>/exercises/empty/add/",
        views.add_empty_exercise,
        name="workout_add_empty_exercise",
    ),
    path(
        "<int:pk>/exercises/<int:exercise_pk>/add/", views.add_exercise, name="workout_add_exercise"
    ),
    path(
        "<int:pk>/items/<int:item_pk>/exercise-options/",
        views.exercise_options,
        name="workout_exercise_options",
    ),
    path(
        "<int:pk>/items/<int:item_pk>/exercise/<int:exercise_pk>/select/",
        views.select_exercise,
        name="workout_select_exercise",
    ),
    path(
        "<int:pk>/items/<int:item_pk>/remove/",
        views.remove_exercise,
        name="workout_remove_exercise",
    ),
    path(
        "<int:pk>/items/<int:item_pk>/move/<str:direction>/",
        views.move_exercise,
        name="workout_move_exercise",
    ),
    path("<int:pk>/items/<int:item_pk>/sets/add/", views.add_set, name="workout_add_set"),
    path("<int:pk>/sets/<int:set_pk>/", views.save_set, name="workout_save_set"),
    path(
        "<int:pk>/sets/<int:set_pk>/move/<str:direction>/",
        views.move_set,
        name="workout_move_set",
    ),
    path("<int:pk>/sets/<int:set_pk>/delete/", views.delete_set, name="workout_delete_set"),
    path("<int:pk>/finish/", views.finish, name="workout_finish"),
    path("<int:pk>/clone/", views.clone, name="workout_clone"),
    path("<int:pk>/delete/", views.delete, name="workout_delete"),
]
