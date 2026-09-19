from django.urls import path
from transactions import views

app_name = "transactions"

urlpatterns = [
    path("", views.transaction_list, name="list"),
    path("table/", views.transaction_table_partial, name="table_partial"),
    path("add/", views.transaction_create, name="create"),
    path("accounts/create/", views.account_create, name="account_create"),
    path("import/", views.import_csv_view, name="import_csv"),
    path("<int:pk>/recategorize/", views.transaction_recategorize, name="recategorize"),
    path("<int:pk>/toggle-recurring/", views.transaction_toggle_recurring, name="toggle_recurring"),
]
