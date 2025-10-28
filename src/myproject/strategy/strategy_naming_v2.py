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


def _sorted_strikes_str(options: List[Option]) -> str:
    strikes = sorted(float(o.strike) for o in options)
    return "/".join(f"{s:.2f}" for s in strikes)


def _both_same_position(a: Option, b: Option) -> bool:
    return a.position == b.position


def _position_name(is_long: bool) -> str:
    return "Long" if is_long else "Short"


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

    calls = [o for o in options if o.option_type == "call"]
    puts  = [o for o in options if o.option_type == "put"]
    longs = [o for o in options if o.position == "long"]
    shorts= [o for o in options if o.position == "short"]

    strikes_sorted = sorted(set(float(o.strike) for o in options))
    strikes_str = "/".join(f"{s:.2f}" for s in strikes_sorted)

    # ======================================================================
    # 1 LEG
    # ======================================================================
    if n_legs == 1:
        o = options[0]
        return f"{_position_name(o.position=='long')} {o.option_type.capitalize()} {o.strike:.2f}"

    # ======================================================================
    # 2 LEGS
    # ======================================================================
    if n_legs == 2:
        # 2 CALLS -> CALL SPREAD
        if len(calls) == 2 and len(puts) == 0 and len(strikes_sorted) == 2:
            c_low, c_high = sorted(calls, key=lambda x: x.strike)
            # Bull Call Spread : Long(lower) + Short(higher)
            if c_low.position == "long" and c_high.position == "short":
                return f"BullCallSpread {c_low.strike:.2f}/{c_high.strike:.2f}"
            # Bear Call Spread : Short(lower) + Long(higher)
            if c_low.position == "short" and c_high.position == "long":
                return f"BearCallSpread {c_low.strike:.2f}/{c_high.strike:.2f}"
            # Sinon combo générique
            return f"CallSpread {c_low.strike:.2f}/{c_high.strike:.2f}"

        # 2 PUTS -> PUT SPREAD
        if len(puts) == 2 and len(calls) == 0 and len(strikes_sorted) == 2:
            p_low, p_high = sorted(puts, key=lambda x: x.strike)
            # Bull Put Spread : Short(higher) + Long(lower)
            if p_low.position == "long" and p_high.position == "short":
                return f"BullPutSpread {p_low.strike:.2f}/{p_high.strike:.2f}"
            # Bear Put Spread : Long(higher) + Short(lower)
            if p_low.position == "short" and p_high.position == "long":
                return f"BearPutSpread {p_low.strike:.2f}/{p_high.strike:.2f}"
            # Sinon combo générique
            return f"PutSpread {p_low.strike:.2f}/{p_high.strike:.2f}"

        # 1 CALL + 1 PUT
        if len(calls) == 1 and len(puts) == 1:
            c, p = calls[0], puts[0]

            # STRADDLE (même strike + même position)
            if c.strike == p.strike and _both_same_position(c, p):
                return f"{_position_name(c.position=='long')}Straddle {c.strike:.2f}"

            # STRANGLE (strikes différents + même position)
            if c.strike != p.strike and _both_same_position(c, p):
                # convention d’affichage: strikes triés
                k1, k2 = sorted([float(p.strike), float(c.strike)])
                return f"{_position_name(c.position=='long')}Strangle {k1:.2f}/{k2:.2f}"

            # SYNTHÈTIQUES au même strike
            if c.strike == p.strike:
                if c.position == "long" and p.position == "short":
                    return f"SyntheticLong {c.strike:.2f}"
                if c.position == "short" and p.position == "long":
                    return f"SyntheticShort {c.strike:.2f}"

            # RISK REVERSALS (positions mixtes, strikes possiblement différents)
            if c.position == "long" and p.position == "short":
                k1, k2 = sorted([float(p.strike), float(c.strike)])
                return f"RiskReversal {k1:.2f}/{k2:.2f}"
            if c.position == "short" and p.position == "long":
                k1, k2 = sorted([float(p.strike), float(c.strike)])
                return f"ReverseRiskReversal {k1:.2f}/{k2:.2f}"

            # Sinon générique
            return f"2Leg_{len(calls)}C{len(puts)}P_{strikes_str}"

        # Générique 2 legs (si autre cas exotique)
        return f"2Leg_{len(calls)}C{len(puts)}P_{strikes_str}"

    # ======================================================================
    # 3 LEGS (inchangé sauf renommages mineurs)
    # ======================================================================
    if n_legs == 3:
        # STRIP : 2P + 1C au même strike et même position
        if len(puts) == 2 and len(calls) == 1 and len(set(o.strike for o in options)) == 1:
            if len(longs) == 3 or len(shorts) == 3:
                pos = _position_name(len(longs) == 3)
                return f"{pos}Strip {options[0].strike:.2f}"

        # STRAP : 2C + 1P au même strike et même position
        if len(calls) == 2 and len(puts) == 1 and len(set(o.strike for o in options)) == 1:
            if len(longs) == 3 or len(shorts) == 3:
                pos = _position_name(len(longs) == 3)
                return f"{pos}Strap {options[0].strike:.2f}"

        # RATIO CALL SPREADS (3 calls, 2 strikes)
        if len(calls) == 3 and len(set(o.strike for o in calls)) == 2:
            sc = sorted(calls, key=lambda o: o.strike)
            if sc[0].position == "long" and sc[1].position == "short" and sc[2].position == "short":
                return f"CallRatioSpread {_sorted_strikes_str(calls)}"
            if sc[0].position == "long" and sc[1].position == "long" and sc[2].position == "short":
                return f"CallBackspread {_sorted_strikes_str(calls)}"

        # RATIO PUT SPREADS (3 puts, 2 strikes)
        if len(puts) == 3 and len(set(o.strike for o in puts)) == 2:
            sp = sorted(puts, key=lambda o: o.strike)
            if sp[0].position == "long" and sp[1].position == "long" and sp[2].position == "short":
                return f"PutRatioSpread {_sorted_strikes_str(puts)}"
            if sp[0].position == "long" and sp[1].position == "short" and sp[2].position == "short":
                return f"PutBackspread {_sorted_strikes_str(puts)}"

        # BUTTERFLY (3 strikes)
        if len(set(o.strike for o in options)) == 3:
            # 3 CALLS
            if len(calls) == 3 and _is_butterfly_pattern(options):
                return f"CallButterfly {strikes_str}"
            # 3 PUTS
            if len(puts) == 3 and _is_butterfly_pattern(options):
                return f"PutButterfly {strikes_str}"

        return f"3Leg_{len(calls)}C{len(puts)}P_{strikes_str}"

    # ======================================================================
    # 4 LEGS (identique à ta logique, avec vérifs)
    # ======================================================================
    if n_legs == 4:
        uniq_strikes = sorted(set(float(o.strike) for o in options))
        if len(calls) == 2 and len(puts) == 2 and len(uniq_strikes) == 3:
            return f"IronButterfly {strikes_str}"

        if len(calls) == 2 and len(puts) == 2 and len(uniq_strikes) == 2:
            if _is_box_spread_pattern(options):
                return f"BoxSpread {strikes_str}"

        if len(uniq_strikes) == 4:
            if len(calls) == 4 and _is_condor_pattern(options):
                return f"CallCondor {strikes_str}"
            if len(puts) == 4 and _is_condor_pattern(options):
                return f"PutCondor {strikes_str}"
            if len(calls) == 2 and len(puts) == 2 and _is_iron_condor_pattern(options):
                return f"IronCondor {strikes_str}"

        return f"4Leg_{len(calls)}C{len(puts)}P_{strikes_str}"

    # ======================================================================
    # FALLBACK > 4 LEGS
    # ======================================================================
    return f"{n_legs}Leg_{len(calls)}C{len(puts)}P_{strikes_str}"


# ======================= AUXILIARY PATTERN CHECKS =========================

def _is_butterfly_pattern(options: List[Option]) -> bool:
    if len(options) != 3:
        return False
    so = sorted(options, key=lambda o: o.strike)
    # Long-Short-Long OR Short-Long-Short
    pat1 = (so[0].position == 'long'  and so[1].position == 'short' and so[2].position == 'long')
    pat2 = (so[0].position == 'short' and so[1].position == 'long'  and so[2].position == 'short')
    return pat1 or pat2


def _is_condor_pattern(options: List[Option]) -> bool:
    if len(options) != 4:
        return False
    so = sorted(options, key=lambda o: o.strike)
    pat1 = (so[0].position == 'long'  and so[1].position == 'short' and
            so[2].position == 'short' and so[3].position == 'long')
    pat2 = (so[0].position == 'short' and so[1].position == 'long'  and
            so[2].position == 'long'  and so[3].position == 'short')
    return pat1 or pat2


def _is_iron_condor_pattern(options: List[Option]) -> bool:
    if len(options) != 4:
        return False
    calls = sorted([o for o in options if o.option_type == 'call'], key=lambda o: o.strike)
    puts  = sorted([o for o in options if o.option_type == 'put'],  key=lambda o: o.strike)
    if len(calls) != 2 or len(puts) != 2:
        return False
    # Puts : Long (bas) + Short (haut)
    if not (puts[0].position == 'long' and puts[1].position == 'short'):
        return False
    # Calls : Short (bas) + Long (haut)
    if not (calls[0].position == 'short' and calls[1].position == 'long'):
        return False
    # Ordre cohérent entre ailes put/call
    return puts[1].strike < calls[0].strike


def _is_box_spread_pattern(options: List[Option]) -> bool:
    if len(options) != 4:
        return False
    calls = sorted([o for o in options if o.option_type == 'call'], key=lambda o: o.strike)
    puts  = sorted([o for o in options if o.option_type == 'put'],  key=lambda o: o.strike)
    if len(calls) != 2 or len(puts) != 2:
        return False
    if calls[0].strike != puts[0].strike or calls[1].strike != puts[1].strike:
        return False
    # Bull Call : Long(lower) + Short(higher)
    if not (calls[0].position == 'long' and calls[1].position == 'short'):
        return False
    # Bear Put : Short(lower) + Long(higher)
    if not (puts[0].position == 'short' and puts[1].position == 'long'):
        return False
    return True
