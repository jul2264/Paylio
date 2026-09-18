from django.urls import path
from . import views

app_name = "investments"

urlpatterns = [
    path("connect/", views.connect_broker, name="connect"),
    path("callback/", views.broker_callback, name="callback"),
    path("holdings/", views.holdings_view, name="holdings"),
]
