from datetime import date
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.shortcuts import get_object_or_404, redirect, render
from .forms import BudgetForm
from .models import Budget
from .services import get_budget_progress


@login_required
def progress_partial(request):
    today = date.today()
    cache_key = f"budget_progress:{request.user.id}:{today.year}-{today.month}"
    rows = cache.get(cache_key)
    if rows is None:
        rows = get_budget_progress(request.user, today.year, today.month)
        cache.set(cache_key, rows, timeout=300)
    return render(request, "partials/_budget_progress.html", {"rows": rows})


@login_required
def budget_list(request):
    today = date.today()
    cache_key = f"budget_progress:{request.user.id}:{today.year}-{today.month}"
    progress_rows = cache.get(cache_key)
    if progress_rows is None:
        progress_rows = get_budget_progress(request.user, today.year, today.month)
        cache.set(cache_key, progress_rows, timeout=300)
    budgets = Budget.objects.filter(user=request.user).select_related("category").order_by("category__name")
    return render(request, "budgets/list.html", {
        "budgets": budgets,
        "progress_rows": progress_rows,
        "current_month": today.strftime("%B %Y"),
    })


@login_required
def budget_create(request):
    if request.method == "POST":
        form = BudgetForm(request.POST, user=request.user)
        if form.is_valid():
            budget = form.save(commit=False)
            budget.user = request.user
            budget.save()
            today = date.today()
            cache.delete(f"budget_progress:{request.user.id}:{today.year}-{today.month}")
            messages.success(request, f"Budget for {budget.category.name} created successfully.")
            return redirect("budgets:list")
    else:
        form = BudgetForm(user=request.user)
    return render(request, "budgets/create.html", {"form": form})


@login_required
def budget_delete(request, pk):
    budget = get_object_or_404(Budget, pk=pk, user=request.user)
    if request.method == "POST":
        category_name = budget.category.name
        budget.delete()
        today = date.today()
        cache.delete(f"budget_progress:{request.user.id}:{today.year}-{today.month}")
        messages.success(request, f"Budget for {category_name} removed.")
        return redirect("budgets:list")
    return render(request, "budgets/confirm_delete.html", {"budget": budget})
