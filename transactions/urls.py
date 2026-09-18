from django.urls import path
from transactions import views

app_name = "transactions"

urlpatterns = [
    path("", views.transaction_list, name="list"),
    path("", views.transaction_list, name="index"),
    path("table/", views.transaction_table_partial, name="table_partial"),
    path("add/", views.transaction_create, name="create"),
    path("<int:pk>/recategorize/", views.transaction_recategorize, name="recategorize"),
]
