# =========================================================================
# Class por créer des options depuis les données blommberg : calcul de roll 
# =========================================================================

import numpy as np
from datetime import date, datetime

from typing import Dict, Optional, Tuple, Any, List
from option.option_class import Option, PositionType
from bloomberg.ticker_builder import TickerBuilder
from bloomberg.refdata.premium import PremiumFetcher
from bloomberg.refdata.fetcher import extract_best_values
from bloomberg.refdata.extractor import create_option_from_bloomberg


TickerMeta = Dict[str, Any]
PremiumKey = Tuple[float, str, str, int]

class OptionProcessor:
    """Traite les données Bloomberg pour créer les objets Option."""
    
    def __init__(self, builder: TickerBuilder, fetcher: PremiumFetcher,
                 mixture: Tuple[np.ndarray, np.ndarray, float],
                 default_position: PositionType):
        self.builder = builder
        self.fetcher = fetcher
        self.mixture = mixture
        self.default_position: PositionType = default_position
    
    def _compute_roll(self, option: Option, meta: TickerMeta):
        """Calcule le roll pour une option."""
        if option.premium is None or option.premium == 0:
            return
        
        roll_expiries = self.builder.roll_expiries or []
        if not roll_expiries:
            return
        
        try:
            # Calculer le roll pour chaque échéance fournie
            rolls: List[float] = []
            rolls_detail: Dict[str, float] = {}
            
            for r_month, r_year in roll_expiries:
                roll_key: PremiumKey = (meta["strike"], meta["option_type"], r_month, r_year)
                roll_premium = self.fetcher.roll_premiums.get(roll_key)
                if roll_premium is not None:
                    roll_value = roll_premium - option.premium
                    rolls.append(roll_value)
                    # Label comme "H6", "M6", etc.
                    label = f"{r_month}{r_year}"
                    rolls_detail[label] = roll_value
            
            if rolls:
                # Roll = série complète dans l'ordre des expiries fournies par l'utilisateur
                option.roll = rolls
                option.rolls_detail = rolls_detail
                
        except Exception as e:
            print(f"  ⚠️ Erreur calcul roll: {e}")
    
    def process_all(self) -> List[Option]:
        """Traite toutes les options et retourne la liste."""
        options: List[Option] = []
        
        # Collecter les périodes uniques
        periods = sorted({(m["year"], m["month"]) for m in self.builder.main_metadata.values()})
        
        for year, month in periods:
            for ticker in self.builder.main_tickers:
                meta = self.builder.main_metadata[ticker]
                if meta["month"] != month or meta["year"] != year:
                    continue
                
                option = self._process_single(ticker, meta)
                if option:
                    options.append(option)
        
        return options
    
    def _process_single(self, ticker: str, meta: TickerMeta) -> Optional[Option]:
        """Traite une seule option."""
        try:
            raw_data = self.fetcher.main_data.get(ticker, {})
            has_warning = raw_data.get("_warning", False)
            
            if not has_warning:
                if not raw_data or all(v is None for v in raw_data.values()):
                    return None
            
            extracted = extract_best_values(raw_data)
            option = create_option_from_bloomberg(
                ticker=ticker,
                underlying=meta["underlying"],
                strike=meta["strike"],
                month=meta["month"],
                year=meta["year"],
                option_type_str=meta["option_type"],
                bloomberg_data=extracted,
                position=self.default_position,
                mixture=self.mixture,
                warning=has_warning,
            )
            
            self._compute_roll(option, meta)
            self._set_time_to_expiry(option, raw_data)

            if option.strike > 0:
                self._print_option(option)
                return option
        except Exception:
            pass
        return None
    
    @staticmethod
    def _set_time_to_expiry(option: Option, raw_data: Dict[str, Any]) -> None:
        """Calcule T à partir de LAST_TRADEABLE_DT ou OPT_EXPIRE_DT."""
        raw_dt = raw_data.get("LAST_TRADEABLE_DT") or raw_data.get("OPT_EXPIRE_DT")
        if not raw_dt:
            return
        text = str(raw_dt).strip()
        if "T" in text:
            text = text.split("T", 1)[0]
        if " " in text:
            text = text.split(" ", 1)[0]
        for fmt in ("%Y-%m-%d", "%m/%d/%y", "%m/%d/%Y"):
            try:
                d = datetime.strptime(text, fmt).date()
                option.time_to_expiry = max((d - date.today()).days, 1) / 365.0
                return
            except ValueError:
                continue

    @staticmethod
    def _print_option(option: Option):
        """Affiche le résumé d'une option."""
        sym = "C" if option.option_type == "call" else "P"
        roll = f", Roll0={option.roll[0]:.4f}" if option.roll else ""
        warn = " ⚠️" if not option.status else ""
        print(f"✓ {sym} {option.strike}: Premium={option.premium}, "
              f"Delta={option.delta}, IV={option.implied_volatility}{roll}{warn}")
