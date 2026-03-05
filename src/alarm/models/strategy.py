"""
Modèles de données pour les stratégies d'options
"""
from dataclasses import dataclass, field
from enum import Enum
from http import client
from typing import Optional
from datetime import datetime
import uuid
import re


def normalize_ticker(ticker: str) -> str:
    """
    Normalise un ticker Bloomberg pour garantir la cohérence.
    """
    if not ticker:
        return ""
    
    ticker = ticker.strip().upper()
    
    # Corriger les variantes de "COMDTY"
    # Remplacer COMDITY, COMDTY, CMDTY, etc. par COMDTY
    ticker = re.sub(r'\bCOMDITY\b', 'COMDTY', ticker, flags=re.IGNORECASE)
    ticker = re.sub(r'\bCOMODITY\b', 'COMDTY', ticker, flags=re.IGNORECASE)
    ticker = re.sub(r'\bCOMDTY\b', 'COMDTY', ticker, flags=re.IGNORECASE)
    
    # Normaliser les espaces multiples en un seul
    ticker = re.sub(r'\s+', ' ', ticker)
    
    return ticker


class Position(Enum):
    """Position sur une option"""
    LONG = "long"
    SHORT = "short"


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
    
    # Prix temps réel depuis Bloomberg
    last_price: Optional[float] = None
    bid: Optional[float] = None
    ask: Optional[float] = None
    mid: Optional[float] = None
    last_update: Optional[datetime] = None
    
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
    
    def get_price_contribution(self) -> Optional[float]:
        """
        Retourne la contribution au prix de la stratégie.
        Long = +prix, Short = -prix
        """
        price = self.mid if self.mid else self.last_price
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
            "quantity": self.quantity
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "OptionLeg":
        """Crée depuis un dictionnaire"""
        # Normaliser le ticker pour cohérence avec Bloomberg
        ticker = normalize_ticker(data.get("ticker", ""))
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            ticker=ticker,
            position=Position(data.get("position", "long")),
            quantity=data.get("quantity", 1)
        )


@dataclass 
class Strategy:
    """Représente une stratégie d'options (butterfly, condor, etc.)"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Nouvelle Stratégie"
    legs: list[OptionLeg] = field(default_factory=list)
    client : Optional[str] = None
    action : Optional[str] = None
    
    # Prix cible et condition
    target_price: Optional[float] = None
    target_condition: TargetCondition = TargetCondition.INFERIEUR  # Alarme si prix < ou > cible
    
    # Status
    status: StrategyStatus = StrategyStatus.EN_COURS
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    
    def add_leg(self, ticker: str = "", position: Position = Position.LONG, quantity: int = 1) -> OptionLeg:
        """Ajoute une jambe à la stratégie"""
        leg = OptionLeg(ticker=ticker, position=position, quantity=quantity)
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
