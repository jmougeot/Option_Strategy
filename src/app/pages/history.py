"""
History utilities — pure Python, no Streamlit dependency.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import json
import uuid

# JSON file stored at project root
HISTORY_FILE = Path(__file__).parent.parent.parent.parent / "search_history.json"


@dataclass
class HistoryEntry:
    """One entry in the search history."""
    id: str
    timestamp: str
    underlying: str
    months: List[str]
    years: List[int]
    price_range: str
    max_legs: int
    num_strategies: int
    best_strategy: str
    best_score: float
    params: Dict[str, Any] = field(default_factory=dict)
    scenarios: List[Dict] = field(default_factory=list)
    filter_data: Dict[str, Any] = field(default_factory=dict)
    scoring_weights: Any = field(default_factory=dict)
    top_strategies_summary: List[Dict] = field(default_factory=list)
    # Runtime fields (not persisted)
    comparisons: List[Any] = field(default_factory=list)
    mixture: Any = None
    future_data: Any = None


def save_history_to_json(history: List[HistoryEntry]) -> None:
    """Persist a list of HistoryEntry objects to the JSON file."""
    data = []
    for entry in history:
        data.append({
            "id": entry.id,
            "timestamp": entry.timestamp,
            "underlying": entry.underlying,
            "months": entry.months,
            "years": entry.years,
            "price_range": entry.price_range,
            "max_legs": entry.max_legs,
            "num_strategies": entry.num_strategies,
            "best_strategy": entry.best_strategy,
            "best_score": entry.best_score,
            "params": entry.params,
            "scenarios": entry.scenarios,
            "filter_data": entry.filter_data,
            "scoring_weights": entry.scoring_weights,
            "top_strategies_summary": entry.top_strategies_summary,
        })
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"History save error: {e}")


def load_history_from_json() -> List[HistoryEntry]:
    """Load history entries from the JSON file."""
    if not HISTORY_FILE.exists():
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            history_data = json.load(f)
        entries = []
        for data in history_data:
            entry = HistoryEntry(
                id=data.get("id", ""),
                timestamp=data.get("timestamp", ""),
                underlying=data.get("underlying", ""),
                months=data.get("months", []),
                years=data.get("years", []),
                price_range=data.get("price_range", ""),
                max_legs=data.get("max_legs", 0),
                num_strategies=data.get("num_strategies", 0),
                best_strategy=data.get("best_strategy", ""),
                best_score=data.get("best_score", 0.0),
                params=data.get("params", {}),
                scenarios=data.get("scenarios", []),
                filter_data=data.get("filter_data", {}),
                scoring_weights=data.get("scoring_weights", {}),
                top_strategies_summary=data.get("top_strategies_summary", []),
            )
            entries.append(entry)
        return entries
    except Exception as e:
        print(f"History load error: {e}")
        return []


def add_to_history(
    history: List[HistoryEntry],
    params: Dict[str, Any],
    comparisons: List[Any],
    mixture: Any,
    future_data: Any,
    scenarios: List[Dict],
    filter_data: Dict[str, Any],
    scoring_weights: Any,
    max_entries: int = 20,
) -> List[HistoryEntry]:
    """Add a new entry to the history list and persist to JSON."""
    timestamp = datetime.now()
    entry_id = timestamp.strftime("%Y%m%d_%H%M%S")

    underlying = params.get("underlying", "N/A")
    months = params.get("months", [])
    years = params.get("years", [])
    price_min = params.get("price_min", 0)
    price_max = params.get("price_max", 0)
    max_legs = params.get("max_legs", 0)

    top_strategies_summary = []
    best_strategy = "N/A"
    best_score = 0.0
    num_strategies = len(comparisons) if comparisons else 0

    if comparisons:
        for i, comp in enumerate(comparisons[:10]):
            top_strategies_summary.append({
                "rank": i + 1,
                "name": getattr(comp, "strategy_name", "N/A"),
                "score": getattr(comp, "score", 0.0),
                "average_pnl": getattr(comp, "average_pnl", 0.0),
                "premium": getattr(comp, "premium", 0.0),
                "max_loss": getattr(comp, "max_loss", 0.0),
            })
        best = comparisons[0]
        best_strategy = getattr(best, "strategy_name", "N/A")
        best_score = getattr(best, "score", 0.0)

    entry = HistoryEntry(
        id=entry_id,
        timestamp=timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        underlying=underlying,
        months=months,
        years=years,
        price_range=f"{price_min:.4f} - {price_max:.4f}",
        max_legs=max_legs,
        num_strategies=num_strategies,
        best_strategy=best_strategy,
        best_score=best_score,
        params=params,
        comparisons=comparisons,
        mixture=mixture,
        future_data=future_data,
        scenarios=scenarios,
        filter_data=filter_data,
        scoring_weights=scoring_weights,
        top_strategies_summary=top_strategies_summary,
    )

    # Clear heavy runtime data from older entries
    for old in history:
        old.comparisons = []
        old.mixture = None
        old.future_data = None

    updated = [entry] + list(history)
    if len(updated) > max_entries:
        updated = updated[:max_entries]

    save_history_to_json(updated)
    return updated
