from django.urls import path
from . import views

app_name = "rates"

urlpatterns = [
    path("widget/", views.rates_widget, name="widget"),
]
