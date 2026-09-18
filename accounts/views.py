import base64
import io
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView
from django_otp import login as otp_login
from django_otp.plugins.otp_totp.models import TOTPDevice
import qrcode
from accounts.forms import CustomUserCreationForm
from accounts.models import User


class SignupView(CreateView):
    model = User
    form_class = CustomUserCreationForm
    template_name = "accounts/signup.html"
    success_url = reverse_lazy("login")


@login_required
def otp_setup(request):
    device = TOTPDevice.objects.filter(user=request.user, confirmed=True).first()
    if not device:
        device = TOTPDevice.objects.filter(user=request.user, confirmed=False).first()
        if not device:
            device = TOTPDevice.objects.create(user=request.user, name="default", confirmed=False)

    if request.method == "POST":
        token = request.POST.get("token", "").strip()
        if device.verify_token(token):
            if not device.confirmed:
                device.confirmed = True
                device.save()
            otp_login(request, device)
            messages.success(request, "Two-factor authentication verified successfully!")
            next_url = request.GET.get("next") or request.POST.get("next") or "dashboard"
            return redirect(next_url)
        else:
            messages.error(request, "Invalid 6-digit verification code. Please try again.")

    url = device.config_url
    img = qrcode.make(url)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    qr_b64 = base64.b64encode(buffer.getvalue()).decode()

    return render(
        request,
        "accounts/otp_setup.html",
        {
            "qr_b64": qr_b64,
            "device": device,
            "next": request.GET.get("next", ""),
        },
    )
