from django.urls import path
from .views import SetuConsentWebhook

app_name = "integrations"

urlpatterns = [
    path("setu/webhook/", SetuConsentWebhook.as_view(), name="setu_webhook"),
]
