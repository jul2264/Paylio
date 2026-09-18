from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.shortcuts import render
from django_htmx.http import trigger_client_event
from .forms import TransactionForm
from .models import Category, Transaction


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
    return render(request, "partials/_transaction_table.html", {"transactions": qs[:100]})


@login_required
def transaction_create(request):
    form = TransactionForm(request.POST, user=request.user)
    form.instance.user = request.user
    if form.is_valid():
        txn = form.save()
        cache.delete(f"dashboard:{request.user.id}:{txn.date.year}-{txn.date.month}")
        response = render(request, "partials/_transaction_row.html", {"txn": txn})
        response = trigger_client_event(response, "transactionsChanged")
        response["HX-Trigger"] = "transactionsChanged"
        return response
    return render(request, "partials/_transaction_form_errors.html", {"form": form})
