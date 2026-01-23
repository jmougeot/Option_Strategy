import urllib.parse
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass
import os
import sys


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


def generate_html_email(
    ui_params: Any,
    scenarios: List[Dict[str, float]],
    filters_data: Any,
    scoring_weights: Dict[str, float],
    best_strategy: Optional[StrategyEmailData] = None,
) -> tuple:
    """
    Génère le sujet et le corps HTML d'un email professionnel.
    Basé sur le template BGC.
    
    Returns:
        tuple: (subject, html_body)
    """
    underlying = ui_params.underlying if ui_params.underlying else "Options"
    date_str = datetime.now().strftime('%Y-%m-%d')
    subject = f"[Options Strategy] {underlying} - Recommended strategy ({date_str})"
    
    # Calculer les infos des scénarios
    scenarios_text = ""
    if scenarios:
        total_weight = sum(s.get('weight', 0) for s in scenarios)
        for i, scen in enumerate(scenarios, 1):
            price = scen.get('price', 0)
            std_l = scen.get('std', 0)
            std_r = scen.get('std_r', std_l)
            weight = scen.get('weight', 0)
            prob = (weight / total_weight * 100) if total_weight > 0 else 0
            if std_l == std_r:
                scenarios_text += f"<li><strong>Target at expiration:</strong> {price:.4f} | <strong>Uncertainty band:</strong> ±{std_l:.4f} ({prob:.0f}% weight)</li>"
            else:
                scenarios_text += f"<li><strong>Target at expiration:</strong> {price:.4f} | <strong>Uncertainty band:</strong> -{std_l:.4f}/+{std_r:.4f} ({prob:.0f}% weight)</li>"
    
    # Scoring weights description
    scoring_desc = _describe_scoring_weights(scoring_weights)
    
    # Risk exposure description
    risk_exposure = _describe_risk_exposure(filters_data.ouvert_gauche, filters_data.ouvert_droite)
    
    # Strategy details
    strategy_name = best_strategy.name if best_strategy else "N/A"
    premium_str = ""
    max_loss_str = ""
    max_profit_str = ""
    avg_pnl_str = ""
    legs_html = ""
    
    if best_strategy:
        if best_strategy.premium >= 0:
            premium_str = f"{best_strategy.premium:.4f}"
        else:
            premium_str = f"credit ({best_strategy.premium:.4f})"
        
        max_loss_str = f"{best_strategy.max_loss:.4f}" if best_strategy.max_loss != float('inf') else "Unlimited"
        max_profit_str = f"{best_strategy.max_profit:.4f}"
        avg_pnl_str = f"{best_strategy.average_pnl:.4f}" if best_strategy.average_pnl else "N/A"
        
        for leg in best_strategy.legs_description:
            legs_html += f"<li>{leg}</li>"
    
    # Expiration formatting
    months_str = _format_months(ui_params.months) if ui_params.months else "N/A"
    years_str = _format_years(ui_params.years) if ui_params.years else ""
    
    html = f"""
<!DOCTYPE html>
<html>
<head>
<style>
body {{
    font-family: Arial, Helvetica, sans-serif;
    font-size: 10pt;
    line-height: 1.4;
    color: #333;
    max-width: 750px;
    margin: 0;
    padding: 10px;
}}
h2 {{
    color: #1a365d;
    border-bottom: 2px solid #2c5282;
    padding-bottom: 4px;
    margin-top: 12px;
    margin-bottom: 6px;
    font-size: 12pt;
}}
h3 {{
    color: #2c5282;
    margin-top: 8px;
    margin-bottom: 4px;
    font-size: 11pt;
}}
.intro {{
    font-size: 10pt;
    margin-bottom: 8px;
}}
.highlight {{
    background-color: #edf2f7;
    padding: 6px 10px;
    border-left: 3px solid #2c5282;
    margin: 6px 0;
}}
.strategy-name {{
    font-family: Consolas, 'Courier New', monospace;
    font-size: 10pt;
    font-weight: bold;
    color: #2c5282;
    background-color: #edf2f7;
    padding: 4px 8px;
    border-radius: 3px;
    display: inline-block;
    margin: 4px 0;
}}
.metrics-table {{
    border-collapse: collapse;
    margin: 6px 0;
}}
.metrics-table td {{
    padding: 2px 10px 2px 0;
    vertical-align: top;
    font-size: 10pt;
}}
.metrics-table td:first-child {{
    font-weight: bold;
    color: #4a5568;
}}
ul {{
    margin: 4px 0;
    padding-left: 18px;
}}
li {{
    margin: 2px 0;
}}
.section-divider {{
    border-top: 1px solid #e2e8f0;
    margin: 10px 0;
}}
.closing {{
    background-color: #f7fafc;
    padding: 8px;
    border-radius: 3px;
    margin-top: 12px;
}}
.image-container {{
    margin: 8px 0;
    text-align: center;
}}
.image-container img {{
    max-width: 600px;
    border: 1px solid #e2e8f0;
    border-radius: 3px;
}}
.image-caption {{
    font-style: italic;
    color: #718096;
    margin-top: 4px;
    font-size: 9pt;
}}
.signature {{
    margin-top: 15px;
    color: #4a5568;
}}
</style>
</head>
<body>

<p class="intro">Dear Team,</p>

<p class="intro">Following our recent discussion, we ran a full options strategy search on <strong>{underlying}</strong>, using our strategy finder framework to explicitly translate a macro view into a concrete, risk-controlled trade idea.</p>

<p>The starting point is simple: rather than selecting a predefined structure, we let the <strong>market view drive the strategy design</strong>. We encode the view as a probabilistic target at expiration, with an explicit uncertainty band, and use this distribution to evaluate expected outcomes across the entire payoff space.</p>

<div class="section-divider"></div>

<h2>📊 Market Context & Intuition</h2>

<p>The objective of this run was to maximize expected P&L at expiration while keeping the risk profile clean, bounded, and fully explicit — no hidden tails, no uncontrolled exposures. All strategies are evaluated under the same probabilistic framework, ensuring comparability and consistency.</p>

<div class="section-divider"></div>

<h2>🎯 Universe & Calibration</h2>

<table class="metrics-table">
<tr><td>Underlying:</td><td><strong>{underlying}</strong></td></tr>
<tr><td>Expiration:</td><td><strong>{months_str} {years_str}</strong></td></tr>
<tr><td>Strike range:</td><td><strong>{ui_params.price_min:.4f} – {ui_params.price_max:.4f}</strong> (step {ui_params.price_step:.4f})</td></tr>
<tr><td>Strategy complexity:</td><td><strong>up to {ui_params.max_legs} legs</strong></td></tr>
</table>

<p>We calibrated the following scenario(s), with explicit weighting:</p>
<ul>
{scenarios_text}
</ul>
<p><em>This calibration defines a Gaussian probability density, which becomes the core input of the strategy evaluation.</em></p>

<div class="section-divider"></div>

<h2>⚠️ Risk Discipline</h2>

<p>All candidate strategies are filtered under strict constraints:</p>
<ul>
<li>Maximum loss capped at <strong>{filters_data.max_loss_right:.2f}</strong></li>
<li>Maximum premium paid <strong>{filters_data.max_premium:.2f}</strong></li>
<li>Minimum premium received when selling <strong>{filters_data.min_premium_sell:.3f}</strong></li>
<li><strong>{risk_exposure}</strong></li>
</ul>
<p><em>This ensures that the ranking favors strategies that are not only attractive in expectation, but also operationally robust.</em></p>

<div class="section-divider"></div>

<h2>📈 What We Actually Optimize</h2>

<p>Each strategy is scored using a weighted function of its metrics. In this run, we prioritize:</p>
<div class="highlight">
<strong>{scoring_desc}</strong>
</div>
<p><em>Importantly, this score is not treated as an absolute truth, but as a <strong>ranking tool</strong>. Final selection remains subject to a human sanity check on payoff shape, risk zones, and execution realism.</em></p>

<div class="section-divider"></div>

<h2>🏆 Result – Recommended Strategy</h2>

<p>The top-ranked strategy emerging from the search is:</p>

<div class="strategy-name">{strategy_name}</div>

<h3>Key Characteristics</h3>
<table class="metrics-table">
<tr><td>Net premium:</td><td><strong>{premium_str}</strong></td></tr>
<tr><td>Maximum loss:</td><td><strong>{max_loss_str}</strong></td></tr>
<tr><td>Maximum profit:</td><td><strong>{max_profit_str}</strong></td></tr>
<tr><td>Expected P&L (Gaussian):</td><td><strong>{avg_pnl_str}</strong></td></tr>
</table>

<p><em>The payoff is centered on the calibrated landing zone, with an asymmetric profile optimized for expected value under the macro distribution.</em></p>

<!-- PAYOFF_DIAGRAM_PLACEHOLDER -->

<div class="section-divider"></div>

<h2>📋 Top 10 Ranking Summary</h2>

<p>Alternative structures with similar characteristics and slightly different trade-offs:</p>

<!-- TOP10_SUMMARY_PLACEHOLDER -->

<div class="section-divider"></div>

<h2>💡 Why This Matters</h2>

<p>This exercise illustrates the core philosophy of the framework:</p>
<ul>
<li>The <strong>algorithm exhaustively explores and ranks</strong> the strategy space</li>
<li>Probabilities replace scenarios</li>
<li>Human expertise intervenes only at the final selection stage</li>
</ul>
<p>The result is not "a strategy", but <strong>the best strategy given a clearly stated view and constraints</strong>.</p>

<div class="closing">
<p>Please let us know if you would like to:</p>
<ul>
<li>Simplify the structure (≤3 legs)</li>
<li>Tighten risk further (strict zero open exposure)</li>
<li>Refocus the ranking toward roll-down or carry efficiency</li>
</ul>
</div>

<p class="signature">
Best regards,<br>
<strong>BGC's team of rates derivatives</strong>
</p>

</body>
</html>
"""
    
    return subject, html


def generate_mailto_link(
    ui_params: Any,  # UIParams
    scenarios: List[Dict[str, float]],  # List of scenario dicts
    filters_data: Any,  # FilterData
    scoring_weights: Dict[str, float],
    best_strategy: Optional[StrategyEmailData] = None,
    top_strategies: Optional[List[StrategyEmailData]] = None,
) -> str:
    """
    Generates a mailto link with a well-formatted, explanatory email body.
    Following the professional template for options strategy communication.
    Includes detailed strategy information from overview and payoff tabs.
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
    body += f"   * Max acceptable loss: {filters_data.max_loss_right:.2f}\n"
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
    
    if best_strategy:
        body += f"   Best strategy identified: {best_strategy.name}\n"
        body += f"   Score: {best_strategy.score:.4f}\n\n"
        
        # Strategy composition (legs)
        body += "   Strategy Composition:\n"
        for leg in best_strategy.legs_description:
            body += f"      - {leg}\n"
        body += "\n"
        
        # Key metrics (from Overview tab)
        body += "   Key Metrics:\n"
        premium_str = f"{best_strategy.premium:.4f}" if best_strategy.premium >= 0 else f"{best_strategy.premium:.4f} (credit)"
        body += f"      - Premium: {premium_str}\n"
        body += f"      - Max Profit: {best_strategy.max_profit:.4f}\n"
        max_loss_str = f"{best_strategy.max_loss:.4f}" if best_strategy.max_loss != float('inf') else "Unlimited"
        body += f"      - Max Loss: {max_loss_str}\n"
        body += f"      - P&L at Target: {best_strategy.profit_at_target:.4f} ({best_strategy.profit_at_target_pct:.1f}% of max)\n"
        if best_strategy.average_pnl is not None:
            body += f"      - Expected P&L (Gaussian): {best_strategy.average_pnl:.4f}\n"
        if best_strategy.sigma_pnl is not None:
            body += f"      - P&L Std Dev: {best_strategy.sigma_pnl:.4f}\n"
        body += "\n"
        
        # Greeks
        body += "   Greeks:\n"
        body += f"      - Delta: {best_strategy.total_delta:.4f}\n"
        body += f"      - Gamma: {best_strategy.total_gamma:.4f}\n"
        body += f"      - Vega: {best_strategy.total_vega:.4f}\n"
        body += f"      - Theta: {best_strategy.total_theta:.4f}\n"
        body += f"      - Avg IV: {best_strategy.avg_implied_volatility:.2%}\n"
        body += "\n"
        
        # Breakeven points
        if best_strategy.breakeven_points:
            be_str = ", ".join([f"{bp:.4f}" for bp in best_strategy.breakeven_points])
            body += f"   Breakeven Point(s): {be_str}\n\n"
        
        # Quick rationale
        body += "   Quick Rationale:\n"
        body += "      - Landing zone: centered on target price(s) from scenarios\n"
        body += "      - Payout: optimized for expected P&L under Gaussian mixture\n"
        if best_strategy.max_loss == float('inf'):
            body += "      - Main risk: UNLIMITED loss potential on one side - monitor closely\n"
        else:
            body += f"      - Main risk: max loss capped at {best_strategy.max_loss:.4f}\n"
        body += "\n"
        
        # Payoff diagram reference
        body += "   Payoff Diagram:\n"
        if best_strategy.diagram_path:
            body += f"      File saved at: {best_strategy.diagram_path}\n"
            body += "      (Please attach this file to your email)\n\n"
        else:
            body += "      [Screenshot the P&L Diagram tab and attach to email]\n\n"
    else:
        body += "   No strategy computed yet. Run the comparison to get recommendations.\n\n"
    
    # -------------------------------------------------------------------------
    # 7. TOP 10 STRATEGIES (Payoff Tab Summary)
    # -------------------------------------------------------------------------
    if top_strategies and len(top_strategies) > 1:
        body += "7. Top 10 Strategies Summary (from P&L Diagram)\n\n"
        body += "   Rank | Strategy                     | Score   | Avg P&L  | Max Profit\n"
        body += "   -----|------------------------------|---------|----------|------------\n"
        for i, strat in enumerate(top_strategies[:10], 1):
            name_short = strat.name[:28] if len(strat.name) > 28 else strat.name.ljust(28)
            avg_pnl_str = f"{strat.average_pnl:.4f}" if strat.average_pnl else "N/A"
            body += f"   {i:4} | {name_short} | {strat.score:.4f}  | {avg_pnl_str:8} | {strat.max_profit:.4f}\n"
        body += "\n"
        
        # Top 10 summary image reference
        body += "   Top 10 Summary Image:\n"
        if top_strategies[0].top5_summary_path:
            body += f"      File saved at: {top_strategies[0].top5_summary_path}\n"
            body += "      (Please attach this file to your email)\n\n"
        else:
            body += "      [Export the summary table and attach to email]\n\n"
    
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


def open_outlook_with_html_email(
    ui_params: Any,
    scenarios: List[Dict[str, float]],
    filters_data: Any,
    scoring_weights: Dict[str, float],
    best_strategy: Optional[StrategyEmailData] = None,
    top_strategies: Optional[List[StrategyEmailData]] = None,
    images: List[str] = None,
    to: str = ""
) -> bool:
    """
    Ouvre Outlook avec un email HTML professionnel et les images intégrées.
    Utilise le template BGC avec styles.
    
    Args:
        ui_params: Paramètres UI
        scenarios: Scénarios
        filters_data: Filtres
        scoring_weights: Poids scoring
        best_strategy: Meilleure stratégie
        top_strategies: Top stratégies
        images: Liste des chemins d'images [payoff_diagram, top10_summary]
        to: Destinataire (optionnel)
    
    Returns:
        True si succès, False sinon
    """
    images = images or []
    
    print("\n" + "="*60)
    print("[Email DEBUG] open_outlook_with_html_email() appelée")
    print(f"[Email DEBUG] Nombre d'images reçues: {len(images)}")
    for i, img in enumerate(images):
        print(f"[Email DEBUG]   Image {i}: {img}")
        if img:
            print(f"[Email DEBUG]   Existe: {os.path.exists(img)}")
        else:
            print(f"[Email DEBUG]   ⚠ Chemin vide!")
    print("="*60 + "\n")
    
    if sys.platform != "win32":
        print("[Email] open_outlook_with_html_email n'est disponible que sur Windows")
        return False
    
    try:
        import pythoncom
        import win32com.client as win32
        
        # Initialiser COM pour ce thread (nécessaire avec Streamlit)
        pythoncom.CoInitialize()
        print("[Email DEBUG] COM initialisé")
        
        outlook = win32.Dispatch('Outlook.Application')
        print("[Email DEBUG] Outlook.Application créé")
        
        mail = outlook.CreateItem(0)  # 0 = olMailItem
        print("[Email DEBUG] Mail item créé")
        
        # Générer le HTML du mail
        subject, html_content = generate_html_email(
            ui_params, scenarios, filters_data, scoring_weights,
            best_strategy, top_strategies
        )
        
        if to:
            mail.To = to
        mail.Subject = subject
        
        # Filtrer les images valides
        valid_images = []
        for img_path in images:
            if img_path and os.path.exists(img_path):
                abs_path = os.path.abspath(img_path)
                valid_images.append(abs_path)
                print(f"[Email DEBUG] ✓ Image valide: {abs_path}")
            else:
                print(f"[Email DEBUG] ✗ Image invalide ou inexistante: {img_path}")
        
        print(f"[Email DEBUG] Images valides à intégrer: {len(valid_images)}")
        
        # Remplacer les placeholders par les images
        payoff_html = ""
        summary_html = ""
        
        if len(valid_images) > 0:
            # Première image = payoff diagram
            payoff_html = f'''
<div class="image-container">
<img src="cid:payoff_diagram" alt="Payoff Diagram" style="max-width:700px; border:1px solid #e2e8f0; border-radius:5px; box-shadow:0 2px 4px rgba(0,0,0,0.1);">
<p class="image-caption">Payoff diagram of the recommended strategy</p>
</div>
'''
        
        if len(valid_images) > 1:
            # Deuxième image = top 10 summary
            summary_html = f'''
<div class="image-container">
<img src="cid:top10_summary" alt="Top 10 Summary" style="max-width:700px; border:1px solid #e2e8f0; border-radius:5px; box-shadow:0 2px 4px rgba(0,0,0,0.1);">
<p class="image-caption">Top 10 strategies comparison</p>
</div>
'''
        
        # Insérer les images dans le HTML
        html_content = html_content.replace("<!-- PAYOFF_DIAGRAM_PLACEHOLDER -->", payoff_html)
        html_content = html_content.replace("<!-- TOP10_SUMMARY_PLACEHOLDER -->", summary_html)
        
        # Définir le HTMLBody
        mail.HTMLBody = html_content
        print("[Email DEBUG] HTMLBody défini")
        
        # Ajouter les images comme pièces jointes avec CID
        PR_ATTACH_CONTENT_ID = "http://schemas.microsoft.com/mapi/proptag/0x3712001F"
        
        cid_names = ["payoff_diagram", "top10_summary"]
        for i, img_path in enumerate(valid_images[:2]):
            cid = cid_names[i] if i < len(cid_names) else f"image{i}"
            try:
                attachment = mail.Attachments.Add(img_path)
                print(f"[Email DEBUG] Attachment ajouté: {img_path}")
                
                attachment.PropertyAccessor.SetProperty(PR_ATTACH_CONTENT_ID, cid)
                print(f"[Email DEBUG] CID défini: {cid}")
                
            except Exception as att_err:
                print(f"[Email DEBUG] ✗ Erreur ajout attachment: {att_err}")
        
        # Afficher l'email (non-modal)
        print("[Email DEBUG] Appel de mail.Display(False)...")
        mail.Display(False)
        print("[Email DEBUG] ✓ Email affiché avec succès")
        
        # Libérer COM
        pythoncom.CoUninitialize()
        
        return True
        
    except ImportError as ie:
        print(f"[Email] Module pywin32 non installé: {ie}")
        print("[Email] Installer avec: pip install pywin32")
        return False
    except Exception as e:
        print(f"[Email] Erreur Outlook: {e}")
        import traceback
        traceback.print_exc()
        try:
            pythoncom.CoUninitialize()
        except:
            pass
        return False


# Alias pour compatibilité
open_outlook_with_inline_images = open_outlook_with_html_email


def create_email_with_images(
    ui_params: Any,
    scenarios: List[Dict[str, float]],
    filters_data: Any,
    scoring_weights: Dict[str, float],
    best_strategy: Optional[StrategyEmailData] = None,
    top_strategies: Optional[List[StrategyEmailData]] = None,
    comparisons: Optional[List] = None,
    mixture: Optional[tuple] = None,
) -> bool:
    """
    Crée un email Outlook professionnel avec les images intégrées.
    Utilise le nouveau template HTML avec styles.
    
    Args:
        ui_params: Paramètres UI
        scenarios: Liste des scénarios
        filters_data: Données de filtrage
        scoring_weights: Poids du scoring
        best_strategy: Meilleure stratégie
        top_strategies: Top stratégies
        comparisons: Liste des StrategyComparison (pour générer les images)
        mixture: Tuple de mixture (pour le diagramme)
    
    Returns:
        True si l'email a été ouvert avec succès
    """
    print("\n" + "="*60)
    print("[Email DEBUG] create_email_with_images() appelée")
    print(f"[Email DEBUG] comparisons reçues: {comparisons is not None}")
    if comparisons:
        print(f"[Email DEBUG] Nombre de comparisons: {len(comparisons)}")
    print("="*60 + "\n")
    
    # Générer les images si on a les données
    images = []
    
    if comparisons:
        try:
            from myproject.app.image_saver import save_all_diagrams
            print("[Email DEBUG] image_saver importé")
            
            saved_images = save_all_diagrams(comparisons, mixture)
            print(f"[Email DEBUG] save_all_diagrams retourne: {saved_images}")
            
            if saved_images.get('payoff'):
                images.append(saved_images['payoff'])
                print(f"[Email DEBUG] Payoff ajouté: {saved_images['payoff']}")
                if best_strategy:
                    best_strategy.diagram_path = saved_images['payoff']
            else:
                print("[Email DEBUG] ⚠ Pas de 'payoff' dans saved_images")
            
            if saved_images.get('summary'):
                images.append(saved_images['summary'])
                print(f"[Email DEBUG] Summary ajouté: {saved_images['summary']}")
                if best_strategy:
                    best_strategy.top5_summary_path = saved_images['summary']
                if top_strategies and len(top_strategies) > 0:
                    top_strategies[0].top5_summary_path = saved_images['summary']
            else:
                print("[Email DEBUG] ⚠ Pas de 'summary' dans saved_images")
                    
        except Exception as e:
            print(f"[Email DEBUG] ✗ Erreur génération images: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("[Email DEBUG] ⚠ Pas de comparisons fourni - pas d'images à générer")
    
    print(f"[Email DEBUG] Liste finale d'images: {images}")
    
    # Ouvrir Outlook avec le nouveau template HTML et les images intégrées
    success = open_outlook_with_html_email(
        ui_params=ui_params,
        scenarios=scenarios,
        filters_data=filters_data,
        scoring_weights=scoring_weights,
        best_strategy=best_strategy,
        top_strategies=top_strategies,
        images=images
    )
    
    if not success:
        print("[Email] ❌ Impossible d'ouvrir Outlook.")
        if images:
            print("[Email] Images générées:")
            for img in images:
                print(f"   - {img}")
    
    return success


def generate_simple_pdf(
    ui_params: Any,
    scenarios: List[Dict[str, float]],
    filters_data: Any,
    scoring_weights: Dict[str, float],
    best_strategy: Optional[StrategyEmailData] = None,
    comparisons: Optional[List] = None,
    mixture: Optional[tuple] = None,
) -> Optional[bytes]:
    """
    Génère un PDF avec:
    - Page 1: Titre + Paramètres complets
    - Page 2: Payoff diagram (pleine page)
    - Page 3: Top 10 summary (pleine page)
    
    Returns:
        bytes du PDF ou None si erreur
    """
    try:
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table, TableStyle, PageBreak
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
        import io
    except ImportError:
        print("[PDF] reportlab n'est pas installé. Installer avec: pip install reportlab")
        return None
    
    # Générer les images si nécessaire
    images = []
    if comparisons:
        try:
            from myproject.app.image_saver import save_all_diagrams
            saved_images = save_all_diagrams(comparisons, mixture)
            if saved_images.get('payoff'):
                images.append(saved_images['payoff'])
            if saved_images.get('summary'):
                images.append(saved_images['summary'])
        except Exception as e:
            print(f"[PDF] Erreur génération images: {e}")
    
    # Créer le PDF en mémoire
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=landscape(A4),
        leftMargin=1.5*cm, 
        rightMargin=1.5*cm,
        topMargin=1.5*cm, 
        bottomMargin=1.5*cm
    )
    
    page_width = landscape(A4)[0] - 3*cm
    page_height = landscape(A4)[1] - 3*cm
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=22,
        textColor=colors.HexColor('#1a365d'),
        alignment=TA_CENTER,
        spaceAfter=15,
    )
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=14,
        textColor=colors.HexColor('#4a5568'),
        alignment=TA_CENTER,
        spaceAfter=8,
    )
    section_style = ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#2c5282'),
        spaceBefore=12,
        spaceAfter=6,
    )
    image_title_style = ParagraphStyle(
        'ImageTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#1a365d'),
        alignment=TA_CENTER,
        spaceAfter=10,
    )
    
    elements = []

    # =========================================================================
    # PAGE 1: PAYOFF DIAGRAM (pleine page)
    # =========================================================================
    if len(images) > 0 and os.path.exists(images[0]):
        elements.append(PageBreak())
        elements.append(Paragraph("Payoff Diagram - Best Strategy", image_title_style))
        elements.append(Spacer(1, 10))
        
        try:
            # Image en pleine page (avec marges)
            img_width = page_width * 0.95
            img_height = page_height * 0.85
            img = RLImage(images[0], width=img_width, height=img_height)
            elements.append(img)
        except Exception as e:
            print(f"[PDF] Erreur chargement image payoff: {e}")
    
    # =========================================================================
    # PAGE 2: TOP 10 SUMMARY (pleine page)
    # =========================================================================
    if len(images) > 1 and os.path.exists(images[1]):
        elements.append(PageBreak())
        elements.append(Paragraph("Top 10 Strategies Comparison", image_title_style))
        elements.append(Spacer(1, 10))
        
        try:
            # Image en pleine page (avec marges)
            img_width = page_width * 0.95
            img_height = page_height * 0.85
            img = RLImage(images[1], width=img_width, height=img_height)
            elements.append(img)
        except Exception as e:
            print(f"[PDF] Erreur chargement image summary: {e}")
    
    # =========================================================================
    # PAGE 3: TITRE + PARAMÈTRES
    # =========================================================================
    
    # Titre
    underlying = ui_params.underlying if ui_params.underlying else "Options"
    date_str = datetime.now().strftime('%Y-%m-%d %H:%M')
    elements.append(Paragraph(f"Options Strategy Report - {underlying}", title_style))
    elements.append(Paragraph(date_str, subtitle_style))
    
    # Stratégie recommandée
    if best_strategy:
        elements.append(Paragraph(f"<b>Recommended Strategy:</b> {best_strategy.name}", subtitle_style))
    
    elements.append(Spacer(1, 15))
    
    # Section: Universe Parameters
    elements.append(Paragraph("Universe Parameters", section_style))
    
    universe_data = [
        ["Parameter", "Value"],
        ["Underlying", underlying],
        ["Expirations", f"{_format_months(ui_params.months)} {_format_years(ui_params.years)}"],
        ["Strike Range", f"{ui_params.price_min:.4f} - {ui_params.price_max:.4f} (step: {ui_params.price_step:.4f})"],
        ["Max Legs", str(ui_params.max_legs)],
    ]
    
    if ui_params.brut_code:
        universe_data.append(["Bloomberg Codes", ", ".join(ui_params.brut_code[:5]) + ("..." if len(ui_params.brut_code) > 5 else "")])
    
    universe_table = Table(universe_data, colWidths=[6*cm, 14*cm])
    universe_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c5282')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('TOPPADDING', (0, 0), (-1, 0), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f7fafc')]),
    ]))
    elements.append(universe_table)
    
    elements.append(Spacer(1, 10))
    
    # Section: Risk Constraints
    elements.append(Paragraph("Risk Constraints", section_style))
    
    risk_data = [
        ["Constraint", "Value"],
        ["Max Loss (Left/Downside)", f"{filters_data.max_loss_left:.4f}"],
        ["Max Loss (Right/Upside)", f"{filters_data.max_loss_right:.4f}"],
        ["Max Premium Paid", f"{filters_data.max_premium:.4f}"],
        ["Min Premium Received (Sell)", f"{filters_data.min_premium_sell:.4f}"],
        ["Open Exposure Left (Puts)", f"{filters_data.ouvert_gauche}"],
        ["Open Exposure Right (Calls)", f"{filters_data.ouvert_droite}"],
        ["Delta Range", f"{filters_data.delta_min:.2f} to {filters_data.delta_max:.2f}"],
    ]
    
    risk_table = Table(risk_data, colWidths=[6*cm, 14*cm])
    risk_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#c53030')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('TOPPADDING', (0, 0), (-1, 0), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#fff5f5')]),
    ]))
    elements.append(risk_table)
    
    elements.append(Spacer(1, 10))
    
    # Section: Scenarios
    elements.append(Paragraph("Market Scenarios", section_style))
    
    scenario_data = [["Scenario", "Target Price", "Uncertainty (σ)", "Probability"]]
    if scenarios:
        total_weight = sum(s.get('weight', 0) for s in scenarios)
        for i, scen in enumerate(scenarios, 1):
            price = scen.get('price', 0)
            std_l = scen.get('std', 0)
            std_r = scen.get('std_r', std_l)
            weight = scen.get('weight', 0)
            prob = (weight / total_weight * 100) if total_weight > 0 else 0
            if std_l == std_r:
                std_str = f"±{std_l:.4f}"
            else:
                std_str = f"-{std_l:.4f} / +{std_r:.4f}"
            scenario_data.append([f"Scenario {i}", f"{price:.4f}", std_str, f"{prob:.1f}%"])
    
    scenario_table = Table(scenario_data, colWidths=[4*cm, 5*cm, 6*cm, 5*cm])
    scenario_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#38a169')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('TOPPADDING', (0, 0), (-1, 0), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0fff4')]),
    ]))
    elements.append(scenario_table)
    
    elements.append(Spacer(1, 10))
    
    # Section: Scoring Weights
    elements.append(Paragraph("Scoring Weights", section_style))
    
    scoring_data = [["Metric", "Weight"]]
    weight_labels = {
        "average_pnl": "Expected P&L",
        "sigma_pnl": "P&L Volatility (Stability)",
        "delta_neutral": "Delta Neutrality",
        "gamma_low": "Low Gamma",
        "vega_low": "Low Vega",
        "theta_positive": "Positive Theta (Carry)",
        "implied_vol_moderate": "Moderate Implied Vol"
    }
    for k, v in scoring_weights.items():
        if v > 0:
            label = weight_labels.get(k, k)
            scoring_data.append([label, f"{v:.0%}"])
    
    if len(scoring_data) > 1:
        scoring_table = Table(scoring_data, colWidths=[10*cm, 5*cm])
        scoring_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#805ad5')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('TOPPADDING', (0, 0), (-1, 0), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#faf5ff')]),
        ]))
        elements.append(scoring_table)
    

    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()


def create_pdf_report(
    ui_params: Any,
    scenarios: List[Dict[str, float]],
    filters_data: Any,
    scoring_weights: Dict[str, float],
    best_strategy: Optional[StrategyEmailData] = None,
    comparisons: Optional[List] = None,
    mixture: Optional[tuple] = None,
) -> Optional[bytes]:
    """
    Wrapper pour générer le PDF simple.
    Retourne les bytes du PDF pour téléchargement via Streamlit.
    """
    return generate_simple_pdf(
        ui_params=ui_params,
        scenarios=scenarios,
        filters_data=filters_data,
        scoring_weights=scoring_weights,
        best_strategy=best_strategy,
        comparisons=comparisons,
        mixture=mixture
    )
