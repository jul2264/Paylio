from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("", include("dashboard.urls")),
    path("transactions/", include("transactions.urls")),
    path("budgets/", include("budgets.urls")),
    path("advisor/", include("advisor.urls")),
    path("investments/", include("investments.urls")),
    path("rates/", include("rates.urls")),
    path("api/v1/", include("api.urls")),
]
