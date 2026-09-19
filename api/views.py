from datetime import date
from django.core.cache import cache
from rest_framework import generics, status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from advisor.ai import generate_advice
from advisor.models import Insight
from advisor.rules import run_rules_for_user
from budgets.models import Budget
from dashboard.services import get_monthly_summary
from rates.models import MetalRateSnapshot
from rates.purity import GOLD_PURITIES, PLATINUM_PURITIES, SILVER_PURITIES, compute_purity_rates
from transactions.categorization import categorize
from transactions.models import Category, FinancialAccount, Transaction
from .models import DeviceToken
from .serializers import (
    BudgetSerializer,
    CategorySerializer,
    DeviceTokenSerializer,
    FinancialAccountSerializer,
    InsightSerializer,
    TransactionSerializer,
    UserRegistrationSerializer,
)


class RegisterView(generics.CreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = UserRegistrationSerializer


class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Category.objects.filter(user=self.request.user).order_by("name")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class FinancialAccountViewSet(viewsets.ModelViewSet):
    serializer_class = FinancialAccountSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return FinancialAccount.objects.filter(user=self.request.user).order_by("name")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class TransactionViewSet(viewsets.ModelViewSet):
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = (
            Transaction.objects.filter(user=self.request.user)
            .select_related("category", "account")
            .order_by("-date", "-id")
        )
        category_id = self.request.query_params.get("category")
        if category_id:
            qs = qs.filter(category_id=category_id)
        return qs

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        vd = serializer.validated_data

        account = vd.get("account")
        tx_date = vd.get("date")
        amount = vd.get("amount")
        merchant = vd.get("merchant", "")

        from transactions.categorization import normalize_merchant
        norm_merchant = normalize_merchant(merchant)

        existing = Transaction.objects.filter(
            user=request.user,
            account=account,
            date=tx_date,
            amount=amount,
        )
        for cand in existing:
            if normalize_merchant(cand.merchant) == norm_merchant:
                out_serializer = self.get_serializer(cand)
                return Response(out_serializer.data, status=status.HTTP_200_OK)

        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        txn = serializer.save(user=self.request.user)
        if txn.category is None:
            categorize(txn)
        cache.delete(f"dashboard:{self.request.user.id}:{txn.date.year}-{txn.date.month}")
        cache.delete(f"budget_progress:{self.request.user.id}:{txn.date.year}-{txn.date.month}")


class BudgetViewSet(viewsets.ModelViewSet):
    serializer_class = BudgetSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Budget.objects.filter(user=self.request.user).select_related("category")

    def _invalidate_cache(self):
        today = date.today()
        cache.delete(f"budget_progress:{self.request.user.id}:{today.year}-{today.month}")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
        self._invalidate_cache()

    def perform_update(self, serializer):
        serializer.save()
        self._invalidate_cache()

    def perform_destroy(self, instance):
        instance.delete()
        self._invalidate_cache()


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard_summary(request):
    today = date.today()
    try:
        year = int(request.query_params.get("year", today.year))
        month = int(request.query_params.get("month", today.month))
    except (ValueError, TypeError):
        year, month = today.year, today.month

    summary = get_monthly_summary(request.user, year, month)
    return Response({"year": year, "month": month, **summary})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def advisor_feed(request):
    insights = (
        Insight.objects.filter(user=request.user)
        .prefetch_related("advice")
        .order_by("-created_at")[:10]
    )
    serializer = InsightSerializer(insights, many=True)
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def advisor_refresh(request):
    rate_key = f"advisor_refresh_lock:{request.user.id}"
    if not cache.add(rate_key, 1, timeout=300):
        return advisor_feed(request)

    today = date.today()
    period_start = today.replace(day=1)
    new_insights = run_rules_for_user(request.user, period_start, today)
    for insight in new_insights:
        try:
            generate_advice(insight)
        except Exception:
            pass
    insights = (
        Insight.objects.filter(user=request.user)
        .prefetch_related("advice")
        .order_by("-created_at")[:10]
    )
    serializer = InsightSerializer(insights, many=True)
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([AllowAny])
def metal_rates(request):
    data = {}
    for metal, table, key in [
        ("GOLD", GOLD_PURITIES, "gold"),
        ("SILVER", SILVER_PURITIES, "silver"),
        ("PLATINUM", PLATINUM_PURITIES, "platinum"),
    ]:
        latest = MetalRateSnapshot.objects.filter(metal=metal).order_by("-fetched_at").first()
        data[key] = compute_purity_rates(float(latest.price_per_gram_999), table) if latest else {}

    latest_snapshot = MetalRateSnapshot.objects.order_by("-fetched_at").first()
    data["last_updated"] = latest_snapshot.fetched_at.isoformat() if latest_snapshot else None
    return Response(data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def register_device_token(request):
    token = request.data.get("expo_push_token")
    if not token:
        return Response({"error": "expo_push_token is required"}, status=status.HTTP_400_BAD_REQUEST)
    device_token, created = DeviceToken.objects.update_or_create(
        expo_push_token=token,
        defaults={"user": request.user},
    )
    serializer = DeviceTokenSerializer(device_token)
    return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
