from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.shortcuts import get_object_or_404, redirect, render
from django_htmx.http import trigger_client_event
from .categorization import categorize, record_user_correction
from .forms import TransactionForm
from .importers import import_csv
from .models import Category, FinancialAccount, Transaction


@login_required
def transaction_list(request):
    form = TransactionForm(user=request.user)
    categories = Category.objects.filter(user=request.user).order_by("name")
    return render(
        request,
        "transactions/list.html",
        {"form": form, "categories": categories},
    )


@login_required
def transaction_table_partial(request):
    qs = Transaction.objects.filter(user=request.user).select_related("category", "account").order_by("-date")
    category = request.GET.get("category")
    if category:
        qs = qs.filter(category_id=category)
    categories = Category.objects.filter(user=request.user).order_by("name")
    return render(
        request,
        "partials/_transaction_table.html",
        {"transactions": qs[:100], "categories": categories},
    )


@login_required
def transaction_create(request):
    form = TransactionForm(request.POST, user=request.user)
    form.instance.user = request.user
    if form.is_valid():
        txn = form.save()
        if txn.category is None:
            categorize(txn)
        cache.delete(f"dashboard:{request.user.id}:{txn.date.year}-{txn.date.month}")
        cache.delete(f"budget_progress:{request.user.id}:{txn.date.year}-{txn.date.month}")
        categories = Category.objects.filter(user=request.user).order_by("name")
        response = render(request, "partials/_transaction_row.html", {"txn": txn, "categories": categories})
        response = trigger_client_event(response, "transactionsChanged")
        response["HX-Trigger"] = "transactionsChanged"
        return response
    return render(request, "partials/_transaction_form_errors.html", {"form": form})


@login_required
def transaction_recategorize(request, pk):
    txn = get_object_or_404(Transaction, pk=pk, user=request.user)
    category = get_object_or_404(Category, pk=request.POST["category"], user=request.user)
    record_user_correction(txn, category)
    cache.delete(f"dashboard:{request.user.id}:{txn.date.year}-{txn.date.month}")
    cache.delete(f"budget_progress:{request.user.id}:{txn.date.year}-{txn.date.month}")
    categories = Category.objects.filter(user=request.user).order_by("name")
    return render(request, "partials/_transaction_row.html", {"txn": txn, "categories": categories})


@login_required
def import_csv_view(request):
    if request.method == "POST":
        account_id = request.POST.get("account")
        account = get_object_or_404(FinancialAccount, id=account_id, user=request.user)
        csv_file = request.FILES.get("file")
        if not csv_file:
            messages.error(request, "Please select a CSV file to upload.")
            return redirect("transactions:import_csv")
        try:
            created_count, affected_months = import_csv(request.user, account, csv_file)
            for year, month in affected_months:
                cache.delete(f"dashboard:{request.user.id}:{year}-{month}")
                cache.delete(f"budget_progress:{request.user.id}:{year}-{month}")
            messages.success(
                request,
                f"Successfully imported {created_count} new transaction(s)."
            )
            return redirect("transactions:list")
        except Exception as e:
            messages.error(request, f"Error importing CSV: {str(e)}")
            return redirect("transactions:import_csv")

    accounts = FinancialAccount.objects.filter(user=request.user)
    return render(request, "transactions/import_csv.html", {"accounts": accounts})

