from django.urls import reverse_lazy
from django.views.generic import CreateView
from accounts.models import User
from accounts.forms import CustomUserCreationForm


class SignupView(CreateView):
    model = User
    form_class = CustomUserCreationForm
    template_name = "accounts/signup.html"
    success_url = reverse_lazy("login")
