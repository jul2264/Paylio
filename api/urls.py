from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import (
    BudgetViewSet,
    CategoryViewSet,
    FinancialAccountViewSet,
    RegisterView,
    TransactionViewSet,
    advisor_feed,
    advisor_refresh,
    dashboard_summary,
    metal_rates,
    register_device_token,
)

app_name = "api"

router = DefaultRouter()
router.register("transactions", TransactionViewSet, basename="transaction")
router.register("categories", CategoryViewSet, basename="category")
router.register("accounts", FinancialAccountViewSet, basename="account")
router.register("budgets", BudgetViewSet, basename="budget")

urlpatterns = [
    path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("register/", RegisterView.as_view(), name="register"),
    path("dashboard/summary/", dashboard_summary, name="dashboard_summary"),
    path("advisor/feed/", advisor_feed, name="advisor_feed"),
    path("advisor/refresh/", advisor_refresh, name="advisor_refresh"),
    path("rates/", metal_rates, name="metal_rates"),
    path("device-token/", register_device_token, name="register_device_token"),
    path("", include(router.urls)),
]
