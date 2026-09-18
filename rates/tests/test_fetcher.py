import pytest
import requests
import responses
from rates.fetcher import TROY_OUNCE_TO_GRAM, fetch_price_per_gram_inr


@responses.activate
def test_fetch_price_converts_oz_to_gram_correctly():
    responses.add(
        responses.GET,
        "https://www.goldapi.io/api/XAU/INR",
        json={"price": 250000.0},
        status=200,
    )

    price_per_gram = fetch_price_per_gram_inr("GOLD")
    expected = 250000.0 / TROY_OUNCE_TO_GRAM
    assert price_per_gram == pytest.approx(expected)


@responses.activate
def test_fetch_price_raises_on_http_error():
    responses.add(
        responses.GET,
        "https://www.goldapi.io/api/XAU/INR",
        json={"error": "Unauthorized"},
        status=401,
    )

    with pytest.raises(requests.exceptions.HTTPError):
        fetch_price_per_gram_inr("GOLD")
