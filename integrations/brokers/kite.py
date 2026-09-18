from django.conf import settings
from kiteconnect import KiteConnect


def get_login_url():
    return KiteConnect(api_key=settings.KITE_API_KEY).login_url()


def exchange_request_token(request_token):
    kite = KiteConnect(api_key=settings.KITE_API_KEY)
    data = kite.generate_session(request_token, api_secret=settings.KITE_API_SECRET)
    return data["access_token"]


def fetch_holdings(access_token):
    kite = KiteConnect(api_key=settings.KITE_API_KEY)
    kite.set_access_token(access_token)
    return kite.holdings()
