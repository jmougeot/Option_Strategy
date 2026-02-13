"""
Overview Page — Strategy comparison results, metrics & payoff diagrams.
"""

import streamlit as st
import uuid
from typing import Dict, List
from streamlit_autorefresh import st_autorefresh
from myproject.app.tabs import display_overview_tab
from myproject.app.widget_payoff import create_payoff_diagram
from myproject.async_processing import start_processing, check_processing_status, stop_processing
from myproject.app.data_types import FilterData, FutureData
from myproject.app.widget_params import UIParams
from myproject.strategy.multi_ranking import MultiRankingResult

def _build_weight_set_names(weight_list: List[Dict[str, float]]) -> List[str]:
    from myproject.app.widget_scoring import RANKING_PRESETS
    names: List[str] = []
    custom_idx = 0
    for ws in weight_list:
        active = {k: v for k, v in ws.items() if v > 0}
        matched = False
        for preset_name, preset_weights in RANKING_PRESETS.items():
            if active == preset_weights:
                names.append(preset_name)
                matched = True
                break
        if not matched:
            custom_idx += 1
            names.append(f"Custom #{custom_idx}")
    return names


def format_large_number(n):
    if n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.1f}Billion"
    elif n >= 1_000_000:
        return f"{n / 1_000_000:.1f}Million"
    elif n >= 1_000:
        return f"{n / 1_000:.1f}K"
    else:
        return str(n)


def run():
    """Main Overview page content."""

    # Retrieve sidebar data stored in session_state by app.py
    params: UIParams = st.session_state.get("_params_widget") #type: ignore
    scenarios = st.session_state.get("_scenarios_widget")
    filter: FilterData = st.session_state.get("_filter_widget") #type: ignore
    scoring_weights = st.session_state.get("_scoring_weights", [])

    # ========================================================================
    # Processing Controls
    # ========================================================================

    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())[:8]
    if "processing" not in st.session_state:
        st.session_state.processing = False
    if "process" not in st.session_state:
        st.session_state.process = None

    def on_stop_click():
        if st.session_state.process is not None:
            stop_processing(st.session_state.process)
            st.session_state.processing = False
            st.session_state.process = None

    compare_col, stop_col = st.columns(2)
    with compare_col:
        compare_button = st.button(
            "Run Comparison",
            type="primary",
            width="stretch",
            disabled=st.session_state.processing,
        )
    with stop_col:
        st.button("STOP", type="secondary", width="stretch", on_click=on_stop_click)

    all_comparisons = None

    # ------------------------------------------------------------------
    # Check running process
    # ------------------------------------------------------------------
    if st.session_state.processing and st.session_state.process is not None:
        is_running, is_complete, result, error = check_processing_status(
            st.session_state.session_id, st.session_state.process
        )
        if is_complete:
            st.session_state.processing = False
            st.session_state.process = None

            if error:
                if "terminated" in error.lower():
                    st.warning("Processing was terminated by user")
                else:
                    st.error(f"Error: {error}")
                return

            if result:
                best_strategies, stats, mixture, future_data = result

                if not best_strategies:
                    st.error("No strategy generated")
                    return

                multi_result = best_strategies
                multi_result.weight_set_names = _build_weight_set_names(scoring_weights)
                all_comparisons = multi_result.all_strategies_flat()
                st.session_state["multi_ranking"] = multi_result
                st.session_state["mixture"] = mixture
                st.session_state["future_data"] = future_data
                st.session_state["stats"] = stats 

                # Save to history
                from myproject.app.pages.history import add_to_history

                _params_for_history = {
                    "underlying": params.underlying,
                    "months": params.months,
                    "years": params.years,
                    "price_min": params.price_min,
                    "price_max": params.price_max,
                    "price_step": params.price_step,
                    "max_legs": params.max_legs,
                    "roll_expiries": params.roll_expiries,
                    "brut_code": params.brut_code,
                }
                _filter_for_history = {
                    "max_loss_left": filter.max_loss_left,
                    "max_loss_right": filter.max_loss_right,
                    "max_premium": filter.max_premium,
                    "delta_min": filter.delta_min,
                    "delta_max": filter.delta_max,
                    "ouvert_gauche": filter.ouvert_gauche,
                    "ouvert_droite": filter.ouvert_droite,
                    "min_premium_sell": filter.min_premium_sell,
                    "limit_left_filter": filter.limit_left,
                    "limit_right_filter": filter.limit_right,
                    "premium_only": filter.premium_only,
                }
                add_to_history(
                    params=_params_for_history,
                    comparisons=all_comparisons,
                    mixture=mixture,
                    future_data=future_data,
                    scenarios=st.session_state.get("scenarios", []),
                    filter_data=_filter_for_history,
                    scoring_weights=scoring_weights,
                )

                nb_screened = stats.get("nb_strategies_possibles", 0)
                nb_options = stats.get("nb_options", 0)
                nb_kept = stats.get("nb_strategies_classees", 0)
                st.success(
                    f"Processing complete! Screened **{format_large_number(nb_screened)}** "
                    f"strategies from {nb_options} options → Kept **{nb_kept}** best"
                )
            else:
                st.warning("Processing was terminated")
                return
        else:
            st.info("Processing in progress... Click STOP to terminate immediately.")
            st_autorefresh(interval=1000, limit=None, key="processing_refresh")

    elif compare_button and not st.session_state.processing:
        st.session_state.processing = True
        _params = {
            "brut_code": params.brut_code,
            "underlying": params.underlying,
            "months": params.months,
            "years": params.years,
            "strikes": params.strikes,
            "price_min": params.price_min,
            "price_max": params.price_max,
            "max_legs": params.max_legs,
            "scoring_weights": scoring_weights,
            "scenarios": scenarios,
            "filter": filter,
            "roll_expiries": params.roll_expiries,
        }
        process = start_processing(st.session_state.session_id, _params)
        st.session_state.process = process
        st.info("Starting processing...")
        st.rerun()

    # ------------------------------------------------------------------
    # Display results
    # ------------------------------------------------------------------
    if not all_comparisons:
        return

    mixture = st.session_state.get("mixture")

    # Future / stats bar
    future_data = st.session_state.get("future_data", FutureData(0, None))
    stats = st.session_state.get("stats", {})

    if future_data or stats:
        col_price, col_date, col_screened = st.columns(3)
        with col_price:
            if future_data:
                st.metric("Underlying Price", f"{future_data.underlying_price:.4f}")
        with col_date:
            if future_data:
                date_str = future_data.last_tradable_date if future_data.last_tradable_date else "N/A"
                st.metric("Last Tradeable Date", date_str)
        with col_screened:
            if stats:
                nb_screened = stats.get("nb_strategies_possibles", 0)
                st.metric("Strategies Screened", format_large_number(nb_screened))

    roll_labels = [f"{m}{y}" for m, y in params.roll_expiries] if params.roll_expiries else None
    underlying_price = future_data.underlying_price if future_data else 0

    multi_ranking: MultiRankingResult | None = st.session_state.get("multi_ranking", None)
    if multi_ranking is not None and multi_ranking.is_multi:
        sub_tab_names = ["Meta Ranking"] + [
            multi_ranking.get_set_label(i) for i in range(multi_ranking.n_sets)
        ]
        sub_tabs = st.tabs(sub_tab_names)
        with sub_tabs[0]:
            display_overview_tab(all_comparisons, roll_labels=roll_labels)
            create_payoff_diagram(all_comparisons[:5], mixture, underlying_price, key="payoff_consensus")
        for i in range(multi_ranking.n_sets):
            with sub_tabs[i + 1]:
                set_comps = multi_ranking.per_set_strategies[i]
                display_overview_tab(set_comps, roll_labels=roll_labels)
                create_payoff_diagram(set_comps[:5], mixture, underlying_price, key=f"payoff_set_{i}")
    else:
        display_overview_tab(all_comparisons, roll_labels=roll_labels)
        create_payoff_diagram(all_comparisons[:5], mixture, underlying_price, key="payoff_single")
