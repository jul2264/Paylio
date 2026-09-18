GOLD_PURITIES = {"24K": 1.0, "22K": 22 / 24, "18K": 18 / 24}

SILVER_PURITIES = {
    "999 Fine": 0.999,
    "958 Britannia": 0.958,
    "925 Sterling": 0.925,
    "900 Coin": 0.900,
    "800 Continental": 0.800,
}

PLATINUM_PURITIES = {"999": 0.999, "950": 0.950, "900": 0.900, "850": 0.850}


def compute_purity_rates(base_price_per_gram, purity_table):
    return {
        label: round(base_price_per_gram * factor, 2)
        for label, factor in purity_table.items()
    }
