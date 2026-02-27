"""
Email utilities module for Options Strategy.
Provides clean pipelines for Outlook email and PDF generation.
"""
from typing import List, Optional
import numpy as np
import streamlit as st
from myproject.app.data_types import FutureData
from myproject.share_result.utils import EmailTemplateData
from myproject.share_result.generate_email import (open_outlook_with_email,)


def _build_strategy_details(best, ref_price_str, underlying, price_step):
    """Build strategy result line, market data, risk and payoff commentary from a StrategyComparison."""
    strategy_result = f"{best.strategy_name}"
    
    # Market data: "Mkt is <premium>, <delta>d, ref <ref_price>"
    delta_pct = int(best.total_delta * 100) if best.total_delta else 0
    delta_str = f"+{delta_pct}" if delta_pct >= 0 else f"{delta_pct}"
    market_data = f"Mkt is {best.premium:.2f}, {delta_str}d, ref {ref_price_str}"
    
    # Risk description from max_loss, max_profit and breakeven
    ticks_step = price_step * 100 if price_step else 1
    risk_parts = []
    if best.max_loss < -900:
        risk_parts.append("Unlimited loss on downside")
    else:
        loss_ticks = abs(best.max_loss) / price_step if price_step else abs(best.max_loss)
        risk_parts.append(f"Max loss of {loss_ticks:.1f} ticks on downside")
    
    if best.breakeven_points:
        bp_str = " / ".join(f"{bp:.4f}" for bp in best.breakeven_points)
        risk_parts.append(f"breakeven at {bp_str}")
    
    risk_description = ", ".join(risk_parts) if risk_parts else "Risk as per strategy structure"
    
    # Payoff commentary: locate the max profit zone
    payoff_commentary = ""
    if best.pnl_array is not None and best.prices is not None:
        max_pnl = float(np.max(best.pnl_array))
        if price_step and price_step > 0:
            max_ticks = max_pnl / price_step
            # Find the price range where PnL is at max (within 1 tick tolerance)
            threshold = max_pnl - price_step
            max_zone = best.prices[best.pnl_array >= threshold]
            if len(max_zone) >= 2:
                payoff_commentary = (
                    f"We love the payoff below where we make the max "
                    f"({max_ticks:.2f} ticks) between {max_zone[0]:.4f} and {max_zone[-1]:.4f}"
                )
    
    return strategy_result, market_data, risk_description, payoff_commentary


def build_email_template_data(params, filter, scoring_weights) -> EmailTemplateData:
    underlying = params.underlying or "Options"
    comparisons_list = st.session_state.get("comparisons", [])
    # Fallback: if comparisons not set directly, try to get from multi_ranking
    if not comparisons_list:
        multi_ranking = st.session_state.get("multi_ranking", None)
        if multi_ranking and hasattr(multi_ranking, 'all_strategies_flat'):
            comparisons_list = multi_ranking.all_strategies_flat()
    
    # ─── Determine best strategy ───
    best = comparisons_list[0] if comparisons_list else None
    
    # ─── Future data & ref price ───
    future_data_email = st.session_state.get("future_data", FutureData(None, None))
    ref_price = future_data_email.underlying_price if future_data_email else None
    ref_price_str = f"{ref_price:.4f}" if isinstance(ref_price, (int, float)) and ref_price is not None else "N/A"
    
    # ─── Strategy result, market data, risk, payoff commentary ───
    if best:
        strategy_result, market_data, risk_description, payoff_commentary = _build_strategy_details(
            best, ref_price_str, underlying, params.price_step
        )
    else:
        strategy_result = "No strategy found"
        market_data = ""
        risk_description = ""
        payoff_commentary = ""
    
    # ─── Selection criteria & roll/leverage descriptions ───
    selection_criteria = []
    roll_description = ""
    leverage_description = ""
    
    if best and comparisons_list:
        # Check if best strategy has the best roll
        roll_sorted = sorted(
            [c for c in comparisons_list if c.rolls_detail],
            key=lambda x: sum(c for c in x.rolls_detail.values()),
            reverse=True
        )
        if roll_sorted and roll_sorted[0] is best and best.rolls_detail:
            selection_criteria.append("ROLLS THE BEST")
            # Build roll description
            roll_parts = []
            for label, val in best.rolls_detail.items():
                ticks = val / params.price_step if params.price_step else val
                roll_parts.append(f"{label}: {ticks:.1f} ticks")
            roll_description = (
                f"This was chosen because it has the highest roll "
                f"({', '.join(roll_parts)})"
            )
        
        # Check if best strategy has the best leverage P&L
        lev_sorted = sorted(
            [c for c in comparisons_list if c.avg_pnl_levrage],
            key=lambda x: x.avg_pnl_levrage,
            reverse=True
        )
        if lev_sorted and lev_sorted[0] is best:
            selection_criteria.append(
                "WITH THE HIGHEST LEVERAGE PnL (highest expected PnL at exp for the premium paid)"
            )
            if params.price_step and params.price_step > 0:
                premium_ticks = best.premium / params.price_step
                avg_pnl_ticks = (best.average_pnl / params.price_step) if best.average_pnl else 0
                leverage_description = (
                    f"The highest leverage p&l of 1 for {best.avg_pnl_levrage:.1f} ticks, "
                    f"for a {best.premium:.2f} MID "
                    f"(with an avg pnl of {avg_pnl_ticks:.1f} ticks at expiry)"
                )
        
        # Fallback if no specific criteria matched
        if not selection_criteria:
            selection_criteria.append("HAS THE BEST OVERALL SCORE")
    
    # ─── Criteria section ───
    scenarios_list = st.session_state.get("scenarios", [])
    if scenarios_list:
        target_parts = []
        for s in scenarios_list:
            price = s.get("price", 0)
            std = s.get("std", 0)
            std_ticks = std / params.price_step if params.price_step else std
            target_parts.append(f"{price:.4f} (+/- {std_ticks:.1f} ticks)")
        target_desc = ", ".join(target_parts)
    else:
        target_desc = "N/A"
    tail_risk_desc = (
        f"{filter.max_loss_left:.2f} ticks max loss on downside; "
        f"{filter.max_loss_right:.2f} ticks max loss on upside"
    )
    max_risk_desc = (
        f"{filter.ouvert_gauche} net short put(s) allowed (downside), "
        f"{filter.ouvert_droite} net short call(s) allowed (upside)"
    )
    ticks_step = params.price_step * 100 if params.price_step else 0
    strikes_desc = (
        f"Looking at all options between {params.price_min:.4f} and {params.price_max:.4f}. "
        f"Every {ticks_step:.1f} ticks. "
        f"Cannot short any option for less than {filter.min_premium_sell:.3f}."
    )
    delta_desc = f"limited from {filter.delta_min * 100:.0f} to {filter.delta_max * 100:+.0f}d"
    premium_desc = f"{filter.max_premium:.2f} TICKS"

    return EmailTemplateData(
        underlying=underlying,
        reference_price=ref_price_str,
        strategy_result=strategy_result,
        market_data=market_data,
        risk_description=risk_description,
        selection_criteria=selection_criteria,
        roll_description=roll_description,
        leverage_description=leverage_description,
        payoff_commentary=payoff_commentary,
        target_description=target_desc,
        tail_risk_description=tail_risk_desc,
        max_risk_description=max_risk_desc,
        strikes_screened_description=strikes_desc,
        delta_description=delta_desc,
        premium_max_description=premium_desc,
        max_legs=params.max_legs,
    )

def create_email_with_images(
    template_data: EmailTemplateData,
    mixture: tuple,
    comparisons: Optional[List] = None,
    selected_comparisons: Optional[List] = None,
    fields: Optional[dict] = None,
    strat_data: Optional[List[dict]] = None,
    params=None,
) -> bool:
    """
    Create an Outlook email with one payoff image per selected strategy.

    Args:
        template_data        : EmailTemplateData base
        comparisons          : Full comparison list (legacy)
        selected_comparisons : Strategies chosen on the Email page — one payoff PNG per entry
        mixture              : Tuple (prices, probs, mean)
        fields               : Dict of form values from the Email page
        strat_data           : List of per-strategy dicts (line, commentary, stats …)
        params               : UIParams

    Returns:
        True if email was opened successfully
    """
    from myproject.share_result.image_saver import save_payoff_single_strategy

    # ── Generate one payoff PNG per selected strategy ────────────────────────
    payoff_images: List[str] = []
    strats_to_plot = selected_comparisons or comparisons or []
    _future = st.session_state.get("future_data", None)
    spot = _future.underlying_price if (_future and _future.underlying_price) else None

    for i, comp in enumerate(strats_to_plot):
        try:
            fname = f"payoff_strat_{i+1}_{comp.strategy_name[:20].replace(' ', '_')}.png"
            path  = save_payoff_single_strategy(comp, mixture, fname, underlying_price=spot)
            if path:
                payoff_images.append(path)
                print(f"[Email] Payoff {i+1} saved: {path}")
        except Exception as e:
            print(f"[Email] Error saving payoff {i+1}: {e}")

    # ── Open Outlook ─────────────────────────────────────────────────────────
    success = open_outlook_with_email(
        template_data=template_data,
        payoff_images=payoff_images,
        fields=fields,
        strat_data=strat_data,
    )

    if not success:
        print("[Email] Could not open Outlook.")
        for img in payoff_images:
            print(f"   - {img}")

    return success
