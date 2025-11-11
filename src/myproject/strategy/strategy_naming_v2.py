"""
Naming des Stratégies d'Options — version corrigée
==================================================
- Corrige l'identification Straddle / Strangle (même position requise)
- Distingue Risk Reversal / Reverse Risk Reversal quand positions mixtes
- Règles bull/bear pour spreads (call/put) robustes
- Noms canoniques avec strikes triés
"""

import numpy as np
from typing import List
from myproject.option.option_class import Option


def _format_option(o: Option, sign: float) -> str:
    """
    Formate une option au format: +-{underlying}{month}{year} {strike}{C/P}
    Exemple: +ERZ6 98.5C ou -ERZ6 98.0P
    """
    sign_str = "+" if sign == 1 else "-"
    underlying = o.underlying_symbol or "ER"
    month = o.expiration_month
    year = o.expiration_year
    # Accès direct à l'attribut au lieu de o.is_call()
    option_type = "C" if o.option_type == "call" else "P"
    return f"{sign_str}{underlying}{month}{year} {o.strike}{option_type}"


def generate_strategy_name(options: List[Option], signs: np.ndarray) -> str:
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

    # OPTIMISATION: Trier seulement si nécessaire (vérification rapide)
    # Les options sont souvent déjà triées depuis option_generator
    if n_legs > 1 and options[0].strike > options[1].strike:
        options.sort(key=lambda o: float(o.strike))

    # Pré-calculer les types d'options pour éviter les appels multiples
    option_types = [opt.option_type for opt in options]  # Accès direct à l'attribut
    
    # ======================================================================
    # 1 LEG
    # ======================================================================
    if n_legs == 1:
        o = options[0]
        s = signs[0]
        position = "long" if s == 1 else "short"
        return f"{position} {option_types[0].lower()} {o.strike} "

    # ======================================================================
    # 2 LEGS
    # ======================================================================
    if n_legs == 2:
        o1, o2 = options[0], options[1]
        s1, s2 = signs[0], signs[1]
        t1, t2 = option_types[0], option_types[1]

        # Même type d'option (call-call ou put-put)
        if t1 == t2:  # Plus rapide que o1.is_call() and o2.is_call()
            if t1 == "call":
                # Spreads verticaux sur calls
                if s1 == 1 and s2 == -1:
                    return f"Bull Call Spread {o1.strike}/{o2.strike}"
                elif s1 == -1 and s2 == 1:
                    return f"Bear Call Spread {o1.strike}/{o2.strike}"
                elif s1 == 1 and s2 == 1:
                    return f"Long Call Strip {o1.strike}/{o2.strike}"
                else:  # short/short
                    return f"Short Call Strip {o1.strike}/{o2.strike}"
            else:  # put
                # Spreads verticaux sur puts
                if s1 == 1 and s2 == -1:
                    return f"Bear Put Spread {o1.strike}/{o2.strike}"
                elif s1 == -1 and s2 == 1:
                    return f"Bull Put Spread {o1.strike}/{o2.strike}"
                elif s1 == 1 and s2 == 1:
                    return f"Long Put Strip {o1.strike}/{o2.strike}"
                else:  # short/short
                    return f"Short Put Strip {o1.strike}/{o2.strike}"

        # Types mixtes (call + put)
        else:
            # Straddle : même strike, même position
            if o1.strike == o2.strike:
                # Long Straddle : long call + long put
                if s1 == 1 and s2 == 1:
                    return f"Long Straddle {o1.strike}"
                # Short Straddle : short call + short put
                elif s1 == -1 and s2 == -1:
                    return f"Short Straddle {o1.strike}"

            # Strangle : strikes différents, même position
            elif o1.strike != o2.strike:
                if s1 == 1 and s2 == 1:
                    return f"Long Strangle {o1.strike}/{o2.strike}"
                elif s1 == -1 and s2 == -1:
                    return f"Short Strangle {o1.strike}/{o2.strike}"

            # Risk Reversal : positions mixtes
            # Identifier quel est le call et quel est le put
            call_idx = 0 if t1 == "call" else 1
            put_idx = 0 if t1 == "put" else 1
            call = options[call_idx]
            put = options[put_idx]
            call_sign = signs[call_idx]
            put_sign = signs[put_idx]

            # Risk Reversal : long call + short put
            if call_sign == 1 and put_sign == -1:
                return f"Risk Reversal {put.strike}/{call.strike}"
            # Reverse Risk Reversal : short call + long put
            elif call_sign == -1 and put_sign == 1:
                return f"Reverse Risk Reversal {put.strike}/{call.strike}"

            # Fallback pour types mixtes non reconnus
            pos1 = "L" if s1 == 1 else "S"
            pos2 = "L" if s2 == 1 else "S"
            return f"Custom Mixed 2-Leg {pos1}{o1.strike}/{pos2}{o2.strike}"

    # ======================================================================
    # 3 LEGS
    # ======================================================================
    if n_legs == 3:
        o1, o2, o3 = options[0], options[1], options[2]
        s1, s2, s3 = signs[0], signs[1], signs[2]
        t1, t2, t3 = option_types[0], option_types[1], option_types[2]

        # ================== CALLS UNIQUEMENT ==================
        if t1 == "call" and t2 == "call" and t3 == "call":
            # Long Call Butterfly : long-short-long (1-2-1 pattern)
            if s1 == 1 and s2 == -1 and s3 == 1:
                return f"{o1.underlying_symbol}{o1.expiration_month}{o1.expiration_year} Long Call Butterfly {o1.strike}/{o2.strike}/{o3.strike}"

            # Short Call Butterfly : short-long-short
            elif s1 == -1 and s2 == 1 and s3 == -1:
                return f"{o1.underlying_symbol}{o1.expiration_month}{o1.expiration_year} Short Call Butterfly {o1.strike}/{o2.strike}/{o3.strike}"

            # Bull Call Ladder (Long Call Ladder) : long-long-short
            elif s1 == 1 and s2 == 1 and s3 == -1:
                return f"{o1.underlying_symbol}{o1.expiration_month}{o1.expiration_year} Bull Call Ladder {o1.strike}/{o2.strike}/{o3.strike}"

            # Bear Call Ladder (Short Call Ladder) : short-short-long
            elif s1 == -1 and s2 == -1 and s3 == 1:
                return f"{o1.underlying_symbol}{o1.expiration_month}{o1.expiration_year} Bear Call Ladder {o1.strike}/{o2.strike}/{o3.strike}"

            # Long Call Ladder inversé : long-short-short
            elif s1 == 1 and s2 == -1 and s3 == -1:
                return f"{o1.underlying_symbol}{o1.expiration_month}{o1.expiration_year} Modified Bull Call Ladder {o1.strike}/{o2.strike}/{o3.strike}"

            # Short Call Ladder inversé : short-long-long
            elif s1 == -1 and s2 == 1 and s3 == 1:
                return f"{o1.underlying_symbol}{o1.expiration_month}{o1.expiration_year} Modified Bear Call Ladder {o1.strike}/{o2.strike}/{o3.strike}"

            else:
                parts = [_format_option(o, signs[i]) for i, o in enumerate(options)]
                return " ".join(parts)

        # ================== PUTS UNIQUEMENT ==================
        elif t1 == "put" and t2 == "put" and t3 == "put":
            # Long Put Butterfly : long-short-long
            if s1 == 1 and s2 == -1 and s3 == 1:
                return f"{o1.underlying_symbol}{o1.expiration_month}{o1.expiration_year} Long Put Butterfly {o1.strike}/{o2.strike}/{o3.strike}"

            # Short Put Butterfly : short-long-short
            elif s1 == -1 and s2 == 1 and s3 == -1:
                return f"{o1.underlying_symbol}{o1.expiration_month}{o1.expiration_year} Short Put Butterfly {o1.strike}/{o2.strike}/{o3.strike}"

            # Bear Put Ladder (Long Put Ladder) : long-long-short
            elif s1 == 1 and s2 == 1 and s3 == -1:
                return f"{o1.underlying_symbol}{o1.expiration_month}{o1.expiration_year} Bear Put Ladder {o1.strike}/{o2.strike}/{o3.strike}"

            # Bull Put Ladder (Short Put Ladder) : short-short-long
            elif s1 == -1 and s2 == -1 and s3 == 1:
                return f"{o1.underlying_symbol}{o1.expiration_month}{o1.expiration_year} Bull Put Ladder {o1.strike}/{o2.strike}/{o3.strike}"

            # Long Put Ladder inversé : long-short-short
            elif s1 == 1 and s2 == -1 and s3 == -1:
                return f"{o1.underlying_symbol}{o1.expiration_month}{o1.expiration_year} Modified Bear Put Ladder {o1.strike}/{o2.strike}/{o3.strike}"

            # Short Put Ladder inversé : short-long-long
            elif s1 == -1 and s2 == 1 and s3 == 1:
                return f"{o1.underlying_symbol}{o1.expiration_month}{o1.expiration_year} Modified Bull Put Ladder {o1.strike}/{o2.strike}/{o3.strike}"

            else:
                parts = [_format_option(o, signs[i]) for i, o in enumerate(options)]
                return " ".join(parts)

        # ================== TYPES MIXTES (CALL + PUT) ==================
        else:
            # Génération des noms avec format complet
            parts = [_format_option(o, signs[i]) for i, o in enumerate(options)]
            return " ".join(parts)

    # ======================================================================
    # 4 LEGS
    # ======================================================================
    if n_legs == 4:
        o1, o2, o3, o4 = options[0], options[1], options[2], options[3]
        s1, s2, s3, s4 = signs[0], signs[1], signs[2], signs[3]
        t1, t2, t3, t4 = option_types[0], option_types[1], option_types[2], option_types[3]

        # Comptage optimisé (sans appels de méthodes)
        n_calls = sum(1 for t in option_types if t == "call")
        n_puts = 4 - n_calls  # Plus rapide que de compter

        # ================== BUTTERFLIES (4 legs avec strike du milieu répété) ==================
        # Vérifier si c'est un butterfly : strike1, strike2, strike2, strike3
        # Les 2 legs du milieu ont le même strike et la même position
        if o2.strike == o3.strike and s2 == s3 and o1.strike < o2.strike < o4.strike:

            # CALL BUTTERFLY
            if n_calls == 4:
                # Long Call Butterfly : long-short-short-long
                if s1 == 1 and s2 == -1 and s3 == -1 and s4 == 1:
                    return f"{o1.underlying_symbol}{o1.expiration_month}{o1.expiration_year} {o1.strike}/{o2.strike}/{o4.strike} Call Fly"

                # Short Call Butterfly : short-long-long-short
                elif s1 == -1 and s2 == 1 and s3 == 1 and s4 == -1:
                    return f"{o1.underlying_symbol}{o1.expiration_month}{o1.expiration_year} {o1.strike}/{o2.strike}/{o4.strike} Short Call Fly"

            # PUT BUTTERFLY
            elif n_puts == 4:
                # Long Put Butterfly : long-short-short-long
                if s1 == 1 and s2 == -1 and s3 == -1 and s4 == 1:
                    return f"{o1.underlying_symbol}{o1.expiration_month}{o1.expiration_year} {o1.strike}/{o2.strike}/{o4.strike} Put Fly"

                # Short Put Butterfly : short-long-long-short
                elif s1 == -1 and s2 == 1 and s3 == 1 and s4 == -1:
                    return f"{o1.underlying_symbol}{o1.expiration_month}{o1.expiration_year} {o1.strike}/{o2.strike}/{o4.strike} Short Put Fly"

        # ================== IRON CONDOR ==================
        # Iron Condor : 4 options, 2 calls + 2 puts
        if n_calls == 2 and n_puts == 2:
            # Séparer calls et puts avec leurs indices (optimisé)
            call_indices = [i for i, t in enumerate(option_types) if t == "call"]
            put_indices = [i for i, t in enumerate(option_types) if t == "put"]

            calls = [options[i] for i in call_indices]
            puts = [options[i] for i in put_indices]

            # Trier par strike en gardant la trace des indices
            call_sorted = sorted(zip(calls, call_indices), key=lambda x: x[0].strike)
            put_sorted = sorted(zip(puts, put_indices), key=lambda x: x[0].strike)

            calls_sorted = [x[0] for x in call_sorted]
            call_signs = [signs[x[1]] for x in call_sorted]
            puts_sorted = [x[0] for x in put_sorted]
            put_signs = [signs[x[1]] for x in put_sorted]

            # Iron Condor : short middle, long wings
            # Put spread: long low put + short high put
            # Call spread: short low call + long high call
            if (
                put_signs[0] == 1
                and put_signs[1] == -1
                and call_signs[0] == -1
                and call_signs[1] == 1
            ):
                return f"{o1.underlying_symbol}{o1.expiration_month}{o1.expiration_year}{puts_sorted[0].strike}/{puts_sorted[1].strike}/{calls_sorted[0].strike}/{calls_sorted[1].strike} Iron Condor"

            # Reverse Iron Condor
            elif (
                put_signs[0] == -1
                and put_signs[1] == 1
                and call_signs[0] == 1
                and call_signs[1] == -1
            ):
                return f"{o1.underlying_symbol}{o1.expiration_month}{o1.expiration_year}{puts_sorted[0].strike}/{puts_sorted[1].strike}/{calls_sorted[0].strike}/{calls_sorted[1].strike} Reverse Iron Condor"

            else:
                # Génération des noms avec format complet
                parts = [_format_option(o, signs[i]) for i, o in enumerate(options)]
                return " ".join(parts)

        # Tous calls
        elif n_calls == 4:
            # Condor : 1-1-1-1 avec positions alternées
            if s1 == 1 and s2 == -1 and s3 == -1 and s4 == 1:
                return (
                    f"Long Call Condor {o1.strike}/{o2.strike}/{o3.strike}/{o4.strike}"
                )
            elif s1 == -1 and s2 == 1 and s3 == 1 and s4 == -1:
                return f"{o1.underlying_symbol}{o1.expiration_month}{o1.expiration_year}{o1.strike}/{o2.strike}/{o3.strike}/{o4.strike} Short Call Condor"
            else:
                parts = [_format_option(o, signs[i]) for i, o in enumerate(options)]
                return " ".join(parts)

        # Tous puts
        elif n_puts == 4:
            if s1 == 1 and s2 == -1 and s3 == -1 and s4 == 1:
                return f"{o1.underlying_symbol}{o1.expiration_month}{o1.expiration_year}{o1.strike}/{o2.strike}/{o3.strike}/{o4.strike} Long Put Condor"
            elif s1 == -1 and s2 == 1 and s3 == 1 and s4 == -1:
                return f"{o1.underlying_symbol}{o1.expiration_month}{o1.expiration_year}{o1.strike}/{o2.strike}/{o3.strike}/{o4.strike} Short Put Condor"
            else:
                parts = [_format_option(o, signs[i]) for i, o in enumerate(options)]
                return " ".join(parts)

        # Autres combinaisons
        else:
            # Génération des noms avec format complet
            parts = [_format_option(o, signs[i]) for i, o in enumerate(options)]
            return " ".join(parts)

    # ======================================================================
    # 5+ LEGS (fallback)
    # ======================================================================
    parts = [_format_option(o, signs[i]) for i, o in enumerate(options)]
    return " ".join(parts)
