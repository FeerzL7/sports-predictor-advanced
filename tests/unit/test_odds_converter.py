# tests/unit/test_odds_converter.py

import pytest
from core.odds.utils.odds_converter import (
    american_to_decimal,
    decimal_to_american,
    implied_probability_from_decimal,
    implied_probability_from_american,
    normalize_odds_to_decimal,
    calculate_vig,
    is_positive_ev,
    expected_value
)


class TestOddsConversion:
    """Tests de conversión de odds."""
    
    def test_american_to_decimal_favorite(self):
        assert american_to_decimal(-150) == pytest.approx(1.67, abs=0.01)
        assert american_to_decimal(-200) == pytest.approx(1.50, abs=0.01)
        assert american_to_decimal(-110) == pytest.approx(1.91, abs=0.01)
    
    def test_american_to_decimal_underdog(self):
        assert american_to_decimal(+200) == pytest.approx(3.00, abs=0.01)
        assert american_to_decimal(+150) == pytest.approx(2.50, abs=0.01)
        assert american_to_decimal(+110) == pytest.approx(2.10, abs=0.01)
    
    def test_decimal_to_american_favorite(self):
        assert decimal_to_american(1.67) == -151  # Redondeo puede variar ±1
        assert decimal_to_american(1.50) == -200
        assert decimal_to_american(1.91) == -110
    
    def test_decimal_to_american_underdog(self):
        assert decimal_to_american(3.00) == 200
        assert decimal_to_american(2.50) == 150
        assert decimal_to_american(2.10) == 110


class TestImpliedProbability:
    """Tests de probabilidad implícita."""
    
    def test_decimal_implied_prob(self):
        assert implied_probability_from_decimal(2.00) == pytest.approx(0.50, abs=0.01)
        assert implied_probability_from_decimal(1.85) == pytest.approx(0.541, abs=0.01)
        assert implied_probability_from_decimal(3.00) == pytest.approx(0.333, abs=0.01)
    
    def test_american_implied_prob_favorite(self):
        assert implied_probability_from_american(-150) == pytest.approx(0.60, abs=0.01)
        assert implied_probability_from_american(-200) == pytest.approx(0.667, abs=0.01)
    
    def test_american_implied_prob_underdog(self):
        assert implied_probability_from_american(+200) == pytest.approx(0.333, abs=0.01)
        assert implied_probability_from_american(+150) == pytest.approx(0.40, abs=0.01)


class TestNormalization:
    """Tests de normalización automática."""
    
    def test_normalize_american(self):
        assert normalize_odds_to_decimal(-150) == pytest.approx(1.67, abs=0.01)
        assert normalize_odds_to_decimal(-140) == pytest.approx(1.71, abs=0.01)  # ✨ NUEVO
        assert normalize_odds_to_decimal(+200) == pytest.approx(3.00, abs=0.01)
        assert normalize_odds_to_decimal(+120) == pytest.approx(2.20, abs=0.01)  # ✨ NUEVO
    
    def test_normalize_decimal(self):
        assert normalize_odds_to_decimal(1.85) == 1.85
        assert normalize_odds_to_decimal(2.50) == 2.50
    
    def test_normalize_edge_cases(self):
        # Edge cases que deben funcionar
        assert normalize_odds_to_decimal(-105) == pytest.approx(1.95, abs=0.01)  # ✨ NUEVO
        assert normalize_odds_to_decimal(+105) == pytest.approx(2.05, abs=0.01)  # ✨ NUEVO

class TestVigAndEV:
    """Tests de vig y expected value."""
    
    def test_calculate_vig(self):
        # Odds de 1.95 / 1.95 → 2.6% vig
        vig = calculate_vig(1.95, 1.95)
        assert vig == pytest.approx(0.026, abs=0.01)
    
    def test_is_positive_ev(self):
        # model_prob=0.55, odds=2.0 → +EV
        assert is_positive_ev(0.55, 2.0) is True
        
        # model_prob=0.45, odds=2.0 → -EV
        assert is_positive_ev(0.45, 2.0) is False
    
    def test_expected_value(self):
        # model_prob=0.55, odds=2.0, stake=100
        # EV = (0.55 * 100) - (0.45 * 100) = +10
        ev = expected_value(0.55, 2.0, 100)
        assert ev == pytest.approx(10.0, abs=0.1)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])