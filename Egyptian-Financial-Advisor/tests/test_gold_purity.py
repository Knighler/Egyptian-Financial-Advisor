"""Unit tests for the gold_purity module."""

import pytest

from gold_purity import (
    GOLD_PURITIES,
    calculate_gold_value,
    convert_weight_to_24k_equivalent,
    fineness_to_karat,
    karat_to_fineness,
    price_per_gram,
    purity_ratio,
)


class TestGoldPurities:
    """Tests for the GOLD_PURITIES constant and karat/fineness helpers."""

    def test_all_standard_purities_present(self):
        expected_karats = {24, 22, 21, 18, 14, 12, 10, 9}
        assert set(GOLD_PURITIES.keys()) == expected_karats

    def test_karat_to_fineness_24k(self):
        assert karat_to_fineness(24) == 999

    def test_karat_to_fineness_22k(self):
        assert karat_to_fineness(22) == 916

    def test_karat_to_fineness_21k(self):
        assert karat_to_fineness(21) == 875

    def test_karat_to_fineness_18k(self):
        assert karat_to_fineness(18) == 750

    def test_karat_to_fineness_14k(self):
        assert karat_to_fineness(14) == 585

    def test_karat_to_fineness_12k(self):
        assert karat_to_fineness(12) == 500

    def test_karat_to_fineness_10k(self):
        assert karat_to_fineness(10) == 417

    def test_karat_to_fineness_9k(self):
        assert karat_to_fineness(9) == 375

    def test_karat_to_fineness_invalid(self):
        with pytest.raises(ValueError, match="Unsupported karat: 15"):
            karat_to_fineness(15)

    def test_fineness_to_karat_999(self):
        assert fineness_to_karat(999) == 24

    def test_fineness_to_karat_916(self):
        assert fineness_to_karat(916) == 22

    def test_fineness_to_karat_875(self):
        assert fineness_to_karat(875) == 21

    def test_fineness_to_karat_750(self):
        assert fineness_to_karat(750) == 18

    def test_fineness_to_karat_585(self):
        assert fineness_to_karat(585) == 14

    def test_fineness_to_karat_500(self):
        assert fineness_to_karat(500) == 12

    def test_fineness_to_karat_417(self):
        assert fineness_to_karat(417) == 10

    def test_fineness_to_karat_375(self):
        assert fineness_to_karat(375) == 9

    def test_fineness_to_karat_invalid(self):
        with pytest.raises(ValueError, match="Unsupported fineness: 600"):
            fineness_to_karat(600)

    def test_purity_ratio_24k(self):
        assert purity_ratio(24) == pytest.approx(0.999)

    def test_purity_ratio_22k(self):
        assert purity_ratio(22) == pytest.approx(0.916)

    def test_purity_ratio_21k(self):
        assert purity_ratio(21) == pytest.approx(0.875)

    def test_purity_ratio_18k(self):
        assert purity_ratio(18) == pytest.approx(0.750)

    def test_purity_ratio_14k(self):
        assert purity_ratio(14) == pytest.approx(0.585)

    def test_purity_ratio_12k(self):
        assert purity_ratio(12) == pytest.approx(0.500)

    def test_purity_ratio_10k(self):
        assert purity_ratio(10) == pytest.approx(0.417)

    def test_purity_ratio_9k(self):
        assert purity_ratio(9) == pytest.approx(0.375)


class TestCalculateGoldValue:
    """Tests for the calculate_gold_value function."""

    def test_24k_value(self):
        # 10g of 24K gold at 100 EGP/g => 10 * 100 * 0.999 = 999
        assert calculate_gold_value(10, 100, 24) == pytest.approx(999.0)

    def test_21k_value(self):
        # 10g of 21K gold at 100 EGP/g => 10 * 100 * 0.875 = 875
        assert calculate_gold_value(10, 100, 21) == pytest.approx(875.0)

    def test_18k_value(self):
        # 10g of 18K gold at 100 EGP/g => 10 * 100 * 0.750 = 750
        assert calculate_gold_value(10, 100, 18) == pytest.approx(750.0)

    def test_14k_value(self):
        # 10g of 14K gold at 100 EGP/g => 10 * 100 * 0.585 = 585
        assert calculate_gold_value(10, 100, 14) == pytest.approx(585.0)

    def test_12k_value(self):
        # 10g of 12K gold at 100 EGP/g => 10 * 100 * 0.500 = 500
        assert calculate_gold_value(10, 100, 12) == pytest.approx(500.0)

    def test_10k_value(self):
        # 10g of 10K gold at 100 EGP/g => 10 * 100 * 0.417 = 417
        assert calculate_gold_value(10, 100, 10) == pytest.approx(417.0)

    def test_9k_value(self):
        # 10g of 9K gold at 100 EGP/g => 10 * 100 * 0.375 = 375
        assert calculate_gold_value(10, 100, 9) == pytest.approx(375.0)

    def test_zero_weight(self):
        assert calculate_gold_value(0, 100, 21) == pytest.approx(0.0)

    def test_zero_price(self):
        assert calculate_gold_value(10, 0, 21) == pytest.approx(0.0)

    def test_negative_weight_raises(self):
        with pytest.raises(ValueError, match="weight_grams must be non-negative"):
            calculate_gold_value(-1, 100, 21)

    def test_negative_price_raises(self):
        with pytest.raises(ValueError, match="price_per_gram_24k must be non-negative"):
            calculate_gold_value(10, -100, 21)

    def test_invalid_karat_raises(self):
        with pytest.raises(ValueError, match="Unsupported karat"):
            calculate_gold_value(10, 100, 15)


class TestPricePerGram:
    """Tests for the price_per_gram function."""

    def test_price_per_gram_24k(self):
        assert price_per_gram(1000, 24) == pytest.approx(999.0)

    def test_price_per_gram_22k(self):
        assert price_per_gram(1000, 22) == pytest.approx(916.0)

    def test_price_per_gram_21k(self):
        assert price_per_gram(1000, 21) == pytest.approx(875.0)

    def test_price_per_gram_18k(self):
        assert price_per_gram(1000, 18) == pytest.approx(750.0)

    def test_price_per_gram_14k(self):
        assert price_per_gram(1000, 14) == pytest.approx(585.0)

    def test_price_per_gram_12k(self):
        assert price_per_gram(1000, 12) == pytest.approx(500.0)

    def test_price_per_gram_10k(self):
        assert price_per_gram(1000, 10) == pytest.approx(417.0)

    def test_price_per_gram_9k(self):
        assert price_per_gram(1000, 9) == pytest.approx(375.0)

    def test_negative_price_raises(self):
        with pytest.raises(ValueError, match="price_per_gram_24k must be non-negative"):
            price_per_gram(-1, 21)


class TestConvertWeightTo24kEquivalent:
    """Tests for the convert_weight_to_24k_equivalent function."""

    def test_24k_unchanged(self):
        assert convert_weight_to_24k_equivalent(10, 24) == pytest.approx(9.99)

    def test_21k_conversion(self):
        assert convert_weight_to_24k_equivalent(10, 21) == pytest.approx(8.75)

    def test_18k_conversion(self):
        assert convert_weight_to_24k_equivalent(10, 18) == pytest.approx(7.50)

    def test_14k_conversion(self):
        assert convert_weight_to_24k_equivalent(10, 14) == pytest.approx(5.85)

    def test_9k_conversion(self):
        assert convert_weight_to_24k_equivalent(10, 9) == pytest.approx(3.75)

    def test_zero_weight(self):
        assert convert_weight_to_24k_equivalent(0, 18) == pytest.approx(0.0)

    def test_negative_weight_raises(self):
        with pytest.raises(ValueError, match="weight_grams must be non-negative"):
            convert_weight_to_24k_equivalent(-5, 18)
