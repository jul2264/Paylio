from django.urls import path
from budgets import views

app_name = "budgets"

urlpatterns = [
    path("", views.budget_list, name="list"),
    path("create/", views.budget_create, name="create"),
    path("<int:pk>/delete/", views.budget_delete, name="delete"),
    path("progress/", views.progress_partial, name="progress_partial"),
]
