"""
Utility data structures for Options Strategy share_result module.
"""
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class StrategyEmailData:
    """Data structure for strategy details in email."""
    name: str
    score: float
    premium: float
    max_profit: float
    max_loss: float
    profit_at_target: float
    profit_at_target_pct: float
    average_pnl: Optional[float]
    sigma_pnl: Optional[float]
    total_delta: float
    total_gamma: float
    total_vega: float
    total_theta: float
    avg_implied_volatility: float
    breakeven_points: List[float]
    legs_description: List[str]  # e.g. ["Long Call 98.00", "Short Put 97.50"]
    diagram_path: Optional[str] = None  # Path to saved payoff diagram PNG
    top5_summary_path: Optional[str] = None  # Path to saved top 10 summary PNG


@dataclass
class EmailTemplateData:
    """Data structure for the new email template format."""
    underlying: str
    reference_price: str  # e.g. "96.745"
    
    # Criteria descriptions (free text)
    target_description: str  # e.g. "9633 target with a poss range between 9629 and 9636 for SFRZ6."
    tail_risk_description: str  # e.g. "(close to zero but not zero) of z6 below 9629..."
    max_risk_description: str  # e.g. "1x2 ps allowed (no 1x3), No 1x2 cs."
    strikes_screened_description: str  # e.g. "It's looking at all options between 9600 and 9700..."
    delta_description: str  # e.g. "limited from -50 to +50d"
    premium_max_description: str  # e.g. "4 TICKS"
    max_loss_description: str  # e.g. "100 ticks included premium below 96.29 / 25 ticks..."
    weighting_description: str  # e.g. "33 pct the best expected gain at exp, 33 pct..."
    
    max_legs: int  # e.g. 6
    
    # Best strategies list with label and description
    # e.g. [{"label": "Best strategy overall with the weighted score", "description": "SFRZ6 96.56/..."}]
    best_strategies: List[Dict[str, str]]


def _format_months(months: List[str]) -> str:
    """Convert Bloomberg month codes to readable names."""
    month_names = {
        "F": "January", "G": "February", "H": "March", "K": "April",
        "M": "June", "N": "July", "Q": "August", "U": "September",
        "V": "October", "X": "November", "Z": "December"
    }
    return ", ".join([month_names.get(m, m) for m in months])


def _format_years(years: List[int]) -> str:
    """Convert year codes to full years."""
    return ", ".join([str(2020 + y) for y in years])


def _describe_risk_exposure(ouvert_gauche: int, ouvert_droite: int) -> str:
    """Generate a sentence describing the risk exposure."""
    parts = []
    
    if ouvert_gauche == 0 and ouvert_droite == 0:
        return "Fully hedged on both sides (no open risk)."
    
    if ouvert_gauche > 0:
        parts.append(f"{ouvert_gauche} net short put(s) accepted (downside exposure)")
    elif ouvert_gauche < 0:
        parts.append(f"{abs(ouvert_gauche)} net long put(s) (downside protection)")
    
    if ouvert_droite > 0:
        parts.append(f"{ouvert_droite} net short call(s) accepted (upside exposure)")
    elif ouvert_droite < 0:
        parts.append(f"{abs(ouvert_droite)} net long call(s) (upside participation)")
    
    if parts:
        return " | ".join(parts)
    return "No specific exposure constraints."


def _describe_scoring_weights(scoring_weights: Dict[str, float]) -> str:
    """Generate a sentence describing the scoring focus."""
    active_weights = {k: v for k, v in scoring_weights.items() if v > 0}
    
    if not active_weights:
        return "No specific scoring criteria applied."
    
    weight_labels = {
        "average_pnl": "expected P&L",
        "sigma_pnl": "P&L volatility (stability)",
        "delta_neutral": "delta neutrality",
        "gamma_low": "low gamma (convexity control)",
        "vega_low": "low vega sensitivity",
        "theta_positive": "positive theta (time decay / carry)",
        "implied_vol_moderate": "moderate implied volatility"
    }
    
    # Sort by weight value
    sorted_weights = sorted(active_weights.items(), key=lambda x: x[1], reverse=True)
    
    parts = []
    for k, v in sorted_weights:
        label = weight_labels.get(k, k)
        parts.append(f"{label}: {v:.0%}")
    
    return " | ".join(parts)
