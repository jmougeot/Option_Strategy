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
            call_opt = o1 if o1.is_call() else o2
            put_opt = o1 if o1.is_put() else o2
            
            same_strike = (call_opt.strike == put_opt.strike)
            same_position = (call_opt.position == put_opt.position)
            
            # Straddle : même strike et même position
            if same_strike and same_position:
                pos = "Long" if call_opt.is_long() else "Short"
                return f"{pos} Straddle {call_opt.strike}"
            
            # Strangle : strikes différents et même position
            elif not same_strike and same_position:
                pos = "Long" if call_opt.is_long() else "Short"
                return f"{pos} Strangle {put_opt.strike}/{call_opt.strike}"
            
            # Risk Reversal : long call + short put
            elif call_opt.is_long_call() and put_opt.is_short_put():
                return f"Risk Reversal {put_opt.strike}/{call_opt.strike}"
            
            # Reverse Risk Reversal : short call + long put
            elif call_opt.is_short_call() and put_opt.is_long_put():
                return f"Reverse Risk Reversal {put_opt.strike}/{call_opt.strike}"
            
            else:
                return f"Custom 2-Leg {o1.position_name()} {o1.strike} / {o2.position_name()} {o2.strike}"

    # ======================================================================
    # 3 LEGS
    # ======================================================================
    if n_legs == 3:
        o1, o2, o3 = options[0], options[1], options[2]
        
        # Butterfly : 1-2-1 pattern, même type
        if o1.is_call() and o2.is_call() and o3.is_call():
            # Long Butterfly : long-short-short-long avec ratio 1-2-1
            if o1.is_long_call() and o2.is_short_call() and o3.is_long_call():
                return f"Long Call Butterfly {o1.strike}/{o2.strike}/{o3.strike}"
            elif o1.is_short_call() and o2.is_long_call() and o3.is_short_call():
                return f"Short Call Butterfly {o1.strike}/{o2.strike}/{o3.strike}"
            else:
                return f"Call Strip 3-Leg {o1.strike}/{o2.strike}/{o3.strike}"
        
        elif o1.is_put() and o2.is_put() and o3.is_put():
            if o1.is_long_put() and o2.is_short_put() and o3.is_long_put():
                return f"Long Put Butterfly {o1.strike}/{o2.strike}/{o3.strike}"
            elif o1.is_short_put() and o2.is_long_put() and o3.is_short_put():
                return f"Short Put Butterfly {o1.strike}/{o2.strike}/{o3.strike}"
            else:
                return f"Put Strip 3-Leg {o1.strike}/{o2.strike}/{o3.strike}"
        
        # Types mixtes
        else:
            # Compter calls et puts
            n_calls = sum(1 for o in options if o.is_call())
            n_puts = sum(1 for o in options if o.is_put())
            
            # Collar (call + 2 puts ou put + 2 calls)
            if n_calls == 2 and n_puts == 1:
                return f"Custom Call Collar {o1.strike}/{o2.strike}/{o3.strike}"
            elif n_calls == 1 and n_puts == 2:
                return f"Custom Put Collar {o1.strike}/{o2.strike}/{o3.strike}"
            else:
                strikes = "/".join(str(o.strike) for o in options)
                return f"Custom 3-Leg {strikes}"

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
                strikes = "/".join(str(o.strike) for o in options)
                return f"Custom Mixed 4-Leg {strikes}"
        
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
                strikes = "/".join(str(o.strike) for o in options)
                return f"Call Strip 4-Leg {strikes}"
        
        # Tous puts
        elif n_puts == 4:
            if (o1.is_long_put() and o2.is_short_put() and 
                o3.is_short_put() and o4.is_long_put()):
                return f"Long Put Condor {o1.strike}/{o2.strike}/{o3.strike}/{o4.strike}"
            elif (o1.is_short_put() and o2.is_long_put() and 
                  o3.is_long_put() and o4.is_short_put()):
                return f"Short Put Condor {o1.strike}/{o2.strike}/{o3.strike}/{o4.strike}"
            else:
                strikes = "/".join(str(o.strike) for o in options)
                return f"Put Strip 4-Leg {strikes}"
        
        # Autres combinaisons
        else:
            strikes = "/".join(str(o.strike) for o in options)
            return f"Custom 4-Leg {strikes}"

    # ======================================================================
    # 5+ LEGS (fallback)
    # ======================================================================
    strikes = "/".join(str(o.strike) for o in options)
    return f"Custom {n_legs}-Leg {strikes}"
