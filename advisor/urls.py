from django.urls import path
from advisor import views

app_name = "advisor"

urlpatterns = [
    path("feed/", views.feed_partial, name="feed_partial"),
    path("refresh/", views.refresh_insights, name="refresh"),
]
