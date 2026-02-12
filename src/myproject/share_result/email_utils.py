"""
Email utilities module for Options Strategy.
Provides clean pipelines for Outlook email and PDF generation.
"""
from typing import List, Optional
import streamlit as st
from myproject.app.data_types import FutureData
from myproject.share_result.utils import EmailTemplateData
from myproject.share_result.generate_email import (open_outlook_with_email,)

def build_email_template_data(params, filter, scoring_weights) -> EmailTemplateData:
    underlying = params.underlying or "Options"
    comparisons_list = st.session_state.get("comparisons", [])
    best_strategies = []

    if comparisons_list and len(comparisons_list) > 0:
        best_overall = comparisons_list[0]
        delta_pct = int(best_overall.total_delta * 100) if best_overall.total_delta else 0
        delta_str = f"+{delta_pct}%" if delta_pct >= 0 else f"{delta_pct}%"
        best_strategies.append({
            "label": "Best strategy overall with the weighted score",
            "description": f"{best_overall.strategy_name} {best_overall.premium:.2f} Mid Price, {delta_str} delta"
        })

        roll_sorted = sorted([c for c in comparisons_list if hasattr(c, 'roll_pnl') and c.roll_pnl],
                                key=lambda x: x.roll_pnl[0] if x.roll_pnl else 0, reverse=True)
        if roll_sorted:
            best_roll = roll_sorted[0]
            delta_pct = int(best_roll.total_delta * 100) if best_roll.total_delta else 0
            delta_str = f"+{delta_pct}%" if delta_pct >= 0 else f"{delta_pct}%"
            best_strategies.append({
                "label": "Best strategy for Roll (first selected expiry)",
                "description": f"{best_roll.strategy_name} {best_roll.premium:.2f} Mid Price, {delta_str} delta"
            })

        pnl_sorted = sorted([c for c in comparisons_list if c.average_pnl],
                            key=lambda x: x.average_pnl or 0, reverse=True)
        if pnl_sorted:
            best_pnl = pnl_sorted[0]
            delta_pct = int(best_pnl.total_delta * 100) if best_pnl.total_delta else 0
            delta_str = f"+{delta_pct}%" if delta_pct >= 0 else f"{delta_pct}%"
            best_strategies.append({
                "label": "Best strategy regarding net average P&L gain at expiry",
                "description": f"{best_pnl.strategy_name} {best_pnl.premium:.2f} Mid Price, {delta_str} delta"
            })

    target_desc = f"Target defined by scenarios in the UI for {underlying}."
    tail_risk_desc = "Tail risk constraints as defined in filters."
    max_risk_desc = f"Open exposure left: {filter.ouvert_gauche}, right: {filter.ouvert_droite}"
    strikes_desc = f"Looking at all options between {params.price_min:.4f} and {params.price_max:.4f}. Step: {params.price_step:.4f}. Min premium to sell: {filter.min_premium_sell:.3f}."
    delta_desc = f"Limited from {filter.delta_min:.0f} to {filter.delta_max:.0f} delta"
    premium_desc = f"{filter.max_premium:.2f} max"
    max_loss_desc = f"{filter.max_loss_left:.2f} on downside / {filter.max_loss_right:.2f} on upside"
    weighting_desc = " | ".join(
        ", ".join(f"{k}: {v:.0%}" for k, v in ws.items() if v > 0)
        for ws in scoring_weights
    ) if scoring_weights else "default"

    future_data_email = st.session_state.get("future_data", FutureData(0, None))
    ref_price = future_data_email.underlying_price if future_data_email else "N/A"
    ref_price_str = f"{ref_price:.4f}" if isinstance(ref_price, (int, float)) else str(ref_price)

    return EmailTemplateData(
        underlying=underlying,
        reference_price=ref_price_str,
        target_description=target_desc,
        tail_risk_description=tail_risk_desc,
        max_risk_description=max_risk_desc,
        strikes_screened_description=strikes_desc,
        delta_description=delta_desc,
        premium_max_description=premium_desc,
        max_loss_description=max_loss_desc,
        weighting_description=weighting_desc,
        max_legs=params.max_legs,
        best_strategies=best_strategies,
    )

def create_email_with_images(
    template_data: EmailTemplateData,
    mixture: tuple,
    comparisons: Optional[List] = None,
) -> bool:
    """
    Create an Outlook email with embedded images.
    Single pipeline for Outlook email.
    
    Args:
        template_data: EmailTemplateData with all parameters
        comparisons: List of StrategyComparison (to generate images)
        mixture: Tuple of mixture (for the diagram)
    
    Returns:
        True if email was opened successfully
    """
    images = []
    
    # Generate images if we have the data
    if comparisons:
        try:
            from myproject.share_result.image_saver import save_all_diagrams
            print("[Email DEBUG] image_saver imported")
            
            saved_images = save_all_diagrams(comparisons, mixture)
            print(f"[Email DEBUG] save_all_diagrams returns: {saved_images}")
            
            if saved_images.get('payoff'):
                images.append(saved_images['payoff'])
                print(f"[Email DEBUG] Payoff added: {saved_images['payoff']}")
            
            if saved_images.get('summary'):
                images.append(saved_images['summary'])
                print(f"[Email DEBUG] Summary added: {saved_images['summary']}")
                
        except Exception as e:
            print(f"[Email DEBUG] Error generating images: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("[Email DEBUG] No comparisons provided - no images to generate")
    
    print(f"[Email DEBUG] Final images list: {images}")
    
    # Open Outlook with the template and images
    success = open_outlook_with_email(
        template_data=template_data,
        images=images
    )
    
    if not success:
        print("[Email] ❌ Could not open Outlook.")
        if images:
            print("[Email] Generated images:")
            for img in images:
                print(f"   - {img}")
    
    return success
