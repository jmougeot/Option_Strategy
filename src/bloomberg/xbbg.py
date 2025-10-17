# options_greeks_run.py
# Requiert: xbbg, pandas, et une session Bloomberg active (Terminal/API)

import re
from datetime import datetime
from typing import List, Optional
import pandas as pd

try:
    from xbbg import blp
except Exception as e:
    raise SystemExit(
        "❌ xbbg introuvable. Installe-le avec:\n"
        "   pip install xbbg\n"
        "Assure-toi aussi d'avoir une session Bloomberg active (Terminal ou API).\n"
        f"Détail: {e}"
    )

# ===================== PARAMÈTRES À ADAPTER =====================
UNDERLYING = "EURH6 Comdty"   # ex: "EURH6 Comdty", "SPY US Equity"
CP         = "C"              # 'C' pour Calls, 'P' pour Puts, None pour tout
MIN_STRIKE = 97.00            # None si pas de filtre
MAX_STRIKE = 98.00            # None si pas de filtre
EXPIRY     = "H6"             # ex: 'H6', 'Z5' ; None si pas de filtre
OUT_CSV    = None             # None -> auto-nom; sinon ex: "euribor_h6_calls.csv"
FIELDS = [
    'PX_LAST','PX_BID','PX_ASK',
    'OPT_IMP_VOL','OPT_DELTA','OPT_GAMMA','OPT_VEGA','OPT_THETA','OPT_RHO',
    'OPT_UNDL_PX','OPT_STRIKE_PX','OPT_EXPIR_DT'
]
# ================================================================

SUFFIXES = {'Comdty', 'Equity', 'Curncy', 'Index'}

def parse_cp(ticker: str) -> Optional[str]:
    m = re.search(r'\b([A-Z0-9]+)([CP])\b', ticker)
    if m:
        return m.group(2)
    if ' C ' in ticker:
        return 'C'
    if ' P ' in ticker:
        return 'P'
    return None

def parse_strike(ticker: str) -> Optional[float]:
    parts = ticker.split()
    if len(parts) >= 2 and parts[-1] in SUFFIXES:
        try:
            return float(parts[-2])
        except ValueError:
            return None
    m = re.search(r'(\d+\.\d+|\d+)(?=\s+(Comdty|Equity|Curncy|Index)\b)', ticker)
    return float(m.group(1)) if m else None

def contains_expiry_code(ticker: str, code: str) -> bool:
    return code.upper() in ticker.upper()

def option_chain_tickers(underlying: str) -> List[str]:
    df = blp.bds(tickers=underlying, flds='OPT_CHAIN')
    vals = set()
    for v in df.values.ravel().tolist():
        if isinstance(v, str) and ((' C' in v) or (' P' in v) or re.search(r'[CP]\b', v)):
            vals.add(v.strip())
    return sorted(vals)

def filter_tickers(
    tickers: List[str],
    cp: Optional[str] = None,
    min_strike: Optional[float] = None,
    max_strike: Optional[float] = None,
    expiry_code: Optional[str] = None,
) -> List[str]:
    out = []
    for t in tickers:
        t_cp = parse_cp(t)
        t_strike = parse_strike(t)
        if cp and t_cp != cp.upper():
            continue
        if min_strike is not None and (t_strike is None or t_strike < min_strike):
            continue
        if max_strike is not None and (t_strike is None or t_strike > max_strike):
            continue
        if expiry_code and not contains_expiry_code(t, expiry_code):
            continue
        out.append(t)
    return out

def fetch_option_data(tickers: List[str], fields: List[str]) -> pd.DataFrame:
    if not tickers:
        return pd.DataFrame(columns=fields)
    df = blp.bdp(tickers=tickers, flds=fields)
    if 'ticker' in df.columns:
        df = df.set_index('ticker')
    return df

def run():
    print(f"[INFO] Sous-jacent : {UNDERLYING}")
    chain = option_chain_tickers(UNDERLYING)
    print(f"[INFO] Options trouvées sur la chaîne : {len(chain)}")

    filt = filter_tickers(
        chain, cp=CP, min_strike=MIN_STRIKE, max_strike=MAX_STRIKE, expiry_code=EXPIRY
    )
    print(f"[INFO] Options retenues après filtre : {len(filt)}")

    if not filt:
        print("[WARN] Aucun ticker ne correspond aux filtres. Ajuste les paramètres.")
        return

    print("[INFO] Téléchargement BDP (prix + grecs)…")
    df = fetch_option_data(filt, FIELDS)

    # Colonnes utilitaires
    df.insert(0, 'CP', [parse_cp(t) for t in df.index])
    df.insert(1, 'Strike', [parse_strike(t) for t in df.index])
    if EXPIRY:
        df.insert(2, 'HasExpiryCode', [contains_expiry_code(t, EXPIRY) for t in df.index])

    df.sort_values(['CP', 'Strike'], inplace=True, na_position='last')

    # Nom de fichier
    out = OUT_CSV
    if out is None:
        safe_under = UNDERLYING.replace(' ', '_')
        stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        parts = [safe_under]
        if CP: parts.append(CP)
        if EXPIRY: parts.append(EXPIRY)
        if (MIN_STRIKE is not None) or (MAX_STRIKE is not None):
            parts.append(f"{MIN_STRIKE or ''}-{MAX_STRIKE or ''}")
        parts.append(stamp)
        out = ("_".join(p for p in parts if p)).strip("_") + ".csv"

    df.to_csv(out)
    print(f"[OK] Sauvegardé -> {out}")
    print(df.head(10))

if __name__ == "__main__":
    run()