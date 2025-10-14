"""
Générateur de Base de Données Complète
======================================
Génère des calls ET des puts pour permettre la construction de toutes les stratégies
"""

from datetime import datetime, timedelta
import json
import math
import random


def calculate_option_premium(spot_price: float, strike: float, days_to_expiry: int,
                             option_type: str, volatility: float = 0.20, 
                             risk_free_rate: float = 0.05) -> float:
    """Calcule la prime d'une option en utilisant Black-Scholes"""
    T = days_to_expiry / 365.0
    
    if T <= 0:
        if option_type == 'call':
            return max(0, spot_price - strike)
        else:
            return max(0, strike - spot_price)
    
    # Black-Scholes
    d1 = (math.log(spot_price / strike) + (risk_free_rate + 0.5 * volatility**2) * T) / (volatility * math.sqrt(T))
    d2 = d1 - volatility * math.sqrt(T)
    
    def norm_cdf(x):
        return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0
    
    if option_type == 'call':
        price = spot_price * norm_cdf(d1) - strike * math.exp(-risk_free_rate * T) * norm_cdf(d2)
    else:  # put
        price = strike * math.exp(-risk_free_rate * T) * norm_cdf(-d2) - spot_price * norm_cdf(-d1)
    
    return max(0.01, price)


def calculate_greeks(spot_price: float, strike: float, days_to_expiry: int,
                    option_type: str, volatility: float = 0.20, 
                    risk_free_rate: float = 0.05) -> dict:
    """Calcule les Greeks"""
    T = days_to_expiry / 365.0
    
    if T <= 0:
        if option_type == 'call':
            delta = 1.0 if spot_price > strike else 0.0
        else:
            delta = -1.0 if spot_price < strike else 0.0
        return {'delta': delta, 'gamma': 0.0, 'theta': 0.0, 'vega': 0.0, 'rho': 0.0}
    
    d1 = (math.log(spot_price / strike) + (risk_free_rate + 0.5 * volatility**2) * T) / (volatility * math.sqrt(T))
    d2 = d1 - volatility * math.sqrt(T)
    
    def norm_cdf(x):
        return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0
    
    def norm_pdf(x):
        return math.exp(-0.5 * x**2) / math.sqrt(2 * math.pi)
    
    # Delta
    if option_type == 'call':
        delta = norm_cdf(d1)
    else:  # put
        delta = norm_cdf(d1) - 1.0
    
    # Gamma (même pour call et put)
    gamma = norm_pdf(d1) / (spot_price * volatility * math.sqrt(T))
    
    # Theta (par jour)
    if option_type == 'call':
        theta = -(spot_price * norm_pdf(d1) * volatility) / (2 * math.sqrt(T)) - \
                risk_free_rate * strike * math.exp(-risk_free_rate * T) * norm_cdf(d2)
    else:  # put
        theta = -(spot_price * norm_pdf(d1) * volatility) / (2 * math.sqrt(T)) + \
                risk_free_rate * strike * math.exp(-risk_free_rate * T) * norm_cdf(-d2)
    theta = theta / 365.0
    
    # Vega (même pour call et put)
    vega = spot_price * math.sqrt(T) * norm_pdf(d1) / 100.0
    
    # Rho
    if option_type == 'call':
        rho = strike * T * math.exp(-risk_free_rate * T) * norm_cdf(d2) / 100.0
    else:  # put
        rho = -strike * T * math.exp(-risk_free_rate * T) * norm_cdf(-d2) / 100.0
    
    return {
        'delta': round(delta, 4),
        'gamma': round(gamma, 4),
        'theta': round(theta, 4),
        'vega': round(vega, 4),
        'rho': round(rho, 4)
    }


def generate_complete_options_data(
    symbol: str = "SPY",
    spot_price: float = 100.0,
    strike_min: float = 90.0,
    strike_max: float = 110.0,
    strike_step: float = 0.5,
    expiration_days: list = [7, 14, 21, 30, 45, 60],
    volatility_base: float = 0.20
):
    """
    Génère une base de données complète avec calls ET puts
    """
    
    print("="*80)
    print(f"GÉNÉRATION COMPLÈTE - CALLS & PUTS")
    print("="*80)
    print(f"Symbole: {symbol}")
    print(f"Prix spot: ${spot_price:.2f}")
    print(f"Strikes: ${strike_min:.2f} à ${strike_max:.2f} (pas de ${strike_step:.2f})")
    print(f"Expirations: {expiration_days} jours")
    print("="*80)
    
    # Générer les strikes
    strikes = []
    current_strike = strike_min
    while current_strike <= strike_max:
        strikes.append(round(current_strike, 2))
        current_strike += strike_step
    
    print(f"\nNombre de strikes: {len(strikes)}")
    print(f"Strikes: {strikes[:10]}..." if len(strikes) > 10 else f"Strikes: {strikes}")
    
    all_options = []
    
    for option_type in ['call', 'put']:
        print(f"\n{'='*80}")
        print(f"Génération des {option_type.upper()}S")
        print(f"{'='*80}")
        
        for days in expiration_days:
            expiration_date = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
            print(f"\nExpiration: {expiration_date} ({days} jours)")
            print("-"*80)
            
            for strike in strikes:
                # Varier la volatilité selon moneyness
                moneyness = strike / spot_price
                vol_adjustment = 0.03 * abs(1.0 - moneyness)  # Smile de volatilité
                volatility = volatility_base + vol_adjustment
                
                # Calculer la prime
                premium = calculate_option_premium(spot_price, strike, days, option_type, volatility)
                
                # Calculer les Greeks
                greeks = calculate_greeks(spot_price, strike, days, option_type, volatility)
                
                # Bid/Ask spread
                spread = premium * 0.02
                bid = max(0.01, premium - spread / 2)
                ask = premium + spread / 2
                
                # Volume et OI (plus élevé près de l'ATM)
                atm_factor = 1.0 - abs(strike - spot_price) / spot_price
                volume = int(random.uniform(100, 3000) * (atm_factor + 0.3))
                open_interest = int(random.uniform(500, 15000) * (atm_factor + 0.3))
                
                # Créer l'option
                option = {
                    'symbol': symbol,
                    'strike': strike,
                    'option_type': option_type,
                    'premium': round(premium, 2),
                    'expiration_date': expiration_date,
                    'underlying_price': spot_price,
                    'bid': round(bid, 2),
                    'ask': round(ask, 2),
                    'volume': volume,
                    'open_interest': open_interest,
                    'implied_volatility': round(volatility, 4),
                    'delta': greeks['delta'],
                    'gamma': greeks['gamma'],
                    'theta': greeks['theta'],
                    'vega': greeks['vega'],
                    'rho': greeks['rho'],
                    'timestamp': datetime.now().isoformat()
                }
                
                all_options.append(option)
                
                # Afficher quelques détails
                if strike in [spot_price - 5, spot_price, spot_price + 5]:
                    moneyness_label = "ITM" if (option_type == 'call' and strike < spot_price) or (option_type == 'put' and strike > spot_price) else \
                                     "ATM" if abs(strike - spot_price) < 0.5 else "OTM"
                    print(f"  Strike ${strike:6.2f} ({moneyness_label:3s}): "
                          f"Premium=${premium:5.2f}, Delta={greeks['delta']:6.3f}, "
                          f"IV={volatility:.2%}, Vol={volume:4d}")
    
    print(f"\n{'='*80}")
    print(f"✓ Génération terminée!")
    print(f"✓ Total d'options: {len(all_options)}")
    print(f"  - Calls: {len([o for o in all_options if o['option_type'] == 'call'])}")
    print(f"  - Puts: {len([o for o in all_options if o['option_type'] == 'put'])}")
    print("="*80)
    
    return all_options


def save_to_json(options: list, filename: str = "calls_export.json"):
    """Sauvegarde les options en JSON"""
    data = {
        "options": options,
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "total_options": len(options),
            "calls": len([o for o in options if o['option_type'] == 'call']),
            "puts": len([o for o in options if o['option_type'] == 'put']),
            "symbols": list(set(o['symbol'] for o in options)),
            "expirations": sorted(list(set(o['expiration_date'] for o in options)))
        }
    }
    
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"\n✓ Données sauvegardées dans {filename}")
    print(f"  Format: JSON")
    print(f"  Taille: {len(json.dumps(data))} caractères")


def display_summary(options: list):
    """Affiche un résumé des données"""
    print("\n" + "="*80)
    print("RÉSUMÉ DES DONNÉES")
    print("="*80)
    
    calls = [o for o in options if o['option_type'] == 'call']
    puts = [o for o in options if o['option_type'] == 'put']
    
    print(f"\nNombre total d'options: {len(options)}")
    print(f"  - Calls: {len(calls)}")
    print(f"  - Puts: {len(puts)}")
    
    expirations = sorted(set(o['expiration_date'] for o in options))
    print(f"\nExpirations ({len(expirations)}):")
    for exp in expirations:
        count = len([o for o in options if o['expiration_date'] == exp])
        print(f"  - {exp}: {count} options")
    
    strikes = sorted(set(o['strike'] for o in options))
    print(f"\nStrikes ({len(strikes)}):")
    print(f"  Range: ${min(strikes):.2f} - ${max(strikes):.2f}")
    print(f"  Premiers: {strikes[:10]}")
    
    # Exemples d'options ATM
    spot = options[0]['underlying_price']
    atm_options = [o for o in options if abs(o['strike'] - spot) < 1.0]
    
    if atm_options:
        print(f"\nExemples d'options ATM (strike ~${spot:.2f}):")
        for opt in atm_options[:4]:
            print(f"  {opt['option_type'].upper():4s} ${opt['strike']:.2f} "
                  f"exp:{opt['expiration_date']} premium:${opt['premium']:.2f} "
                  f"delta:{opt['delta']:.3f}")
    
    print("="*80)


if __name__ == "__main__":
    
    # Paramètres de génération
    print("\n🚀 DÉMARRAGE DE LA GÉNÉRATION\n")
    
    options = generate_complete_options_data(
        symbol="SPY",
        spot_price=100.0,
        strike_min=90.0,      # Range plus large pour toutes les stratégies
        strike_max=110.0,
        strike_step=0.5,      # Strikes tous les 0.5
        expiration_days=[7, 14, 21, 30, 45, 60, 90],  # Plus d'échéances
        volatility_base=0.18
    )
    
    # Sauvegarder
    save_to_json(options, "calls_export.json")
    
    # Afficher le résumé
    display_summary(options)
    
    print("\n✅ TERMINÉ! Le fichier calls_export.json est prêt pour test_comparison.py")
    print("\n💡 Prochaine étape: python3 test_comparison.py")
