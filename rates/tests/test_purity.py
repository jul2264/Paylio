from rates.purity import (
    GOLD_PURITIES,
    PLATINUM_PURITIES,
    SILVER_PURITIES,
    compute_purity_rates,
)


def test_compute_purity_rates_gold():
    base_price = 6000.0
    rates = compute_purity_rates(base_price, GOLD_PURITIES)

    assert rates["24K"] == 6000.0
    assert rates["22K"] == 5500.0
    assert rates["18K"] == 4500.0


def test_compute_purity_rates_silver():
    base_price = 80.0
    rates = compute_purity_rates(base_price, SILVER_PURITIES)

    assert rates["999 Fine"] == round(80.0 * 0.999, 2)
    assert rates["958 Britannia"] == round(80.0 * 0.958, 2)
    assert rates["925 Sterling"] == round(80.0 * 0.925, 2)
    assert rates["900 Coin"] == round(80.0 * 0.900, 2)
    assert rates["800 Continental"] == round(80.0 * 0.800, 2)


def test_compute_purity_rates_platinum():
    base_price = 3000.0
    rates = compute_purity_rates(base_price, PLATINUM_PURITIES)

    assert rates["999"] == round(3000.0 * 0.999, 2)
    assert rates["950"] == round(3000.0 * 0.950, 2)
    assert rates["900"] == round(3000.0 * 0.900, 2)
    assert rates["850"] == round(3000.0 * 0.850, 2)
