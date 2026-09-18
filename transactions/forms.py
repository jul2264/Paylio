from django import forms
from .models import FinancialAccount, Category, Transaction


class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ["account", "category", "amount", "date", "merchant", "description"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields["account"].queryset = FinancialAccount.objects.filter(user=user)
            self.fields["category"].queryset = Category.objects.filter(user=user)
