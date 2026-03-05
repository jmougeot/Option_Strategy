"""
Script complet pour parser Trade_monitor.csv et construire des StrategyComparison
"""

import re
from typing import List, Tuple, Optional
from alarm.models.strategy import Strategy, OptionLeg, Position

Strike = {
"06" : "0625", 
"12" : "125",
"18" : "1875",
"31" : "3125",
"37" : "375",
"43" : "4375",
"56" : "5625",
"60"  : "625",
"62" : "625",
"68" : "6875",
"81" : "8125",
"87" :"875",
"93": "9375",
}

# Positions par type de stratégie: (position, quantité)
STRATEGY_POSITIONS = {
    "call_fly": [("long", 1), ("short", 2), ("long", 1)],
    "put_fly": [("long", 1), ("short", 2), ("long", 1)],
    "broken_call_fly": [("long", 1), ("short", 2), ("long", 1)],
    "broken_put_fly": [("long", 1), ("short", 2), ("long", 1)],
    "call_condor": [("long", 1), ("short", 1), ("short", 1), ("long", 1)],
    "put_condor": [("long", 1), ("short", 1), ("short", 1), ("long", 1)],
    "call_spread": [("long", 1), ("short", 1)],
    "put_spread": [("short", 1), ("long", 1)],
    "call_strangle": [("long", 1), ("long", 1)],
    "put_strangle": [("long", 1), ("long", 1)],
    "call_straddle": [("long", 1), ("long", 1)],
    "put_straddle": [("long", 1), ("long", 1)],
    "call_ladder": [("long", 1), ("short", 1), ("short", 1)],
    "put_ladder": [("long", 1), ("short", 1), ("short", 1)],
}



def separate_parts(info_strategy: str) -> Tuple[str, str, str]:
    """
    Sépare une ligne comme 'Avi  SFRF6 96.50/96.625/96.75 Call Fly  buy to open' en 3 parties
    basé sur les tabs ou grands espaces (2+ espaces consécutifs)
    - partie 1: 'Avi'
    - partie 2: 'SFRF6 96.50/96.625/96.75 Call Fly'
    - partie 3: 'buy to open'
    """
    # Split sur les tabs ou espaces multiples (2 ou plus)
    parts = re.split(r'\t+|\s{2,}', info_strategy.strip())
    
    # Si une seule partie, la mettre dans parts[1] (stratégie)
    if len(parts) == 1:
        return "", parts[0], ""
    
    # Garantir 3 éléments
    while len(parts) < 3:
        parts.append("")
    
    return parts[0], parts[1], parts[2]

def convert_strike_decimal(strike_str: str) -> float:
    """Convertit un strike arrondi en strike Bloomberg complet
    Ex: 98.06 -> 98.0625, 98.12 -> 98.125
    """
    if "." not in strike_str:
        return float(strike_str)
    
    parts = strike_str.split(".")
    integer_part = parts[0]
    decimal_part = parts[1] if len(parts) > 1 else ""
    
    # Si la partie décimale est dans le dictionnaire Strike, la remplacer
    if decimal_part in Strike:
        return float(integer_part + "." + Strike[decimal_part])
    else:
        return float(strike_str)
    
def detect_vs(strategy_str: str) -> Tuple[str, Optional[str]]:
    """
    Détecte si la stratégie contient 'vs' et split en deux parties
    Ex: 'SFRF6 96.50/96.75 Call Fly vs SFRF6 97.00 Call'
    Returns: ('SFRF6 96.50/96.75 Call Fly', 'SFRF6 97.00 Call')
    Ou: ('SFRF6 96.50/96.75 Call Fly', None) si pas de vs
    """
    # Pattern pour détecter "vs" entouré d'espaces
    vs_pattern = r'\s+vs\s+|\s+VS\s+'
    
    if re.search(vs_pattern, strategy_str, re.IGNORECASE):
        # Split sur vs
        parts = re.split(vs_pattern, strategy_str, maxsplit=1, flags=re.IGNORECASE)
        if len(parts) == 2:
            return parts[0].strip(), parts[1].strip()
    
    return strategy_str, None

def extract_strikes(strategy_str: str) -> List[float]:
    """Extraction avancée des strikes - gère tous les formats et conversions Bloomberg"""
    strikes = []

    # Nettoyer: retirer codes produit au début (ERJ4, SFRM4, etc.)
    cleaned_str = re.sub(r"^\s*[A-Z]{2,5}\d\s+", "", strategy_str, flags=re.IGNORECASE)

    # Chercher d'abord les séquences avec / (priorité)
    # Pattern: nombres séparés par / (avec ou sans décimales)
    slash_pattern = r"(\d{2,3}\.?\d{0,5}(?:/\d{1,5}\.?\d{0,5})+)"
    slash_sequences = re.findall(slash_pattern, cleaned_str)

    for sequence in slash_sequences:
        parts = sequence.split("/")
        first = parts[0]

        if "." in first:
            # Format avec décimales: 106.4/106.8/107 ou 95.06/12/18
            base = first.split(".")[0]

            # Premier élément - appliquer conversion
            try:
                strike = convert_strike_decimal(first)
                if 50 < strike < 200:
                    strikes.append(strike)
            except:
                pass

            # Éléments suivants
            for part in parts[1:]:
                if "." in part:
                    # Décimale complète: 106.8, 95.125
                    try:
                        strike = convert_strike_decimal(part)
                        if 50 < strike < 200:
                            strikes.append(strike)
                    except:
                        pass
                elif len(part) <= 2:
                    # Suffixe 2 chiffres: "12" → 95.125 (avec conversion)
                    try:
                        full_str = base + "." + part
                        strike = convert_strike_decimal(full_str)
                        if 50 < strike < 200:
                            strikes.append(strike)
                    except:
                        pass
                elif len(part) == 3:
                    # 3 chiffres: probablement entier "107"
                    try:
                        strike = float(part)
                        if 50 < strike < 200:
                            strikes.append(strike)
                    except:
                        pass
                else:
                    # 4+ chiffres: format collé "9712"
                    try:
                        full_str = part[:2] + "." + part[2:]
                        strike = convert_strike_decimal(full_str)
                        if 50 < strike < 200:
                            strikes.append(strike)
                    except:
                        pass

        elif len(first) == 2:
            # Format: 95/95.06/95.125/95.18 (premier = 2 chiffres)
            base = first
            try:
                strike = float(first)
                if 50 < strike < 200:
                    strikes.append(strike)
            except:
                pass

            for part in parts[1:]:
                if "." in part:
                    try:
                        strike = convert_strike_decimal(part)
                        if 50 < strike < 200:
                            strikes.append(strike)
                    except:
                        pass
                elif len(part) <= 2:
                    try:
                        full_str = base + "." + part
                        strike = convert_strike_decimal(full_str)
                        if 50 < strike < 200:
                            strikes.append(strike)
                    except:
                        pass
        elif len(first) == 4:
            # Format collé 4 chiffres: 9712/9737/9750 ou 9540/50/60/70
            base = first[:2]

            if all(len(p) == 4 for p in parts):
                # Tous 4 chiffres: 9712/9737/9750
                for part in parts:
                    try:
                        full_str = part[:2] + "." + part[2:]
                        strike = convert_strike_decimal(full_str)
                        if 50 < strike < 200:
                            strikes.append(strike)
                    except:
                        pass
            else:
                # Format mixte: 9540/50/60/70
                try:
                    full_str = first[:2] + "." + first[2:]
                    strike = convert_strike_decimal(full_str)
                    if 50 < strike < 200:
                        strikes.append(strike)
                except:
                    pass
                for part in parts[1:]:
                    if len(part) == 2:
                        try:
                            full_str = base + "." + part
                            strike = convert_strike_decimal(full_str)
                            if 50 < strike < 200:
                                strikes.append(strike)
                        except:
                            pass


    # Si pas de séquence trouvée, extraction simple
    if not strikes:
        simple_pattern = r"\b(\d{2,3}\.?\d{0,5})\b"
        matches = re.findall(simple_pattern, cleaned_str)
        for match in matches:
            try:
                strike = convert_strike_decimal(match)
                if 50 < strike < 200:
                    strikes.append(strike)
            except:
                pass

    # Dédupliquer et trier
    return sorted(list(strikes))

def detect_strategy_type(strategy_str: str, num_strikes: int) -> Tuple[str, str]:
    """Détection avancée du type de stratégie avec support straddle/strangle"""
    strategy_lower = strategy_str.lower()

    # Déterminer si call ou put (peut être mixte pour straddle/strangle)
    is_put = "put" in strategy_lower or " p " in strategy_lower or " ps" in strategy_lower
    is_call = "call" in strategy_lower or " c " in strategy_lower or " cs" in strategy_lower
    
    # Si ni call ni put explicite, défaut = call
    if not is_put and not is_call:
        option_type = "call"
    elif is_put and not is_call:
        option_type = "put"
    else:
        option_type = "call"

    # Détecter le type basé sur les mots-clés et le nombre de strikes
    if "fly" in strategy_lower:
        if (
            "broken" in strategy_lower
            or "brk" in strategy_lower
            or "bkn" in strategy_lower
        ):
            return f"broken_{option_type}_fly", option_type
        return f"{option_type}_fly", option_type
    
    elif "condor" in strategy_lower:
        if (
            "broken" in strategy_lower
            or "brk" in strategy_lower
            or "bkn" in strategy_lower
        ):
            return f"broken_{option_type}_fly", option_type
        return f"{option_type}_condor", option_type
    
    elif "straddle" in strategy_lower or "^" in strategy_lower:
        # Straddle: même strike pour call et put
        return f"{option_type}_straddle", option_type
    elif "strangle" in strategy_lower or "^^" in strategy_lower:
        return f"{option_type}_strangle", option_type
    
    elif "ladder" in strategy_lower:
        return f"{option_type}_ladder", option_type
    
    elif (
        "spread" in strategy_lower or " cs" in strategy_lower or " ps" in strategy_lower
    ):
        return f"{option_type}_spread", option_type
    elif num_strikes == 2:

        return f"{option_type}_spread", option_type
    elif num_strikes == 3:
        return f"{option_type}_fly", option_type
    elif num_strikes == 4:
        return f"{option_type}_condor", option_type

    return "unknown", option_type
    
def str_to_leg(match, opt_type, strategy_type, strikes) :
    Legs : List[OptionLeg] = []
    underlying = match.group(1).upper()
    expiry = match.group(2).upper()
    
    # Convertir call/put en C/P pour Bloomberg
    opt_type_code = "C" if opt_type == "call" else "P"

    # Récupérer les positions depuis le dictionnaire
    signs = STRATEGY_POSITIONS.get(strategy_type, [("long", 1)] * len(strikes))

    # Créer les legs
    for i, strike in enumerate(strikes):
        if i >= len(signs):
            break
        
        # Ticker normalisé en MAJUSCULES pour cohérence avec Bloomberg
        ticker = f"{underlying}{expiry}{opt_type_code} {strike} COMDTY"
        position = Position.LONG if signs[i][0] == "long" else Position.SHORT
        quantity = signs[i][1]
        
        Leg_i = OptionLeg(ticker=ticker, position=position, quantity=quantity)
        Legs.append(Leg_i)
    return Legs


def str_to_strat(info_strategy : str) -> Optional[Strategy]:
    """
    Convertit une string de stratégie en objet Strategy
    Ex: 'Avi  SFRF6 96.50/96.625/96.75 Call Fly  buy to open'
    """

    client, name, action = separate_parts(info_strategy)
    
    # Si pas de nom de stratégie, retourner None
    if not name:
        return None
    
    # Détecter si on a un "vs" (deux stratégies)
    part1, part2 = detect_vs(name)
    
    # Traiter la première partie
    strikes1 = extract_strikes(part1)
    strategy_type1, opt_type1 = detect_strategy_type(part1, len(strikes1))  # FIXÉ: utiliser part1

    # Extraire underlying et expiry de la première partie
    pattern = r"\b([A-Z]{2,4})([FGHJKMNQUVXZ]\d)\b"
    match1 = re.search(pattern, part1, re.IGNORECASE)  # FIXÉ: utiliser part1
    
    # Si pas de match, impossible de créer les tickers
    if not match1:
        return None
    
    Legs = str_to_leg(match1, opt_type1, strategy_type1, strikes1)

    # Traiter la deuxième partie si elle existe
    if part2 is not None : 
        strikes2 = extract_strikes(part2)
        strategy_type2, opt_type2 = detect_strategy_type(part2, len(strikes2))  # FIXÉ: utiliser part2
        
        # Chercher underlying/expiry dans part2, sinon réutiliser match1
        match2 = re.search(pattern, part2, re.IGNORECASE)
        if not match2:
            match2 = match1  # Réutiliser le même underlying/expiry
        
        Legs2 = str_to_leg(match2, opt_type2, strategy_type2, strikes2)
        # Inverser les positions de la deuxième stratégie (après "vs")
        for leg in Legs2: 
            if leg.position == Position.LONG:
                leg.position = Position.SHORT
            else: 
                leg.position = Position.LONG
        Legs.extend(Legs2)


    # Créer la stratégie
    strategy = Strategy(
        name=name,
        legs=Legs,
        client=client if client else None,
        action=action if action else None,
    )
    return strategy
