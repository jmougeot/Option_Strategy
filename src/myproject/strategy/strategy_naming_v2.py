"""
Naming des Stratégies d'Options — version corrigée
==================================================
- Corrige l'identification Straddle / Strangle (même position requise)
- Distingue Risk Reversal / Reverse Risk Reversal quand positions mixtes
- Règles bull/bear pour spreads (call/put) robustes
- Noms canoniques avec strikes triés
"""

from typing import List
from myproject.option.option_class import Option


def _format_option(o: Option) -> str:
    """
    Formate une option au format: +-{underlying}{month}{year} {strike}{C/P}
    Exemple: +ERZ6 98.5C ou -ERZ6 98.0P
    """
    sign = "+" if o.is_long() else "-"
    underlying = o.underlying_symbol or "ER"
    month = o.expiration_month
    year = o.expiration_year
    option_type = "C" if o.is_call() else "P"
    return f"{sign}{underlying}{month}{year} {o.strike}{option_type}"


def generate_strategy_name(options: List[Option]) -> str:
    """
    Génère un nom descriptif pour une stratégie d'options.

    Règles principales corrigées :
      - Straddle : 1 call + 1 put, *même strike* et *même position*.
      - Strangle : 1 call + 1 put, *strikes différents* et *même position*.
      - Risk Reversal : long call + short put (strikes poss. différents).
      - Reverse Risk Reversal : short call + long put (strikes poss. différents).
      - Spreads : bull/bear call/put selon l’ordre (long/short) et l’ordre des strikes.
    """
    if not options:
        return "EmptyStrategy"

    n_legs = len(options)

    options.sort(key=lambda o: float(o.strike))

    # ======================================================================
    # 1 LEG
    # ======================================================================
    if n_legs == 1:
        o = options[0]
        return f"{o.position} {o.option_type.lower()} {o.strike} "

    # ======================================================================
    # 2 LEGS
    # ======================================================================
    if n_legs == 2:
        o1, o2 = options[0], options[1]
        
        # Même type d'option (call-call ou put-put)
        if o1.is_call() and o2.is_call():
            # Spreads verticaux sur calls
            if o1.is_long_call() and o2.is_short_call():
                return f"Bull Call Spread {o1.strike}/{o2.strike}"
            elif o1.is_short_call() and o2.is_long_call():
                return f"Bear Call Spread {o1.strike}/{o2.strike}"
            elif o1.is_long_call() and o2.is_long_call():
                return f"Long Call Strip {o1.strike}/{o2.strike}"
            else:  # short/short
                return f"Short Call Strip {o1.strike}/{o2.strike}"
        
        elif o1.is_put() and o2.is_put():
            # Spreads verticaux sur puts
            if o1.is_long_put() and o2.is_short_put():
                return f"Bear Put Spread {o1.strike}/{o2.strike}"
            elif o1.is_short_put() and o2.is_long_put():
                return f"Bull Put Spread {o1.strike}/{o2.strike}"
            elif o1.is_long_put() and o2.is_long_put():
                return f"Long Put Strip {o1.strike}/{o2.strike}"
            else:  # short/short
                return f"Short Put Strip {o1.strike}/{o2.strike}"
        
        # Types mixtes (call + put)
        else:
            # Straddle : même strike, même position
            if o1.strike == o2.strike:
                # Long Straddle : long call + long put
                if o1.is_long() and o2.is_long():
                    return f"Long Straddle {o1.strike}"
                # Short Straddle : short call + short put
                elif o1.is_short() and o2.is_short():
                    return f"Short Straddle {o1.strike}"
            
            # Strangle : strikes différents, même position
            elif o1.strike != o2.strike:
                if o1.is_long() and o2.is_long():
                    return f"Long Strangle {o1.strike}/{o2.strike}"
                elif o1.is_short() and o2.is_short():
                    return f"Short Strangle {o1.strike}/{o2.strike}"
            
            # Risk Reversal : positions mixtes
            # Identifier quel est le call et quel est le put
            call = o1 if o1.is_call() else o2
            put = o1 if o1.is_put() else o2
            
            # Risk Reversal : long call + short put
            if call.is_long() and put.is_short():
                return f"Risk Reversal {put.strike}/{call.strike}"
            # Reverse Risk Reversal : short call + long put
            elif call.is_short() and put.is_long():
                return f"Reverse Risk Reversal {put.strike}/{call.strike}"
            
            # Fallback pour types mixtes non reconnus
            pos1 = "L" if o1.is_long() else "S"
            pos2 = "L" if o2.is_long() else "S"
            return f"Custom Mixed 2-Leg {pos1}{o1.strike}/{pos2}{o2.strike}"

    # ======================================================================
    # 3 LEGS
    # ======================================================================
    if n_legs == 3:
        o1, o2, o3 = options[0], options[1], options[2]
        
        # ================== CALLS UNIQUEMENT ==================
        if o1.is_call() and o2.is_call() and o3.is_call():
            # Long Call Butterfly : long-short-long (1-2-1 pattern)
            if o1.is_long_call() and o2.is_short_call() and o3.is_long_call():
                return f"Long Call Butterfly {o1.strike}/{o2.strike}/{o3.strike}"
            
            # Short Call Butterfly : short-long-short
            elif o1.is_short_call() and o2.is_long_call() and o3.is_short_call():
                return f"Short Call Butterfly {o1.strike}/{o2.strike}/{o3.strike}"
            
            # Bull Call Ladder (Long Call Ladder) : long-long-short
            elif o1.is_long_call() and o2.is_long_call() and o3.is_short_call():
                return f"Bull Call Ladder {o1.strike}/{o2.strike}/{o3.strike}"
            
            # Bear Call Ladder (Short Call Ladder) : short-short-long
            elif o1.is_short_call() and o2.is_short_call() and o3.is_long_call():
                return f"Bear Call Ladder {o1.strike}/{o2.strike}/{o3.strike}"
            
            # Long Call Ladder inversé : long-short-short
            elif o1.is_long_call() and o2.is_short_call() and o3.is_short_call():
                return f"Modified Bull Call Ladder {o1.strike}/{o2.strike}/{o3.strike}"
            
            # Short Call Ladder inversé : short-long-long
            elif o1.is_short_call() and o2.is_long_call() and o3.is_long_call():
                return f"Modified Bear Call Ladder {o1.strike}/{o2.strike}/{o3.strike}"
            
            else:
                parts = [_format_option(o) for o in options]
                return " ".join(parts)
        
        # ================== PUTS UNIQUEMENT ==================
        elif o1.is_put() and o2.is_put() and o3.is_put():
            # Long Put Butterfly : long-short-long
            if o1.is_long_put() and o2.is_short_put() and o3.is_long_put():
                return f"Long Put Butterfly {o1.strike}/{o2.strike}/{o3.strike}"
            
            # Short Put Butterfly : short-long-short
            elif o1.is_short_put() and o2.is_long_put() and o3.is_short_put():
                return f"Short Put Butterfly {o1.strike}/{o2.strike}/{o3.strike}"
            
            # Bear Put Ladder (Long Put Ladder) : long-long-short
            elif o1.is_long_put() and o2.is_long_put() and o3.is_short_put():
                return f"Bear Put Ladder {o1.strike}/{o2.strike}/{o3.strike}"
            
            # Bull Put Ladder (Short Put Ladder) : short-short-long
            elif o1.is_short_put() and o2.is_short_put() and o3.is_long_put():
                return f"Bull Put Ladder {o1.strike}/{o2.strike}/{o3.strike}"
            
            # Long Put Ladder inversé : long-short-short
            elif o1.is_long_put() and o2.is_short_put() and o3.is_short_put():
                return f"Modified Bear Put Ladder {o1.strike}/{o2.strike}/{o3.strike}"
            
            # Short Put Ladder inversé : short-long-long
            elif o1.is_short_put() and o2.is_long_put() and o3.is_long_put():
                return f"Modified Bull Put Ladder {o1.strike}/{o2.strike}/{o3.strike}"
            
            else:
                parts = [_format_option(o) for o in options]
                return " ".join(parts)
        
        # ================== TYPES MIXTES (CALL + PUT) ==================
        else:
            # Génération des noms avec format complet
            parts = [_format_option(o) for o in options]
            return " ".join(parts)

    # ======================================================================
    # 4 LEGS
    # ======================================================================
    if n_legs == 4:
        o1, o2, o3, o4 = options[0], options[1], options[2], options[3]
        
        # Iron Condor : 4 options, 2 calls + 2 puts
        n_calls = sum(1 for o in options if o.is_call())
        n_puts = sum(1 for o in options if o.is_put())
        
        if n_calls == 2 and n_puts == 2:
            # Séparer calls et puts
            calls = [o for o in options if o.is_call()]
            puts = [o for o in options if o.is_put()]
            
            # Trier par strike
            calls.sort(key=lambda o: o.strike)
            puts.sort(key=lambda o: o.strike)
            
            # Iron Condor : short middle, long wings
            # Put spread: long low put + short high put
            # Call spread: short low call + long high call
            if (puts[0].is_long_put() and puts[1].is_short_put() and
                calls[0].is_short_call() and calls[1].is_long_call()):
                return f"Iron Condor {puts[0].strike}/{puts[1].strike}/{calls[0].strike}/{calls[1].strike}"
            
            # Reverse Iron Condor
            elif (puts[0].is_short_put() and puts[1].is_long_put() and
                  calls[0].is_long_call() and calls[1].is_short_call()):
                return f"Reverse Iron Condor {puts[0].strike}/{puts[1].strike}/{calls[0].strike}/{calls[1].strike}"
            
            else:
                # Génération des noms avec format complet
                parts = [_format_option(o) for o in options]
                return " ".join(parts)
        
        # Tous calls
        elif n_calls == 4:
            # Condor : 1-1-1-1 avec positions alternées
            if (o1.is_long_call() and o2.is_short_call() and 
                o3.is_short_call() and o4.is_long_call()):
                return f"Long Call Condor {o1.strike}/{o2.strike}/{o3.strike}/{o4.strike}"
            elif (o1.is_short_call() and o2.is_long_call() and 
                  o3.is_long_call() and o4.is_short_call()):
                return f"Short Call Condor {o1.strike}/{o2.strike}/{o3.strike}/{o4.strike}"
            else:
                parts = [_format_option(o) for o in options]
                return " ".join(parts)
        
        # Tous puts
        elif n_puts == 4:
            if (o1.is_long_put() and o2.is_short_put() and 
                o3.is_short_put() and o4.is_long_put()):
                return f"Long Put Condor {o1.strike}/{o2.strike}/{o3.strike}/{o4.strike}"
            elif (o1.is_short_put() and o2.is_long_put() and 
                  o3.is_long_put() and o4.is_short_put()):
                return f"Short Put Condor {o1.strike}/{o2.strike}/{o3.strike}/{o4.strike}"
            else:
                parts = [_format_option(o) for o in options]
                return " ".join(parts)
        
        # Autres combinaisons
        else:
            # Génération des noms avec format complet
            parts = [_format_option(o) for o in options]
            return " ".join(parts)

    # ======================================================================
    # 5+ LEGS (fallback)
    # ======================================================================
    parts = [_format_option(o) for o in options]
    return " ".join(parts)
