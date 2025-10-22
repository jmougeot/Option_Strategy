"""
Naming des Stratégies d'Options
================================
Module dédié à la génération automatique des noms de stratégies
en fonction des caractéristiques des options.

Reconnaît les patterns courants :
- Spreads (bull/bear, call/put)
- Straddles et Strangles
- Butterflies
- Condors (call, put, iron)
"""

from typing import List
from myproject.option.option_class import Option


def generate_strategy_name(options: List[Option]) -> str:
    """
    Génère un nom descriptif pour une stratégie d'options.
    
    Reconnaît automatiquement les patterns courants et génère un nom approprié.
    Si le pattern n'est pas reconnu, génère un nom générique descriptif.
    
    Args:
        options: Liste d'options constituant la stratégie
        
    Returns:
        Nom de la stratégie (ex: "LongStraddle 97.00", "IronCondor 95/96/98/99")
    
    Exemples:
        >>> call = Option(option_type='call', strike=100, position='long', premium=2.5)
        >>> generate_strategy_name([call])
        'Long Call 100.00'
        
        >>> call1 = Option(option_type='call', strike=95, position='long', premium=3.0)
        >>> call2 = Option(option_type='call', strike=100, position='short', premium=2.0)
        >>> generate_strategy_name([call1, call2])
        'BullCallSpread 95.00/100.00'
    """
    if not options:
        return "EmptyStrategy"
    
    n_legs = len(options)
    
    # Extraire les informations de base
    calls = [o for o in options if o.option_type == 'call']
    puts = [o for o in options if o.option_type == 'put']
    longs = [o for o in options if o.position == 'long']
    shorts = [o for o in options if o.position == 'short']
    
    # Récupérer les strikes uniques triés
    strikes = sorted(set(o.strike for o in options))
    strikes_str = '/'.join([f"{s:.2f}" for s in strikes])
    
    # ============================================================================
    # STRATÉGIES À 1 LEG
    # ============================================================================
    if n_legs == 1:
        opt = options[0]
        position_name = 'Long' if opt.position == 'long' else 'Short'
        type_name = opt.option_type.capitalize()
        return f"{position_name} {type_name} {opt.strike:.2f}"
    
    # ============================================================================
    # STRATÉGIES À 2 LEGS
    # ============================================================================
    elif n_legs == 2:
        # CALL SPREADS
        if len(calls) == 2 and len(strikes) == 2:
            if len(longs) == 1 and len(shorts) == 1:
                # Bull Call Spread : Long lower strike, Short higher strike
                long_strike = longs[0].strike
                short_strike = shorts[0].strike
                if long_strike < short_strike:
                    return f"BullCallSpread {strikes_str}"
                else:
                    return f"BearCallSpread {strikes_str}"
        
        # PUT SPREADS
        elif len(puts) == 2 and len(strikes) == 2:
            if len(longs) == 1 and len(shorts) == 1:
                # Bull Put Spread : Short higher strike, Long lower strike
                long_strike = longs[0].strike
                short_strike = shorts[0].strike
                if long_strike < short_strike:
                    return f"BullPutSpread {strikes_str}"
                else:
                    return f"BearPutSpread {strikes_str}"
        
        # STRADDLE (même strike)
        elif len(calls) == 1 and len(puts) == 1:
            if len(strikes) == 1:
                position_name = 'Long' if len(longs) == 2 else 'Short'
                return f"{position_name}Straddle {strikes[0]:.2f}"
            
            # STRANGLE (strikes différents)
            else:
                position_name = 'Long' if len(longs) == 2 else 'Short'
                return f"{position_name}Strangle {strikes_str}"
        
        # NOM GÉNÉRIQUE POUR 2 LEGS
        return f"2Leg_{len(calls)}C{len(puts)}P_{strikes_str}"
    
    # ============================================================================
    # STRATÉGIES À 3 LEGS
    # ============================================================================
    elif n_legs == 3:
        if len(strikes) == 3:
            # CALL BUTTERFLY
            if len(calls) == 3:
                # Pattern : 1 long - 2 short - 1 long aux strikes extrêmes
                if _is_butterfly_pattern(options):
                    return f"CallButterfly {strikes_str}"
            
            # PUT BUTTERFLY
            elif len(puts) == 3:
                if _is_butterfly_pattern(options):
                    return f"PutButterfly {strikes_str}"
        
        # NOM GÉNÉRIQUE POUR 3 LEGS
        return f"3Leg_{len(calls)}C{len(puts)}P_{strikes_str}"
    
    # ============================================================================
    # STRATÉGIES À 4 LEGS
    # ============================================================================
    elif n_legs == 4:
        if len(strikes) == 4:
            # CALL CONDOR
            if len(calls) == 4:
                if _is_condor_pattern(options):
                    return f"CallCondor {strikes_str}"
            
            # PUT CONDOR
            elif len(puts) == 4:
                if _is_condor_pattern(options):
                    return f"PutCondor {strikes_str}"
            
            # IRON CONDOR (2 calls + 2 puts)
            elif len(calls) == 2 and len(puts) == 2:
                if _is_iron_condor_pattern(options):
                    return f"IronCondor {strikes_str}"
            
            # IRON BUTTERFLY (spécial : strikes centraux identiques)
            elif len(calls) == 2 and len(puts) == 2 and len(strikes) == 3:
                return f"IronButterfly {strikes_str}"
        
        # NOM GÉNÉRIQUE POUR 4 LEGS
        return f"4Leg_{len(calls)}C{len(puts)}P_{strikes_str}"
    
    # ============================================================================
    # NOM GÉNÉRIQUE POUR > 4 LEGS
    # ============================================================================
    return f"{n_legs}Leg_{len(calls)}C{len(puts)}P_{strikes_str}"


# ============================================================================
# FONCTIONS AUXILIAIRES DE RECONNAISSANCE DE PATTERNS
# ============================================================================

def _is_butterfly_pattern(options: List[Option]) -> bool:
    """
    Vérifie si les options forment un pattern butterfly valide.
    
    Pattern attendu : 1 long (strike bas) - 2 short (strike milieu) - 1 long (strike haut)
    ou l'inverse (short-long-short)
    
    Args:
        options: Liste de 3 options avec 3 strikes différents
        
    Returns:
        True si c'est un butterfly valide
    """
    if len(options) != 3:
        return False
    
    # Trier par strike
    sorted_opts = sorted(options, key=lambda o: o.strike)
    
    # Pattern 1 : Long-Short-Long (butterfly classique)
    if (sorted_opts[0].position == 'long' and 
        sorted_opts[1].position == 'short' and 
        sorted_opts[2].position == 'long'):
        return True
    
    # Pattern 2 : Short-Long-Short (reverse butterfly)
    if (sorted_opts[0].position == 'short' and 
        sorted_opts[1].position == 'long' and 
        sorted_opts[2].position == 'short'):
        return True
    
    return False


def _is_condor_pattern(options: List[Option]) -> bool:
    """
    Vérifie si les options forment un pattern condor valide.
    
    Pattern attendu : Long-Short-Short-Long (strikes croissants)
    ou Short-Long-Long-Short
    
    Args:
        options: Liste de 4 options avec 4 strikes différents
        
    Returns:
        True si c'est un condor valide
    """
    if len(options) != 4:
        return False
    
    # Trier par strike
    sorted_opts = sorted(options, key=lambda o: o.strike)
    
    # Pattern 1 : Long-Short-Short-Long (condor classique)
    if (sorted_opts[0].position == 'long' and 
        sorted_opts[1].position == 'short' and 
        sorted_opts[2].position == 'short' and 
        sorted_opts[3].position == 'long'):
        return True
    
    # Pattern 2 : Short-Long-Long-Short (reverse condor)
    if (sorted_opts[0].position == 'short' and 
        sorted_opts[1].position == 'long' and 
        sorted_opts[2].position == 'long' and 
        sorted_opts[3].position == 'short'):
        return True
    
    return False


def _is_iron_condor_pattern(options: List[Option]) -> bool:
    """
    Vérifie si les options forment un iron condor valide.
    
    Pattern attendu :
    - 2 puts : Long put (strike bas) + Short put (strike médian bas)
    - 2 calls : Short call (strike médian haut) + Long call (strike haut)
    
    Args:
        options: Liste de 4 options (2 calls + 2 puts)
        
    Returns:
        True si c'est un iron condor valide
    """
    if len(options) != 4:
        return False
    
    calls = sorted([o for o in options if o.option_type == 'call'], key=lambda o: o.strike)
    puts = sorted([o for o in options if o.option_type == 'put'], key=lambda o: o.strike)
    
    if len(calls) != 2 or len(puts) != 2:
        return False
    
    # Vérifier le pattern des puts : Long (bas) - Short (haut)
    if not (puts[0].position == 'long' and puts[1].position == 'short'):
        return False
    
    # Vérifier le pattern des calls : Short (bas) - Long (haut)
    if not (calls[0].position == 'short' and calls[1].position == 'long'):
        return False
    
    # Vérifier que les strikes sont dans le bon ordre
    if not (puts[1].strike < calls[0].strike):
        return False
    
    return True


# ============================================================================
# FONCTIONS SUPPLÉMENTAIRES
# ============================================================================

def get_strategy_category(strategy_name: str) -> str:
    """
    Détermine la catégorie d'une stratégie à partir de son nom.
    
    Args:
        strategy_name: Nom de la stratégie
        
    Returns:
        Catégorie : 'single_leg', 'spread', 'straddle_strangle', 'butterfly', 'condor', 'complex'
    """
    name_lower = strategy_name.lower()
    
    if 'long call' in name_lower or 'short call' in name_lower or \
       'long put' in name_lower or 'short put' in name_lower:
        if '/' not in strategy_name:  # Pas de multiples strikes
            return 'single_leg'
    
    if 'spread' in name_lower:
        return 'spread'
    
    if 'straddle' in name_lower or 'strangle' in name_lower:
        return 'straddle_strangle'
    
    if 'butterfly' in name_lower:
        return 'butterfly'
    
    if 'condor' in name_lower:
        return 'condor'
    
    return 'complex'


def format_strategy_name_for_display(strategy_name: str, max_length: int = 30) -> str:
    """
    Formate un nom de stratégie pour l'affichage (tronque si trop long).
    
    Args:
        strategy_name: Nom de la stratégie
        max_length: Longueur maximale
        
    Returns:
        Nom formaté (avec "..." si tronqué)
    """
    if len(strategy_name) <= max_length:
        return strategy_name
    
    return strategy_name[:max_length-3] + "..."


# ============================================================================
# EXEMPLE D'UTILISATION
# ============================================================================

if __name__ == "__main__":
    from myproject.option.option_class import Option
    
    print("=" * 70)
    print("TESTS DE RECONNAISSANCE DE STRATÉGIES")
    print("=" * 70)
    
    # Test 1 : Long Call
    print("\n1. Long Call :")
    call = Option(option_type='call', strike=100.0, premium=2.5, position='long')
    print(f"   {generate_strategy_name([call])}")
    
    # Test 2 : Bull Call Spread
    print("\n2. Bull Call Spread :")
    call1 = Option(option_type='call', strike=95.0, premium=3.0, position='long')
    call2 = Option(option_type='call', strike=100.0, premium=2.0, position='short')
    print(f"   {generate_strategy_name([call1, call2])}")
    
    # Test 3 : Long Straddle
    print("\n3. Long Straddle :")
    call3 = Option(option_type='call', strike=100.0, premium=2.5, position='long')
    put1 = Option(option_type='put', strike=100.0, premium=2.0, position='long')
    print(f"   {generate_strategy_name([call3, put1])}")
    
    # Test 4 : Call Butterfly
    print("\n4. Call Butterfly :")
    call_low = Option(option_type='call', strike=95.0, premium=4.0, position='long')
    call_mid = Option(option_type='call', strike=100.0, premium=2.0, position='short')
    call_high = Option(option_type='call', strike=105.0, premium=1.0, position='long')
    print(f"   {generate_strategy_name([call_low, call_mid, call_high])}")
    
    # Test 5 : Iron Condor
    print("\n5. Iron Condor :")
    put_low = Option(option_type='put', strike=90.0, premium=0.5, position='long')
    put_mid = Option(option_type='put', strike=95.0, premium=1.5, position='short')
    call_mid = Option(option_type='call', strike=105.0, premium=1.5, position='short')
    call_high = Option(option_type='call', strike=110.0, premium=0.5, position='long')
    print(f"   {generate_strategy_name([put_low, put_mid, call_mid, call_high])}")
    
    # Test 6 : Catégories
    print("\n" + "=" * 70)
    print("CATÉGORIES DE STRATÉGIES")
    print("=" * 70)
    
    strategies = [
        "Long Call 100.00",
        "BullCallSpread 95.00/100.00",
        "LongStraddle 100.00",
        "CallButterfly 95.00/100.00/105.00",
        "IronCondor 90.00/95.00/105.00/110.00"
    ]
    
    for strat in strategies:
        category = get_strategy_category(strat)
        print(f"   {strat:<40} -> {category}")
