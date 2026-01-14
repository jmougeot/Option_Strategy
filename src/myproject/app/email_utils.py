import urllib.parse
from typing import Dict, Any, List, Optional
from datetime import datetime


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
    
    return "Scoring weights: " + " | ".join(parts) + "."


def generate_mailto_link(
    ui_params: Any,  # UIParams
    scenarios: List[Dict[str, float]],  # List of scenario dicts
    filters_data: Any,  # FilterData
    scoring_weights: Dict[str, float],
    best_strategy_name: Optional[str] = None,
    best_strategy_score: Optional[float] = None,
) -> str:
    """
    Generates a mailto link with a well-formatted, explanatory email body.
    Following the professional template for options strategy communication.
    """
    # Build a descriptive subject line
    underlying_name = ui_params.underlying if ui_params.underlying else "Options"
    date_str = datetime.now().strftime('%Y-%m-%d')
    subject = f"[Options Strategy] {underlying_name} - Scenarios, risk constraints & recommended strategy ({date_str})"
    
    # =========================================================================
    # BUILD EMAIL BODY
    # =========================================================================
    body = "Dear Team,\n\n"
    body += f"*** OPTIONS STRATEGY - {underlying_name} ***\n\n"
    
    # -------------------------------------------------------------------------
    # 1. CONTEXT & MARKET INTUITION
    # -------------------------------------------------------------------------
    body += "1. Context & Market Intuition\n"
    body += "   We ran an options strategy search using our 'strategy finder' "
    body += "(Gaussian framework: target at expiration + uncertainty around the target, weighted by scenarios). "
    body += "The idea is simple: maximize expected gain at expiration while keeping clean and explicit risk constraints "
    body += "(budget, convexity, residual exposure).\n\n"
    
    # -------------------------------------------------------------------------
    # 2. PARAMETERS (UNIVERSE SETUP)
    # -------------------------------------------------------------------------
    body += "2. Parameters (Universe Setup)\n\n"
    body += f"   * Underlying: {ui_params.underlying}\n"
    body += f"   * Expirations: {_format_months(ui_params.months)} {_format_years(ui_params.years)}\n"
    body += f"   * Strike grid: {ui_params.price_min:.4f} -> {ui_params.price_max:.4f} (step: {ui_params.price_step:.4f})\n"
    body += f"   * Complexity: up to {ui_params.max_legs} leg(s) per strategy\n"
    
    if ui_params.brut_code:
        body += f"   * Bloomberg instruments: {', '.join(ui_params.brut_code)}\n"
    else:
        body += "   * Bloomberg instruments: N/A (generated from strike grid)\n"
    body += "\n"
    
    # -------------------------------------------------------------------------
    # 3. MARKET VIEW (SCENARIOS)
    # -------------------------------------------------------------------------
    body += "3. Market View (Scenarios)\n"
    
    if scenarios:
        total_weight = sum(s.get('weight', 0) for s in scenarios)
        body += f"   We calibrate {len(scenarios)} scenario(s) (target price + uncertainty), with explicit weighting:\n\n"
        
        for i, scen in enumerate(scenarios, 1):
            price = scen.get('price', 0)
            std_l = scen.get('std', 0)
            std_r = scen.get('std_r', std_l)
            weight = scen.get('weight', 0)
            prob = (weight / total_weight * 100) if total_weight > 0 else 0
            
            if std_l == std_r:
                body += f"   * Scenario {i} ({prob:.0f}%): target {price:.4f}, uncertainty +/-{std_l:.4f}\n"
            else:
                body += f"   * Scenario {i} ({prob:.0f}%): target {price:.4f}, uncertainty -{std_l:.4f}/+{std_r:.4f}\n"
    else:
        body += "   No specific scenarios defined.\n"
    body += "\n"
    
    # -------------------------------------------------------------------------
    # 4. RISK CONSTRAINTS & EXPOSURES
    # -------------------------------------------------------------------------
    body += "4. Risk Constraints & Exposures\n\n"
    body += f"   * Max acceptable loss: {filters_data.max_loss:.2f}\n"
    body += f"   * Max premium to pay: {filters_data.max_premium:.2f}\n"
    body += f"   * Min premium to receive (if selling): {filters_data.min_premium_sell:.3f}\n"
    body += f"   * Residual exposure (open risk):\n"
    body += f"     {_describe_risk_exposure(filters_data.ouvert_gauche, filters_data.ouvert_droite)}\n"
    body += "     (Goal: avoid uncontrolled 'short tail' profiles and limit naked positions.)\n\n"
    
    # -------------------------------------------------------------------------
    # 5. SCORING METHODOLOGY
    # -------------------------------------------------------------------------
    body += "5. Scoring Methodology (What We Actually Optimize)\n"
    body += f"   {_describe_scoring_weights(scoring_weights)}\n\n"
    body += "   Notes:\n"
    body += "   - Weights reflect our current priority (expected P&L vs stability/neutrality).\n"
    body += "   - Scoring remains a function, not revealed truth: we keep a 'human' sanity check on the payoff and risk zones.\n\n"
    
    # -------------------------------------------------------------------------
    # 6. RESULT - RECOMMENDED STRATEGY
    # -------------------------------------------------------------------------
    body += "6. Result - Recommended Strategy\n\n"
    
    if best_strategy_name:
        body += f"   Best strategy identified: {best_strategy_name}\n"
        if best_strategy_score is not None:
            body += f"   Score: {best_strategy_score:.4f}\n"
        body += "\n"
        body += "   Quick rationale:\n"
        body += "   - Landing zone: centered on target price(s) from scenarios\n"
        body += "   - Payout: optimized for expected P&L under Gaussian mixture\n"
        body += "   - Main risk: see payoff diagram for tail exposure\n"
        body += "   - Package cost/credit: see strategy premium details\n\n"
        body += "   [Payoff diagram and details attached / screenshot]\n\n"
    else:
        body += "   No strategy computed yet. Run the comparison to get recommendations.\n\n"
    
    # -------------------------------------------------------------------------
    # CLOSING
    # -------------------------------------------------------------------------
    body += "-------------------------------------------\n"
    body += "Let me know if you would like:\n"
    body += "(a) a simpler version (<=3 legs),\n"
    body += "(b) stricter open risk constraint (0 = fully hedged),\n"
    body += "(c) or a 'roll-friendly' focus (priority on carry/roll).\n\n"
    body += "Best regards"
    
    # Encode only the subject (no email address)
    params = {
        "subject": subject,
        "body": body
    }
    query_string = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    
    return f"mailto:?{query_string}"

