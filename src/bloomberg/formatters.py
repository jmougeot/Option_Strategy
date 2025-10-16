"""
Bloomberg Data Formatters
=========================
Fonctions utilitaires pour afficher les données d'options de manière lisible.

Auteur: BGC Trading Desk
Date: 2025-10-16
"""

from typing import List
from models import OptionData, EuriborOptionData


def format_option_summary(option: OptionData) -> str:
    """
    Formate un résumé compact d'une option sur une ligne.
    
    Args:
        option: Données de l'option
    
    Returns:
        Chaîne formatée (ex: "AAPL 12/20/24 C150: Last=$5.20 Delta=0.45 IV=25.3%")
    
    Exemple:
        >>> opt = OptionData(...)
        >>> print(format_option_summary(opt))
        AAPL 12/20/24 C150: Last=$5.20 Delta=0.45 IV=25.3%
    """
    expiry_str = option.expiry.strftime("%m/%d/%y")
    opt_type = option.option_type[0]  # 'C' ou 'P'
    
    parts = [
        f"{option.underlying} {expiry_str} {opt_type}{option.strike}:"
    ]
    
    if option.last:
        parts.append(f"Last=${option.last:.2f}")
    
    if option.delta is not None:
        parts.append(f"Delta={option.delta:.3f}")
    
    if option.implied_volatility is not None:
        parts.append(f"IV={option.implied_volatility:.1f}%")
    
    return " ".join(parts)


def format_option_table(options: List[OptionData], title: str = "Options") -> str:
    """
    Formate une liste d'options en tableau lisible.
    
    Args:
        options: Liste des options à afficher
        title: Titre du tableau
    
    Returns:
        Tableau formaté en texte
    
    Exemple:
        >>> opts = [opt1, opt2, opt3]
        >>> print(format_option_table(opts, "AAPL Calls"))
    """
    if not options:
        return f"{title}: Aucune option trouvée"
    
    lines = [
        f"\n{'='*80}",
        f"{title}",
        f"{'='*80}",
        f"{'Expiry':<12} {'Strike':>8} {'Last':>8} {'Bid':>8} {'Ask':>8} {'Delta':>8} {'IV%':>8} {'Volume':>10}"
    ]
    
    for opt in options:
        expiry_str = opt.expiry.strftime("%Y-%m-%d")
        
        last = f"${opt.last:.2f}" if opt.last else "-"
        bid = f"${opt.bid:.2f}" if opt.bid else "-"
        ask = f"${opt.ask:.2f}" if opt.ask else "-"
        delta = f"{opt.delta:.3f}" if opt.delta is not None else "-"
        iv = f"{opt.implied_volatility:.1f}" if opt.implied_volatility is not None else "-"
        volume = f"{opt.volume:,}" if opt.volume else "-"
        
        lines.append(
            f"{expiry_str:<12} {opt.strike:>8.2f} {last:>8} {bid:>8} {ask:>8} {delta:>8} {iv:>8} {volume:>10}"
        )
    
    lines.append(f"{'='*80}\n")
    return "\n".join(lines)


def format_euribor_option(option: EuriborOptionData) -> str:
    """
    Formate spécifiquement une option EURIBOR avec les métriques de taux.
    
    Args:
        option: Données EURIBOR
    
    Returns:
        Résumé formaté avec taux implicite et tick value
    
    Exemple:
        >>> euribor_opt = EuriborOptionData(...)
        >>> print(format_euribor_option(euribor_opt))
        ER H5 C97.50 (Implied Rate: 2.50%)
        Last: $X.XX | Delta: 0.XXX | IV: XX.X%
        Tick Value: €25.00
    """
    lines = [
        f"{option.ticker} (Implied Rate: {option.implied_rate:.2f}%)",
    ]
    
    # Prix et Greeks
    price_info = []
    if option.last:
        price_info.append(f"Last: ${option.last:.2f}")
    if option.delta is not None:
        price_info.append(f"Delta: {option.delta:.3f}")
    if option.implied_volatility is not None:
        price_info.append(f"IV: {option.implied_volatility:.1f}%")
    
    if price_info:
        lines.append(" | ".join(price_info))
    
    # Métriques spécifiques EURIBOR
    lines.append(f"Tick Value: €{option.tick_value:.2f}")
    
    return "\n".join(lines)


def format_greeks_summary(option: OptionData) -> str:
    """
    Formate uniquement les Greeks d'une option.
    
    Args:
        option: Données de l'option
    
    Returns:
        Résumé des Greeks formaté
    
    Exemple:
        >>> print(format_greeks_summary(opt))
        Greeks for AAPL 12/20/24 C150:
          Delta: 0.450 (45% probability ITM)
          Gamma: 0.023 (delta sensitivity)
          Vega: 0.180 (volatility sensitivity)
          Theta: -0.052 (time decay per day)
          Rho: 0.012 (interest rate sensitivity)
    """
    expiry_str = option.expiry.strftime("%m/%d/%y")
    opt_type = option.option_type[0]
    
    lines = [
        f"Greeks for {option.underlying} {expiry_str} {opt_type}{option.strike}:"
    ]
    
    if option.delta is not None:
        prob_itm = abs(option.delta) * 100
        lines.append(f"  Delta: {option.delta:.3f} ({prob_itm:.1f}% probability ITM)")
    
    if option.gamma is not None:
        lines.append(f"  Gamma: {option.gamma:.3f} (delta sensitivity)")
    
    if option.vega is not None:
        lines.append(f"  Vega: {option.vega:.3f} (volatility sensitivity)")
    
    if option.theta is not None:
        lines.append(f"  Theta: {option.theta:.3f} (time decay per day)")
    
    if option.rho is not None:
        lines.append(f"  Rho: {option.rho:.3f} (interest rate sensitivity)")
    
    return "\n".join(lines)


def format_liquidity_check(option: OptionData) -> str:
    """
    Évalue et formate les métriques de liquidité d'une option.
    
    Args:
        option: Données de l'option
    
    Returns:
        Rapport de liquidité formaté
    
    Exemple:
        >>> print(format_liquidity_check(opt))
        Liquidity Check for AAPL 12/20/24 C150:
          Status: ✓ LIQUID
          Volume: 1,250 contracts
          Open Interest: 8,430 contracts
          Spread: $0.10 (2.0% of mid)
    """
    expiry_str = option.expiry.strftime("%m/%d/%y")
    opt_type = option.option_type[0]
    
    lines = [
        f"Liquidity Check for {option.underlying} {expiry_str} {opt_type}{option.strike}:"
    ]
    
    # Statut global
    status = "✓ LIQUID" if option.is_liquid else "✗ ILLIQUID"
    lines.append(f"  Status: {status}")
    
    # Métriques
    if option.volume is not None:
        lines.append(f"  Volume: {option.volume:,} contracts")
    
    if option.open_interest is not None:
        lines.append(f"  Open Interest: {option.open_interest:,} contracts")
    
    if option.spread is not None and option.mid is not None:
        spread_pct = (option.spread / option.mid) * 100
        lines.append(f"  Spread: ${option.spread:.2f} ({spread_pct:.1f}% of mid)")
    
    return "\n".join(lines)


def format_term_structure(options: List[OptionData], metric: str = "implied_volatility") -> str:
    """
    Formate la structure de terme (term structure) d'une métrique.
    
    Utile pour analyser comment une métrique (IV, delta, etc.) évolue
    selon les dates d'expiration.
    
    Args:
        options: Liste d'options avec différentes expiries (même strike)
        metric: Attribut à afficher ("implied_volatility", "delta", etc.)
    
    Returns:
        Tableau de structure de terme formaté
    
    Exemple:
        >>> chain = fetcher.get_options_by_strike("AAPL", 150, "C")
        >>> print(format_term_structure(chain, "implied_volatility"))
        
        Term Structure: implied_volatility
        ==================================
        2024-12-20: 25.3%
        2025-01-17: 26.8%
        2025-02-21: 27.2%
    """
    if not options:
        return f"Term Structure: No data"
    
    # Trier par date d'expiration
    sorted_opts = sorted(options, key=lambda o: o.expiry)
    
    lines = [
        f"\nTerm Structure: {metric}",
        "=" * 50
    ]
    
    for opt in sorted_opts:
        expiry_str = opt.expiry.strftime("%Y-%m-%d")
        value = getattr(opt, metric, None)
        
        if value is not None:
            # Formater selon le type de métrique
            if metric == "implied_volatility":
                value_str = f"{value:.1f}%"
            elif metric in ["delta", "gamma", "vega", "theta", "rho"]:
                value_str = f"{value:.3f}"
            else:
                value_str = f"{value:.2f}"
            
            lines.append(f"{expiry_str}: {value_str}")
    
    lines.append("=" * 50 + "\n")
    return "\n".join(lines)


if __name__ == "__main__":
    # Tests avec données fictives
    from datetime import date
    
    test_opt = OptionData(
        ticker="AAPL 12/20/24 C150 Equity",
        underlying="AAPL",
        option_type="CALL",
        strike=150.0,
        expiry=date(2024, 12, 20),
        last=5.20,
        bid=5.10,
        ask=5.30,
        mid=5.20,
        volume=1250,
        open_interest=8430,
        delta=0.450,
        gamma=0.023,
        vega=0.180,
        theta=-0.052,
        rho=0.012,
        implied_volatility=25.3
    )
    
    print(format_option_summary(test_opt))
    print()
    print(format_greeks_summary(test_opt))
    print()
    print(format_liquidity_check(test_opt))
