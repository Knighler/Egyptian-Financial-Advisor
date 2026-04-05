"""
Gold purity calculations for the Egyptian Financial Advisor.

This module provides constants and functions to work with standard gold purities
(karats and fineness) and calculate gold values based on weight and current price.
"""

# Standard gold purities: karat -> fineness (parts per 1000)
GOLD_PURITIES = {
    24: 999,
    22: 916,
    21: 875,
    18: 750,
    14: 585,
    12: 500,
    10: 417,
    9: 375,
}


def karat_to_fineness(karat: int) -> int:
    """Return the fineness (parts per 1000) for a given karat value.

    Args:
        karat: Gold karat (e.g. 24, 22, 21, 18, 14, 12, 10, 9).

    Returns:
        Fineness value (parts per 1000).

    Raises:
        ValueError: If the karat is not a recognised standard purity.
    """
    if karat not in GOLD_PURITIES:
        raise ValueError(
            f"Unsupported karat: {karat}. "
            f"Supported values are: {sorted(GOLD_PURITIES.keys())}"
        )
    return GOLD_PURITIES[karat]


def fineness_to_karat(fineness: int) -> int:
    """Return the karat for a given fineness value.

    Args:
        fineness: Gold fineness (parts per 1000).

    Returns:
        Karat value.

    Raises:
        ValueError: If the fineness does not match a recognised standard purity.
    """
    reverse = {v: k for k, v in GOLD_PURITIES.items()}
    if fineness not in reverse:
        raise ValueError(
            f"Unsupported fineness: {fineness}. "
            f"Supported values are: {sorted(reverse.keys())}"
        )
    return reverse[fineness]


def purity_ratio(karat: int) -> float:
    """Return the gold purity as a ratio between 0 and 1 for a given karat.

    Args:
        karat: Gold karat (e.g. 24, 22, 21, 18, 14, 12, 10, 9).

    Returns:
        Purity ratio (e.g. 0.999 for 24K, 0.916 for 22K).

    Raises:
        ValueError: If the karat is not a recognised standard purity.
    """
    return karat_to_fineness(karat) / 1000


def calculate_gold_value(
    weight_grams: float,
    price_per_gram_24k: float,
    karat: int,
) -> float:
    """Calculate the value of a gold item given its weight, purity and the
    current price of 24K gold.

    Args:
        weight_grams: Weight of the gold item in grams.
        price_per_gram_24k: Current market price of 24K (pure) gold per gram
            in the desired currency (e.g. EGP).
        karat: Gold purity in karats (e.g. 24, 22, 21, 18, 14, 12, 10, 9).

    Returns:
        Monetary value of the gold item.

    Raises:
        ValueError: If weight or price are negative, or karat is not supported.
    """
    if weight_grams < 0:
        raise ValueError("weight_grams must be non-negative.")
    if price_per_gram_24k < 0:
        raise ValueError("price_per_gram_24k must be non-negative.")

    ratio = purity_ratio(karat)
    return weight_grams * price_per_gram_24k * ratio


def price_per_gram(price_per_gram_24k: float, karat: int) -> float:
    """Return the price per gram for a specific karat given the 24K price.

    Args:
        price_per_gram_24k: Current market price of 24K gold per gram.
        karat: Gold purity in karats.

    Returns:
        Price per gram for the requested karat.

    Raises:
        ValueError: If price is negative or karat is not supported.
    """
    if price_per_gram_24k < 0:
        raise ValueError("price_per_gram_24k must be non-negative.")

    return price_per_gram_24k * purity_ratio(karat)


def convert_weight_to_24k_equivalent(weight_grams: float, karat: int) -> float:
    """Convert a gold item's weight to its 24K pure-gold equivalent weight.

    Args:
        weight_grams: Weight of the gold item in grams.
        karat: Gold purity in karats.

    Returns:
        Equivalent weight in 24K pure gold (grams).

    Raises:
        ValueError: If weight is negative or karat is not supported.
    """
    if weight_grams < 0:
        raise ValueError("weight_grams must be non-negative.")

    return weight_grams * purity_ratio(karat)
