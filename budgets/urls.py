from django.urls import path
from budgets import views

app_name = "budgets"

urlpatterns = [
    path("progress/", views.progress_partial, name="progress_partial"),
]
