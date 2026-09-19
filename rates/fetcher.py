import requests
from django.conf import settings

TROY_OUNCE_TO_GRAM = 31.1034768
SYMBOLS = {"GOLD": "XAU", "SILVER": "XAG", "PLATINUM": "XPT"}


def fetch_price_per_gram_inr(metal: str) -> float:
    resp = requests.get(
        f"https://www.goldapi.io/api/{SYMBOLS[metal]}/INR",
        headers={"x-access-token": settings.METALS_API_KEY},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    if "price" not in data:
        raise ValueError(
            f"GoldAPI response for {metal} missing 'price' key. Got keys: {list(data.keys())}"
        )
    price_per_oz_inr = data["price"]
    return price_per_oz_inr / TROY_OUNCE_TO_GRAM
