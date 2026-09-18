from datetime import timedelta
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone
from django_otp.decorators import otp_required
from integrations.brokers.kite import exchange_request_token, get_login_url
from .models import BrokerConnection


@login_required
@otp_required(login_url="otp_setup")
def connect_broker(request):
    return redirect(get_login_url())


@login_required
@otp_required(login_url="otp_setup")
def broker_callback(request):
    access_token = exchange_request_token(request.GET["request_token"])
    BrokerConnection.objects.update_or_create(
        user=request.user,
        broker="zerodha",
        defaults={
            "encrypted_access_token": access_token,
            "token_expires_at": timezone.now() + timedelta(hours=20),
        },
    )
    return redirect("investments:holdings")


@login_required
def holdings_view(request):
    connection = BrokerConnection.objects.filter(user=request.user, broker="zerodha").first()
    expired = connection is None or connection.token_expires_at < timezone.now()
    holdings = [] if expired else list(connection.holding_set.all().order_by("symbol"))

    total_invested = sum((h.quantity * h.avg_price for h in holdings), start=0)
    current_value = sum(
        (h.quantity * (h.last_synced_price or h.avg_price) for h in holdings),
        start=0,
    )
    total_pnl = current_value - total_invested
    pnl_pct = (total_pnl / total_invested * 100) if total_invested > 0 else 0

    return render(
        request,
        "investments/holdings.html",
        {
            "connection": connection,
            "holdings": holdings,
            "needs_reconnect": expired,
            "total_invested": total_invested,
            "current_value": current_value,
            "total_pnl": total_pnl,
            "pnl_pct": pnl_pct,
        },
    )
