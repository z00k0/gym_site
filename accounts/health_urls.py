from django.urls import path

from . import views

urlpatterns = [
    path("", views.health, name="health"),
    path("profile/", views.update_profile, name="update_profile"),
    path("weight/add/", views.add_weight, name="add_weight"),
    path("weight/<int:pk>/delete/", views.delete_weight, name="delete_weight"),
]
