from django.contrib.auth import get_user_model
from rest_framework import serializers

from advisor.models import AdviceMessage, Insight
from budgets.models import Budget
from transactions.models import Category, FinancialAccount, Transaction
from .models import DeviceToken

User = get_user_model()


class UserRegistrationSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ["id", "username", "email", "password"]

    def validate_email(self, value):
        normalized = value.strip().lower()
        if User.objects.filter(email__iexact=normalized).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return normalized

    def create(self, validated_data):
        return User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
        )


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "parent", "kind"]
        read_only_fields = ["id"]


class FinancialAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinancialAccount
        fields = ["id", "name", "account_type", "currency"]
        read_only_fields = ["id"]


class TransactionSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True, default=None)
    account_name = serializers.CharField(source="account.name", read_only=True)

    class Meta:
        model = Transaction
        fields = [
            "id",
            "account",
            "account_name",
            "category",
            "category_name",
            "amount",
            "kind",
            "date",
            "merchant",
            "description",
            "source",
            "external_id",
            "is_recurring",
            "created_at",
        ]
        read_only_fields = ["id", "created_at", "source"]


class BudgetSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = Budget
        fields = ["id", "category", "category_name", "monthly_limit"]
        read_only_fields = ["id"]


class AdviceMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdviceMessage
        fields = ["id", "insight", "body", "model_used", "user_feedback", "created_at"]
        read_only_fields = ["id", "created_at"]


class InsightSerializer(serializers.ModelSerializer):
    advice = AdviceMessageSerializer(many=True, read_only=True)

    class Meta:
        model = Insight
        fields = [
            "id",
            "rule_key",
            "severity",
            "category",
            "period_start",
            "period_end",
            "summary",
            "raw_data",
            "created_at",
            "advice",
        ]
        read_only_fields = ["id", "created_at"]


class DeviceTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceToken
        fields = ["id", "expo_push_token", "created_at"]
        read_only_fields = ["id", "created_at"]
