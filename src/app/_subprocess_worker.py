"""
Subprocess entry point — NO Qt imports.

This module is imported by the spawned Process.  Keeping it Qt-free prevents
the 0xC0000005 (access violation) crash that happens when PyQt6 tries to
initialise a display context inside a headless child process.
"""
from __future__ import annotations

import pickle
import sys
import tempfile
import traceback
from pathlib import Path
from typing import Any, Dict

TEMP_DIR = Path(tempfile.gettempdir()) / "option_strategy_results"
TEMP_DIR.mkdir(exist_ok=True)


def _result_path(session_id: str) -> Path:
    return TEMP_DIR / f"result_{session_id}.pkl"


def _error_path(session_id: str) -> Path:
    return TEMP_DIR / f"error_{session_id}.txt"


def run(session_id: str, params: Dict[str, Any]) -> None:
    """Called by multiprocessing.Process — no Qt imports anywhere in this file."""
    try:
        from main import process_bloomberg_to_strategies 

        result = process_bloomberg_to_strategies(
            brut_code=params.get("brut_code"),
            underlying=params["underlying"],
            months=params["months"],
            years=params["years"],
            strikes=params["strikes"],
            price_min=params["price_min"],
            price_max=params["price_max"],
            max_legs=params["max_legs"],
            scoring_weights=params["scoring_weights"],
            scenarios=params["scenarios"],
            filter=params["filter"],
            roll_expiries=params.get("roll_expiries"),
            recalibrate=params.get("recalibrate", True),
            vol_model=params.get("vol_model", "sabr"),
            leg_penalty=params.get("operation_penalisation", 0.0),
            prefilled_options=params.get("prefilled_options"),
        )
        with open(_result_path(session_id), "wb") as f:
            pickle.dump(result, f)
    except Exception as exc:
        with open(_error_path(session_id), "w") as f:
            f.write(f"{exc}\n\n{traceback.format_exc()}")
