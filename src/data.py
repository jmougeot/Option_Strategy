"""
Module Data - Gestion et Stockage des Données de Marché
========================================================
Ce module gère le stockage, la validation et la manipulation des données
récupérées depuis l'API PriceMonkey pour les stratégies d'options.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime
import json
import sqlite3
from pathlib import Path


@dataclass
class OptionData:
    """Données d'une option individuelle"""
    symbol: str
    strike: float
    option_type: str  # "call" ou "put"
    premium: float
    expiration_date: str
    underlying_price: float
    bid: Optional[float] = None
    ask: Optional[float] = None
    volume: Optional[int] = None
    open_interest: Optional[int] = None
    implied_volatility: Optional[float] = None
    delta: Optional[float] = None
    gamma: Optional[float] = None
    theta: Optional[float] = None
    vega: Optional[float] = None
    rho: Optional[float] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict:
        """Convertit en dictionnaire"""
        return {
            "symbol": self.symbol,
            "strike": self.strike,
            "option_type": self.option_type,
            "premium": self.premium,
            "expiration_date": self.expiration_date,
            "underlying_price": self.underlying_price,
            "bid": self.bid,
            "ask": self.ask,
            "volume": self.volume,
            "open_interest": self.open_interest,
            "implied_volatility": self.implied_volatility,
            "delta": self.delta,
            "gamma": self.gamma,
            "theta": self.theta,
            "vega": self.vega,
            "rho": self.rho,
            "timestamp": self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'OptionData':
        """Crée une instance depuis un dictionnaire"""
        return cls(**data)


@dataclass
class StrategyData:
    """Données d'une stratégie complète"""
    strategy_name: str
    symbol: str
    underlying_price: float
    expiration_date: str
    legs: List[Dict]  # Liste des jambes de la stratégie
    net_credit: float
    max_profit: float
    max_loss: float
    breakeven_points: List[float]
    probability_of_profit: Optional[float] = None
    expected_return: Optional[float] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict:
        """Convertit en dictionnaire"""
        return {
            "strategy_name": self.strategy_name,
            "symbol": self.symbol,
            "underlying_price": self.underlying_price,
            "expiration_date": self.expiration_date,
            "legs": self.legs,
            "net_credit": self.net_credit,
            "max_profit": self.max_profit,
            "max_loss": self.max_loss,
            "breakeven_points": self.breakeven_points,
            "probability_of_profit": self.probability_of_profit,
            "expected_return": self.expected_return,
            "timestamp": self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'StrategyData':
        """Crée une instance depuis un dictionnaire"""
        return cls(**data)


class DataManager:
    """Gestionnaire de données avec persistance"""
    
    def __init__(self, db_path: str = "options_strategies.db"):
        """
        Initialise le gestionnaire de données
        
        Args:
            db_path: Chemin vers la base de données SQLite
        """
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialise la base de données SQLite"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Table pour les options individuelles
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS options (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                strike REAL NOT NULL,
                option_type TEXT NOT NULL,
                premium REAL NOT NULL,
                expiration_date TEXT NOT NULL,
                underlying_price REAL NOT NULL,
                bid REAL,
                ask REAL,
                volume INTEGER,
                open_interest INTEGER,
                implied_volatility REAL,
                delta REAL,
                gamma REAL,
                theta REAL,
                vega REAL,
                rho REAL,
                timestamp TEXT NOT NULL,
                UNIQUE(symbol, strike, option_type, expiration_date, timestamp)
            )
        """)
        
        # Table pour les stratégies
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS strategies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_name TEXT NOT NULL,
                symbol TEXT NOT NULL,
                underlying_price REAL NOT NULL,
                expiration_date TEXT NOT NULL,
                legs TEXT NOT NULL,
                net_credit REAL NOT NULL,
                max_profit REAL NOT NULL,
                max_loss REAL NOT NULL,
                breakeven_points TEXT NOT NULL,
                probability_of_profit REAL,
                expected_return REAL,
                timestamp TEXT NOT NULL
            )
        """)
        
        conn.commit()
        conn.close()
    
    def save_option(self, option: OptionData):
        """
        Sauvegarde une option dans la base de données
        
        Args:
            option: Données de l'option à sauvegarder
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO options 
            (symbol, strike, option_type, premium, expiration_date, underlying_price,
             bid, ask, volume, open_interest, implied_volatility,
             delta, gamma, theta, vega, rho, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            option.symbol, option.strike, option.option_type, option.premium,
            option.expiration_date, option.underlying_price, option.bid, option.ask,
            option.volume, option.open_interest, option.implied_volatility,
            option.delta, option.gamma, option.theta, option.vega, option.rho,
            option.timestamp
        ))
        
        conn.commit()
        conn.close()
    
    def save_strategy(self, strategy: StrategyData):
        """
        Sauvegarde une stratégie dans la base de données
        
        Args:
            strategy: Données de la stratégie à sauvegarder
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO strategies 
            (strategy_name, symbol, underlying_price, expiration_date, legs,
             net_credit, max_profit, max_loss, breakeven_points,
             probability_of_profit, expected_return, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            strategy.strategy_name, strategy.symbol, strategy.underlying_price,
            strategy.expiration_date, json.dumps(strategy.legs), strategy.net_credit,
            strategy.max_profit, strategy.max_loss, json.dumps(strategy.breakeven_points),
            strategy.probability_of_profit, strategy.expected_return, strategy.timestamp
        ))
        
        conn.commit()
        conn.close()
    
    def get_latest_option(self, symbol: str, strike: float, 
                         option_type: str, expiration_date: str) -> Optional[OptionData]:
        """
        Récupère les données les plus récentes pour une option
        
        Args:
            symbol: Symbole du sous-jacent
            strike: Prix d'exercice
            option_type: Type d'option
            expiration_date: Date d'expiration
        
        Returns:
            OptionData ou None si non trouvé
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM options 
            WHERE symbol = ? AND strike = ? AND option_type = ? AND expiration_date = ?
            ORDER BY timestamp DESC LIMIT 1
        """, (symbol, strike, option_type, expiration_date))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return OptionData(
                symbol=row[1], strike=row[2], option_type=row[3],
                premium=row[4], expiration_date=row[5], underlying_price=row[6],
                bid=row[7], ask=row[8], volume=row[9], open_interest=row[10],
                implied_volatility=row[11], delta=row[12], gamma=row[13],
                theta=row[14], vega=row[15], rho=row[16], timestamp=row[17]
            )
        return None
    
    def get_strategies_by_symbol(self, symbol: str, limit: int = 10) -> List[StrategyData]:
        """
        Récupère les stratégies les plus récentes pour un symbole
        
        Args:
            symbol: Symbole du sous-jacent
            limit: Nombre maximum de résultats
        
        Returns:
            Liste de StrategyData
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM strategies 
            WHERE symbol = ?
            ORDER BY timestamp DESC LIMIT ?
        """, (symbol, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        strategies = []
        for row in rows:
            strategies.append(StrategyData(
                strategy_name=row[1], symbol=row[2], underlying_price=row[3],
                expiration_date=row[4], legs=json.loads(row[5]), net_credit=row[6],
                max_profit=row[7], max_loss=row[8], 
                breakeven_points=json.loads(row[9]),
                probability_of_profit=row[10], expected_return=row[11],
                timestamp=row[12]
            ))
        
        return strategies
    
    def export_to_json(self, output_file: str = "exported_data.json"):
        """
        Exporte toutes les données en JSON
        
        Args:
            output_file: Nom du fichier de sortie
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Récupérer toutes les options
        cursor.execute("SELECT * FROM options ORDER BY timestamp DESC")
        options_rows = cursor.fetchall()
        
        # Récupérer toutes les stratégies
        cursor.execute("SELECT * FROM strategies ORDER BY timestamp DESC")
        strategies_rows = cursor.fetchall()
        
        conn.close()
        
        # Formater les données
        data = {
            "options": [],
            "strategies": []
        }
        
        for row in options_rows:
            data["options"].append({
                "symbol": row[1], "strike": row[2], "option_type": row[3],
                "premium": row[4], "expiration_date": row[5], "underlying_price": row[6],
                "bid": row[7], "ask": row[8], "volume": row[9], "open_interest": row[10],
                "implied_volatility": row[11], "delta": row[12], "gamma": row[13],
                "theta": row[14], "vega": row[15], "rho": row[16], "timestamp": row[17]
            })
        
        for row in strategies_rows:
            data["strategies"].append({
                "strategy_name": row[1], "symbol": row[2], "underlying_price": row[3],
                "expiration_date": row[4], "legs": json.loads(row[5]), "net_credit": row[6],
                "max_profit": row[7], "max_loss": row[8],
                "breakeven_points": json.loads(row[9]),
                "probability_of_profit": row[10], "expected_return": row[11],
                "timestamp": row[12]
            })
        
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"Données exportées dans {output_file}")
    
    def clear_old_data(self, days: int = 30):
        """
        Supprime les données plus anciennes que N jours
        
        Args:
            days: Nombre de jours à conserver
        """
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM options WHERE timestamp < ?", (cutoff_date,))
        cursor.execute("DELETE FROM strategies WHERE timestamp < ?", (cutoff_date,))
        
        deleted_options = cursor.rowcount
        conn.commit()
        conn.close()
        
        print(f"Supprimé {deleted_options} entrées plus anciennes que {days} jours")


# =============================================================================
# FONCTIONS UTILITAIRES
# =============================================================================

def create_strategy_from_api_data(api_data: Dict, strategy_type: str) -> StrategyData:
    """
    Crée un objet StrategyData depuis les données API
    
    Args:
        api_data: Données brutes de l'API
        strategy_type: Type de stratégie
    
    Returns:
        StrategyData formaté
    """
    if strategy_type == "iron_condor":
        legs = [
            {"type": "long_put", "strike": api_data["long_put_strike"], 
             "premium": api_data["long_put_premium"]},
            {"type": "short_put", "strike": api_data["short_put_strike"], 
             "premium": api_data["short_put_premium"]},
            {"type": "short_call", "strike": api_data["short_call_strike"], 
             "premium": api_data["short_call_premium"]},
            {"type": "long_call", "strike": api_data["long_call_strike"], 
             "premium": api_data["long_call_premium"]}
        ]
        
        net_credit = api_data.get("net_credit", 0)
        max_profit = net_credit
        put_width = api_data["short_put_strike"] - api_data["long_put_strike"]
        call_width = api_data["long_call_strike"] - api_data["short_call_strike"]
        max_loss = max(put_width, call_width) - net_credit
        
        breakeven_points = [
            api_data["short_put_strike"] - net_credit,
            api_data["short_call_strike"] + net_credit
        ]
        
        return StrategyData(
            strategy_name="Iron Condor",
            symbol=api_data["symbol"],
            underlying_price=api_data["underlying_price"],
            expiration_date=api_data["expiration_date"],
            legs=legs,
            net_credit=net_credit,
            max_profit=max_profit,
            max_loss=max_loss,
            breakeven_points=breakeven_points
        )
    
    # Ajouter d'autres types de stratégies ici
    raise ValueError(f"Type de stratégie non supporté: {strategy_type}")


# =============================================================================
# EXEMPLE D'UTILISATION
# =============================================================================

if __name__ == "__main__":
    from datetime import timedelta
    
    # Initialiser le gestionnaire de données
    manager = DataManager("test_options.db")
    
    # Exemple 1: Sauvegarder une option
    print("=" * 70)
    print("EXEMPLE 1: Sauvegarde d'une option")
    print("=" * 70)
    
    option = OptionData(
        symbol="SPY",
        strike=450,
        option_type="put",
        premium=2.5,
        expiration_date="2025-11-15",
        underlying_price=470,
        bid=2.4,
        ask=2.6,
        volume=1000,
        open_interest=5000,
        implied_volatility=0.18,
        delta=-0.25,
        gamma=0.05,
        theta=-0.15,
        vega=0.30,
        rho=-0.10
    )
    
    manager.save_option(option)
    print("Option sauvegardée avec succès!")
    
    # Exemple 2: Récupérer une option
    print("\n" + "=" * 70)
    print("EXEMPLE 2: Récupération d'une option")
    print("=" * 70)
    
    retrieved = manager.get_latest_option("SPY", 450, "put", "2025-11-15")
    if retrieved:
        print(f"Option trouvée: {retrieved.symbol} ${retrieved.strike} {retrieved.option_type}")
        print(f"Prime: ${retrieved.premium}")
        print(f"Delta: {retrieved.delta}")
    
    # Exemple 3: Sauvegarder une stratégie
    print("\n" + "=" * 70)
    print("EXEMPLE 3: Sauvegarde d'une stratégie Iron Condor")
    print("=" * 70)
    
    strategy = StrategyData(
        strategy_name="Iron Condor",
        symbol="SPY",
        underlying_price=470,
        expiration_date="2025-11-15",
        legs=[
            {"type": "long_put", "strike": 440, "premium": 1.0},
            {"type": "short_put", "strike": 450, "premium": 2.5},
            {"type": "short_call", "strike": 490, "premium": 2.5},
            {"type": "long_call", "strike": 500, "premium": 1.0}
        ],
        net_credit=3.0,
        max_profit=3.0,
        max_loss=7.0,
        breakeven_points=[447.0, 493.0],
        probability_of_profit=0.65
    )
    
    manager.save_strategy(strategy)
    print("Stratégie sauvegardée avec succès!")
    
    # Exemple 4: Export JSON
    print("\n" + "=" * 70)
    print("EXEMPLE 4: Export des données en JSON")
    print("=" * 70)
    
    manager.export_to_json("exported_strategies.json")
