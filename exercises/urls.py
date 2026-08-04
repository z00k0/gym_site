from django.urls import path

from . import views

urlpatterns = [
    path("", views.catalog, name="exercise_catalog"),
    path("new/", views.create, name="exercise_create"),
    path("<int:pk>/", views.detail, name="exercise_detail"),
    path("<int:pk>/alias/", views.save_alias, name="exercise_alias"),
    path("<int:pk>/edit/", views.edit, name="exercise_edit"),
    path("<int:pk>/archive/", views.archive, name="exercise_archive"),
]
