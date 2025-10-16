"""
Tests Unitaires - Module Bloomberg Refactorisé
===============================================
Tests pour valider la nouvelle architecture modulaire.

Exécution:
    pytest test_bloomberg_refactored.py -v

Auteur: BGC Trading Desk
Date: 2025-10-16
"""

import pytest
from datetime import date
from unittest.mock import Mock, patch

# Import des modules à tester
from models import OptionData, EuriborOptionData
from ticker_builder import (
    get_suffix,
    build_equity_option_ticker,
    build_euribor_option_ticker,
    build_option_ticker,
    parse_euribor_expiry_code,
    MONTH_CODES
)
from formatters import (
    format_option_summary,
    format_euribor_option,
    format_greeks_summary
)


# ========== Tests Models ==========

class TestOptionData:
    """Tests pour la classe OptionData"""
    
    def test_create_basic_option(self):
        """Test création option basique"""
        opt = OptionData(
            ticker="AAPL 12/20/24 C150 Equity",
            underlying="AAPL",
            option_type="CALL",
            strike=150.0,
            expiry=date(2024, 12, 20)
        )
        
        assert opt.ticker == "AAPL 12/20/24 C150 Equity"
        assert opt.underlying == "AAPL"
        assert opt.strike == 150.0
    
    def test_spread_calculation(self):
        """Test calcul du spread bid-ask"""
        opt = OptionData(
            ticker="TEST",
            underlying="TEST",
            option_type="CALL",
            strike=100.0,
            expiry=date(2024, 12, 20),
            bid=5.0,
            ask=5.20
        )
        
        # Utiliser pytest.approx pour gérer la précision des floats
        assert opt.spread == pytest.approx(0.20, abs=1e-9)
    
    def test_spread_none_when_missing_data(self):
        """Test spread None si bid/ask manquants"""
        opt = OptionData(
            ticker="TEST",
            underlying="TEST",
            option_type="CALL",
            strike=100.0,
            expiry=date(2024, 12, 20),
            bid=None,
            ask=5.20
        )
        
        assert opt.spread is None
    
    def test_is_liquid_with_volume(self):
        """Test liquidité avec volume"""
        opt = OptionData(
            ticker="TEST",
            underlying="TEST",
            option_type="CALL",
            strike=100.0,
            expiry=date(2024, 12, 20),
            volume=1000,
            bid=5.0,
            ask=5.10,
            mid=5.05
        )
        
        assert opt.is_liquid is True
    
    def test_is_illiquid_wide_spread(self):
        """Test illiquidité avec spread large"""
        opt = OptionData(
            ticker="TEST",
            underlying="TEST",
            option_type="CALL",
            strike=100.0,
            expiry=date(2024, 12, 20),
            volume=100,
            bid=5.0,
            ask=6.0,  # Spread = 1.0 = 19% du mid
            mid=5.5
        )
        
        assert opt.is_liquid is False


class TestEuriborOptionData:
    """Tests pour la classe EuriborOptionData"""
    
    def test_create_euribor_option(self):
        """Test création option EURIBOR"""
        opt = EuriborOptionData(
            ticker="ER H5 C97.50 Comdty",
            underlying="ER",
            option_type="CALL",
            strike=97.50,
            expiry=date(2025, 3, 15)
        )
        
        assert opt.ticker == "ER H5 C97.50 Comdty"
        assert opt.contract_size == 2500.0
    
    def test_implied_rate_calculation(self):
        """Test calcul du taux implicite"""
        opt = EuriborOptionData(
            ticker="ER H5 C97.50 Comdty",
            underlying="ER",
            option_type="CALL",
            strike=97.50,
            expiry=date(2025, 3, 15)
        )
        
        assert opt.implied_rate == 2.50
    
    def test_tick_value(self):
        """Test valeur du tick"""
        opt = EuriborOptionData(
            ticker="ER H5 C97.50 Comdty",
            underlying="ER",
            option_type="CALL",
            strike=97.50,
            expiry=date(2025, 3, 15)
        )
        
        assert opt.tick_value == 25.0  # 2500 × 0.01
    
    def test_payoff_call_in_the_money(self):
        """Test payoff CALL dans la monnaie"""
        opt = EuriborOptionData(
            ticker="ER H5 C97.50 Comdty",
            underlying="ER",
            option_type="CALL",
            strike=97.50,
            expiry=date(2025, 3, 15)
        )
        
        # Taux final = 2.25% → Future = 97.75
        # Intrinsic = max(0, 97.75 - 97.50) = 0.25
        # Payoff = 0.25 × 2500 = 625
        payoff = opt.payoff_at_rate(2.25)
        assert payoff == 625.0
    
    def test_payoff_call_out_of_the_money(self):
        """Test payoff CALL hors de la monnaie"""
        opt = EuriborOptionData(
            ticker="ER H5 C97.50 Comdty",
            underlying="ER",
            option_type="CALL",
            strike=97.50,
            expiry=date(2025, 3, 15)
        )
        
        # Taux final = 2.75% → Future = 97.25
        # Intrinsic = max(0, 97.25 - 97.50) = 0
        payoff = opt.payoff_at_rate(2.75)
        assert payoff == 0.0
    
    def test_payoff_put_in_the_money(self):
        """Test payoff PUT dans la monnaie"""
        opt = EuriborOptionData(
            ticker="ER H5 P97.50 Comdty",
            underlying="ER",
            option_type="PUT",
            strike=97.50,
            expiry=date(2025, 3, 15)
        )
        
        # Taux final = 2.75% → Future = 97.25
        # Intrinsic = max(0, 97.50 - 97.25) = 0.25
        # Payoff = 0.25 × 2500 = 625
        payoff = opt.payoff_at_rate(2.75)
        assert payoff == 625.0


# ========== Tests Ticker Builder ==========

class TestTickerBuilder:
    """Tests pour la construction de tickers"""
    
    def test_get_suffix_equity(self):
        """Test suffixe pour actions"""
        assert get_suffix("AAPL") == "Equity"
        assert get_suffix("MSFT") == "Equity"
        assert get_suffix("TSLA") == "Equity"
    
    def test_get_suffix_index(self):
        """Test suffixe pour indices"""
        assert get_suffix("SPX") == "Index"
        assert get_suffix("NDX") == "Index"
        assert get_suffix("RUT") == "Index"
    
    def test_get_suffix_euribor(self):
        """Test suffixe pour EURIBOR"""
        assert get_suffix("ER") == "Comdty"
        assert get_suffix("EURIBOR") == "Comdty"
    
    def test_build_equity_option_ticker(self):
        """Test construction ticker action"""
        ticker = build_equity_option_ticker(
            underlying="AAPL",
            expiry=date(2024, 12, 20),
            option_type="C",
            strike=150.0
        )
        
        assert ticker == "AAPL 12/20/24 C150 Equity"
    
    def test_build_equity_option_ticker_put(self):
        """Test construction ticker PUT"""
        ticker = build_equity_option_ticker(
            underlying="MSFT",
            expiry=date(2024, 12, 20),
            option_type="P",
            strike=300.5
        )
        
        assert ticker == "MSFT 12/20/24 P300.50 Equity"
    
    def test_build_index_option_ticker(self):
        """Test construction ticker indice"""
        ticker = build_equity_option_ticker(
            underlying="SPX",
            expiry=date(2024, 12, 20),
            option_type="CALL",
            strike=4500.0,
            suffix="Index"
        )
        
        assert ticker == "SPX 12/20/24 C4500 Index"
    
    def test_build_euribor_option_ticker_march(self):
        """Test construction ticker EURIBOR Mars"""
        ticker = build_euribor_option_ticker(
            expiry=date(2025, 3, 15),
            option_type="C",
            strike=97.50
        )
        
        assert ticker == "ER H5 C97.50 Comdty"
    
    def test_build_euribor_option_ticker_june(self):
        """Test construction ticker EURIBOR Juin"""
        ticker = build_euribor_option_ticker(
            expiry=date(2025, 6, 15),
            option_type="P",
            strike=98.00
        )
        
        assert ticker == "ER M5 P98.00 Comdty"
    
    def test_build_euribor_option_ticker_september(self):
        """Test construction ticker EURIBOR Septembre"""
        ticker = build_euribor_option_ticker(
            expiry=date(2025, 9, 15),
            option_type="C",
            strike=97.75
        )
        
        assert ticker == "ER U5 C97.75 Comdty"
    
    def test_build_euribor_option_ticker_december(self):
        """Test construction ticker EURIBOR Décembre"""
        ticker = build_euribor_option_ticker(
            expiry=date(2025, 12, 15),
            option_type="P",
            strike=98.25
        )
        
        assert ticker == "ER Z5 P98.25 Comdty"
    
    def test_build_option_ticker_auto_detect_equity(self):
        """Test détection automatique action"""
        ticker = build_option_ticker(
            underlying="AAPL",
            expiry=date(2024, 12, 20),
            option_type="C",
            strike=150.0
        )
        
        assert ticker == "AAPL 12/20/24 C150 Equity"
    
    def test_build_option_ticker_auto_detect_euribor(self):
        """Test détection automatique EURIBOR"""
        ticker = build_option_ticker(
            underlying="ER",
            expiry=date(2025, 3, 15),
            option_type="C",
            strike=97.50
        )
        
        assert ticker == "ER H5 C97.50 Comdty"
    
    def test_parse_euribor_expiry_code(self):
        """Test parsing code d'expiry EURIBOR"""
        assert parse_euribor_expiry_code("H5") == date(2025, 3, 15)
        assert parse_euribor_expiry_code("M5") == date(2025, 6, 15)
        assert parse_euribor_expiry_code("U5") == date(2025, 9, 15)
        assert parse_euribor_expiry_code("Z5") == date(2025, 12, 15)


# ========== Tests Formatters ==========

class TestFormatters:
    """Tests pour les fonctions de formatage"""
    
    def test_format_option_summary(self):
        """Test résumé d'option"""
        opt = OptionData(
            ticker="AAPL 12/20/24 C150 Equity",
            underlying="AAPL",
            option_type="CALL",
            strike=150.0,
            expiry=date(2024, 12, 20),
            last=5.20,
            delta=0.45,
            implied_volatility=25.3
        )
        
        summary = format_option_summary(opt)
        
        assert "AAPL" in summary
        assert "12/20/24" in summary
        assert "C150" in summary
        assert "5.20" in summary
        assert "0.45" in summary
        assert "25.3" in summary
    
    def test_format_euribor_option(self):
        """Test formatage option EURIBOR"""
        opt = EuriborOptionData(
            ticker="ER H5 C97.50 Comdty",
            underlying="ER",
            option_type="CALL",
            strike=97.50,
            expiry=date(2025, 3, 15),
            last=0.15,
            delta=0.35,
            implied_volatility=20.5
        )
        
        formatted = format_euribor_option(opt)
        
        assert "ER H5 C97.50 Comdty" in formatted
        assert "2.50%" in formatted  # Implied rate
        assert "€25.00" in formatted  # Tick value
    
    def test_format_greeks_summary(self):
        """Test résumé Greeks"""
        opt = OptionData(
            ticker="AAPL 12/20/24 C150 Equity",
            underlying="AAPL",
            option_type="CALL",
            strike=150.0,
            expiry=date(2024, 12, 20),
            delta=0.450,
            gamma=0.023,
            vega=0.180,
            theta=-0.052,
            rho=0.012
        )
        
        greeks = format_greeks_summary(opt)
        
        assert "Delta: 0.450" in greeks
        assert "45.0% probability" in greeks  # Delta * 100
        assert "Gamma: 0.023" in greeks
        assert "Vega: 0.180" in greeks
        assert "Theta: -0.052" in greeks
        assert "Rho: 0.012" in greeks


# ========== Tests d'intégration ==========

class TestIntegration:
    """Tests d'intégration du workflow complet"""
    
    def test_equity_option_workflow(self):
        """Test workflow complet pour option action"""
        # 1. Construire le ticker
        ticker = build_option_ticker("AAPL", date(2024, 12, 20), "C", 150.0)
        assert ticker == "AAPL 12/20/24 C150 Equity"
        
        # 2. Créer l'objet option
        opt = OptionData(
            ticker=ticker,
            underlying="AAPL",
            option_type="CALL",
            strike=150.0,
            expiry=date(2024, 12, 20),
            last=5.20,
            bid=5.10,
            ask=5.30,
            mid=5.20,
            volume=1000,  # Ajouter volume pour is_liquid
            delta=0.45,
            implied_volatility=25.3
        )
        
        # 3. Vérifier propriétés
        assert opt.spread == pytest.approx(0.20, abs=1e-9)
        assert opt.is_liquid is True
        
        # 4. Formater
        summary = format_option_summary(opt)
        assert "AAPL" in summary
    
    def test_euribor_option_workflow(self):
        """Test workflow complet pour option EURIBOR"""
        # 1. Construire le ticker
        ticker = build_euribor_option_ticker(date(2025, 3, 15), "C", 97.50)
        assert ticker == "ER H5 C97.50 Comdty"
        
        # 2. Créer l'objet option
        opt = EuriborOptionData(
            ticker=ticker,
            underlying="ER",
            option_type="CALL",
            strike=97.50,
            expiry=date(2025, 3, 15),
            last=0.15,
            delta=0.35,
            implied_volatility=20.5
        )
        
        # 3. Vérifier métriques EURIBOR
        assert opt.implied_rate == 2.50
        assert opt.tick_value == 25.0
        
        # 4. Calculer payoff
        payoff = opt.payoff_at_rate(2.25)
        assert payoff == 625.0
        
        # 5. Formater
        formatted = format_euribor_option(opt)
        assert "2.50%" in formatted


# ========== Exécution ==========

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
