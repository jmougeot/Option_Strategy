"""
Modèles de données pour les stratégies d'options
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from datetime import date, datetime
import math
import uuid

from bloomberg.config import (
    normalize_ticker,
    OPTION_TICKER_RE as _OPTION_TICKER_RE,
    OPTION_TICKER_DETAILS_RE as _OPTION_TICKER_DETAILS_RE,
    FUTURE_TICKER_RE as _FUTURE_TICKER_RE,
    MONTH_TO_NUMBER as _MONTH_TO_NUMBER,
    resolve_expiry_year as _resolve_expiry_year,
    third_wednesday as _third_wednesday,
)
from option.bachelier import Bachelier
from option.option_class import Position


def parse_leg_ticker(ticker: str) -> tuple[str, str, float]:
    """Normalise un ticker et en extrait underlying/strike si le format est reconnu."""
    normalized = normalize_ticker(ticker)
    match = _OPTION_TICKER_RE.match(normalized)
    if not match:
        return normalized, "", 0.0
    try:
        strike = float(match.group(2))
    except ValueError:
        strike = 0.0
    return normalized, match.group(1).upper(), strike


def _parse_option_ticker_details(ticker: str) -> Optional[tuple[bool, float, float]]:
    normalized = normalize_ticker(ticker)
    match = _OPTION_TICKER_DETAILS_RE.match(normalized)
    if not match:
        return None

    month_code = match.group(2).upper()
    month_number = _MONTH_TO_NUMBER.get(month_code)
    if month_number is None:
        return None

    try:
        expiry_year = _resolve_expiry_year(match.group(3))
        strike = float(match.group(5))
    except ValueError:
        return None

    expiry_date = _third_wednesday(expiry_year, month_number)
    time_to_expiry = max((expiry_date - date.today()).days, 1) / 365.0
    is_call = match.group(4).upper() == "C"
    return is_call, strike, time_to_expiry


class StrategyStatus(Enum):
    """Status d'une stratégie"""
    EN_COURS = "En cours"
    FAIT = "Fait"
    ANNULE = "Annulé"


class TargetCondition(Enum):
    """Condition de déclenchement de l'alarme"""
    INFERIEUR = "inferieur"  # Alarme si prix <= cible
    SUPERIEUR = "superieur"  # Alarme si prix >= cible


@dataclass
class OptionLeg:
    """Représente une jambe d'option dans une stratégie"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    ticker: str = ""  # ex: "SFRH6C 98.00 Comdty"
    position: Position = Position.LONG
    quantity: int = 1
    total_qty: Optional[int] = None
    underlying: str = ""
    strike: float = 0.0
    # Prix temps réel depuis Bloomberg
    last_price: Optional[float] = None
    bid: Optional[float] = None
    ask: Optional[float] = None
    mid: Optional[float] = None
    last_update: Optional[datetime] = None

    # Prix ajusté (block)
    adjusted_mid: Optional[float] = None

    # Greeks temps réel depuis Bloomberg
    delta: Optional[float] = None
    gamma: Optional[float] = None
    theta: Optional[float] = None
    implied_vol: Optional[float] = None

    @property
    def future_ticker(self) -> Optional[str]:
        """Ticker du future sous-jacent, dérivé du ticker option."""
        m = _FUTURE_TICKER_RE.match(normalize_ticker(self.ticker or ""))
        return f"{m.group(1).upper()} COMDTY" if m else None

    def update_price(self, last_price: float, bid: float, ask: float):
        """Met à jour les prix de l'option. Ignore les valeurs négatives (pas de donnée)."""
        if last_price is not None and last_price >= 0:
            self.last_price = last_price
        if bid is not None and bid >= 0:
            self.bid = bid
        if ask is not None and ask >= 0:
            self.ask = ask
        if self.bid is not None and self.ask is not None:
            self.mid = (self.bid + self.ask) / 2
        self.last_update = datetime.now()

    def _clear_market_analytics(self) -> None:
        self.delta = None
        self.gamma = None
        self.theta = None
        self.implied_vol = None

    def recalculate_market_analytics(self, forward_price: Optional[float]) -> None:
        """Recalcule IV, delta, gamma et theta via Bachelier à partir du prix marché."""
        market_price = self.mid if self.mid is not None and self.mid > 0 else self.last_price
        if forward_price is None or forward_price <= 0 or market_price is None or market_price <= 0:
            self._clear_market_analytics()
            return

        details = _parse_option_ticker_details(self.ticker or "")
        if details is None:
            self._clear_market_analytics()
            return

        is_call, ticker_strike, time_to_expiry = details
        strike = self.strike if self.strike > 0 else ticker_strike
        if strike <= 0 or time_to_expiry <= 0:
            self._clear_market_analytics()
            return

        implied_vol = Bachelier(
            forward_price,
            strike,
            0.0,
            time_to_expiry,
            is_call,
            market_price,
        ).implied_vol()

        if implied_vol <= 0 or not math.isfinite(implied_vol):
            self._clear_market_analytics()
            return

        model = Bachelier(forward_price, strike, implied_vol, time_to_expiry, is_call)
        self.delta = model.delta()
        self.gamma = model.gamma()
        self.theta = model.theta()
        self.implied_vol = implied_vol

    def get_price_contribution(self) -> Optional[float]:
        """
        Retourne la contribution au prix de la stratégie.
        Long = +prix, Short = -prix
        """
        price = self.mid if self.mid is not None else self.last_price
        if price is None:
            return None
        
        multiplier = 1 if self.position == Position.LONG else -1
        return price * multiplier * self.quantity
    
    def to_dict(self) -> dict:
        """Convertit en dictionnaire pour sauvegarde"""
        return {
            "id": self.id,
            "ticker": self.ticker,
            "position": self.position.value,
            "quantity": self.quantity,
            "total_qty": self.total_qty,
            "underlying": self.underlying,
            "strike": self.strike,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "OptionLeg":
        """Crée depuis un dictionnaire"""
        ticker, inferred_underlying, inferred_strike = parse_leg_ticker(data.get("ticker", ""))
        strike_raw = data.get("strike", 0.0)
        total_qty_raw = data.get("total_qty")
        try:
            strike = float(strike_raw) if strike_raw not in (None, "") else inferred_strike
        except (TypeError, ValueError):
            strike = inferred_strike

        try:
            total_qty = int(total_qty_raw) if total_qty_raw not in (None, "") else None
        except (TypeError, ValueError):
            total_qty = None

        return cls(
            id=data.get("id", str(uuid.uuid4())),
            ticker=ticker,
            position=Position(data.get("position", "long")),
            quantity=data.get("quantity", 1),
            total_qty=total_qty,
            underlying=data.get("underlying", "") or inferred_underlying,
            strike=strike,
        )


@dataclass 
class Strategy:
    """Représente une stratégie d'options (butterfly, condor, etc.)"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Nouvelle Stratégie"
    legs: list[OptionLeg] = field(default_factory=list)
    client : Optional[str] = None
    action : Optional[str] = None
    underlying : Optional[str] = None
    expiration : Optional[str] = None
    target_price: Optional[float] = None
    target_condition: TargetCondition = TargetCondition.INFERIEUR  # Alarme si prix < ou > cible
    status: StrategyStatus = StrategyStatus.EN_COURS
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    future_price: Optional[float] = None

    def add_leg(self, ticker: str = "", position: Position = Position.LONG, quantity: int = 1) -> OptionLeg:
        """Ajoute une jambe à la stratégie"""
        normalized_ticker, underlying, strike = parse_leg_ticker(ticker)
        leg = OptionLeg(
            ticker=normalized_ticker,
            position=position,
            quantity=quantity,
            underlying=underlying,
            strike=strike,
        )
        self.legs.append(leg)
        self.updated_at = datetime.now()
        return leg
    
    def remove_leg(self, leg_id: str) -> bool:
        """Supprime une jambe par son ID"""
        for i, leg in enumerate(self.legs):
            if leg.id == leg_id:
                self.legs.pop(i)
                self.updated_at = datetime.now()
                return True
        return False
    
    def get_leg(self, leg_id: str) -> Optional[OptionLeg]:
        """Retourne une jambe par son ID"""
        for leg in self.legs:
            if leg.id == leg_id:
                return leg
        return None
    
    def calculate_strategy_price(self) -> Optional[float]:
        """
        Calcule le prix de la stratégie en additionnant les contributions de chaque jambe.
        Retourne None si une jambe n'a pas de prix.
        """
        if not self.legs:
            return None
        
        total = 0.0
        for leg in self.legs:
            contribution = leg.get_price_contribution()
            if contribution is None:
                return None  # Prix incomplet
            total += contribution
        
        return total

    def recalculate_market_analytics(self) -> None:
        """Recalcule les grecques temps réel et l'IV de chaque leg via Bachelier."""
        for leg in self.legs:
            leg.recalculate_market_analytics(self.future_price)

    def get_total_delta(self) -> Optional[float]:
        """Delta agrégé de la stratégie (signé par position)."""
        vals = []
        for leg in self.legs:
            if leg.delta is not None:
                sign = 1 if leg.position == Position.LONG else -1
                vals.append(leg.delta * leg.quantity * sign)
        return sum(vals) if vals else None

    def get_total_gamma(self) -> Optional[float]:
        """Gamma agrégé de la stratégie (signé par position)."""
        vals = []
        for leg in self.legs:
            if leg.gamma is not None:
                sign = 1 if leg.position == Position.LONG else -1
                vals.append(leg.gamma * leg.quantity * sign)
        return sum(vals) if vals else None

    def get_total_theta(self) -> Optional[float]:
        """Theta agrégé de la stratégie (signé par position)."""
        vals = []
        for leg in self.legs:
            if leg.theta is not None:
                sign = 1 if leg.position == Position.LONG else -1
                vals.append(leg.theta * leg.quantity * sign)
        return sum(vals) if vals else None

    def get_average_ivol(self) -> Optional[float]:
        """Volatilité implicite moyenne des legs."""
        ivols = [leg.implied_vol for leg in self.legs if leg.implied_vol is not None]
        return sum(ivols) / len(ivols) if ivols else None

    def is_target_reached(self) -> Optional[bool]:
        """
        Vérifie si le prix a atteint la cible selon la condition.
        - INFERIEUR: alarme si prix <= cible
        - SUPERIEUR: alarme si prix >= cible
        Retourne None si pas de prix cible ou prix non disponible.
        """
        if self.target_price is None:
            return None
        
        current_price = self.calculate_strategy_price()
        if current_price is None:
            return None
        
        if self.target_condition == TargetCondition.INFERIEUR:
            return current_price <= self.target_price
        else:  # SUPERIEUR
            return current_price >= self.target_price
    
    def get_all_tickers(self) -> list[str]:
        """Retourne tous les tickers de la stratégie"""
        return [leg.ticker for leg in self.legs if leg.ticker]
    
    def to_dict(self) -> dict:
        """Convertit en dictionnaire pour sauvegarde"""
        return {
            "id": self.id,
            "name": self.name,
            "client": self.client,
            "action": self.action,
            "legs": [leg.to_dict() for leg in self.legs],
            "target_price": self.target_price,
            "target_condition": self.target_condition.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Strategy":
        """Crée depuis un dictionnaire"""
        condition = data.get("target_condition", "inferieur")
        strategy = cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", "Nouvelle Stratégie"),
            client=data.get("client"),
            action=data.get("action"),
            target_price=data.get("target_price"),
            target_condition=TargetCondition(condition) if condition else TargetCondition.INFERIEUR,
            status=StrategyStatus(data.get("status", "En cours"))
        )
        
        for leg_data in data.get("legs", []):
            strategy.legs.append(OptionLeg.from_dict(leg_data))
        
        if data.get("created_at"):
            strategy.created_at = datetime.fromisoformat(data["created_at"])
        
        return strategy
