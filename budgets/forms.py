from django import forms
from transactions.models import Category
from .models import Budget


class BudgetForm(forms.ModelForm):
    class Meta:
        model = Budget
        fields = ["category", "monthly_limit"]
        widgets = {
            "monthly_limit": forms.NumberInput(attrs={
                "step": "0.01",
                "placeholder": "e.g. 5000.00",
                "class": "w-full bg-slate-800/60 border border-slate-700/80 rounded-xl px-3.5 py-2 text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 text-sm",
            }),
            "category": forms.Select(attrs={
                "class": "w-full bg-slate-800/60 border border-slate-700/80 rounded-xl px-3.5 py-2 text-slate-100 focus:outline-none focus:ring-2 focus:ring-emerald-500 text-sm",
            }),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields["category"].queryset = Category.objects.filter(
                user=user, kind=Category.EXPENSE
            ).order_by("name")
