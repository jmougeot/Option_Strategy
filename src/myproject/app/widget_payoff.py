from typing import List, Optional, Tuple
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import numpy as np
import streamlit as st

from myproject.strategy.strategy_class import StrategyComparison



def create_payoff_diagram(
    comparisons: List[StrategyComparison],
    mixture: Tuple[np.ndarray, np.ndarray, float],
    underlying_price: Optional[float] = None,
    key: Optional[str] = None,
):
    """
    Creates an interactive P&L diagram for all strategies with optional Gaussian mixture

    Args:
        comparisons: List of strategies to display
        mixture: Tuple (prices, probabilities, mean) for displaying Gaussian distribution
        underlying_price: Current price of the underlying asset (optional)

    Returns:
        Plotly figure with P&L curves and optionally the mixture
    """
    if not comparisons:
        return None

    # Generate price range
    price_range = comparisons[0].prices

    # Create a figure with two Y axes if mixture provided
    if mixture is not None:
        fig = make_subplots(rows=1, cols=1, specs=[[{"secondary_y": True}]])
    else:
        fig = go.Figure()

    # Reference lines
    if mixture is not None:
        fig.add_hline(
            y=0, line_dash="dash", line_color="gray", opacity=0.5, secondary_y=False
        )
    else:
        fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
        fig.add_vline(
            line_dash="dot",
            line_color="red",
            annotation_text="Target",
            opacity=0.7,
        )

    # Palette de couleurs
    colors = [
        "#1f77b4",
        "#ff7f0e",
        "#2ca02c",
        "#d62728",
        "#9467bd",
        "#8c564b",
        "#e377c2",
        "#7f7f7f",
        "#bcbd22",
        "#17becf",
    ]

    # Tracer chaque stratÃ©gie
    for idx, comp in enumerate(comparisons):
        color = colors[idx % len(colors)]

        # Calculer P&L (optimisÃ© avec list comprehension)
        pnl_values = comp.pnl_array        

        if mixture is not None:
            fig.add_trace(
                go.Scatter(
                    x=price_range,
                    y=pnl_values,
                    mode="lines",
                    name=comp.strategy_name,
                    line=dict(color=color, width=2.5),
                    hovertemplate="<b>%{fullData.name}</b><br>"
                    + "Prix: $%{x:.2f}<br>"
                    + "P&L: $%{y:.2f}<extra></extra>",
                ),
                secondary_y=False,
            )
        else:
            fig.add_trace(
                go.Scatter(
                    x=price_range,
                    y=pnl_values,
                    mode="lines",
                    name=comp.strategy_name,
                    line=dict(color=color, width=2.5),
                    hovertemplate="<b>%{fullData.name}</b><br>"
                    + "Prix: $%{x:.2f}<br>"
                    + "P&L: $%{y:.2f}<extra></extra>",
                )
            )

        # Markers de breakeven
        if comp.breakeven_points:
            if mixture is not None:
                fig.add_trace(
                    go.Scatter(
                        x=comp.breakeven_points,
                        y=[0] * len(comp.breakeven_points),
                        mode="markers",
                        marker=dict(
                            size=10,
                            color=color,
                            symbol="circle-open",
                            line=dict(width=2),
                        ),
                        showlegend=False,
                        hovertemplate="<b>Breakeven</b><br>Prix: $%{x:.2f}<extra></extra>",
                    ),
                    secondary_y=False,
                )
            else:
                fig.add_trace(
                    go.Scatter(
                        x=comp.breakeven_points,
                        y=[0] * len(comp.breakeven_points),
                        mode="markers",
                        marker=dict(
                            size=10,
                            color=color,
                            symbol="circle-open",
                            line=dict(width=2),
                        ),
                        showlegend=False,
                        hovertemplate="<b>Breakeven</b><br>Prix: $%{x:.2f}<extra></extra>",
                    )
                )

    # Ajouter la mixture gaussienne si fournie
    prices_mixture, probabilities, mean_price = mixture

    # Tracer la distribution sur l'axe Y secondaire
    fig.add_trace(
        go.Scatter(
            x=prices_mixture,
            y=probabilities,
            mode="lines",
            name="Distribution Gaussienne",
            fill="tozeroy",
            line=dict(color="rgba(128, 128, 128, 0.8)", width=2, dash="dot"),
            fillcolor="rgba(128, 128, 128, 0.2)",
            hovertemplate="Prix: $%{x:.2f}<br>ProbabilitÃ©: %{y:.4f}<extra></extra>",
            yaxis="y2",
        ),
        secondary_y=True,
    )

    # Ajouter ligne de moyenne
    fig.add_vline(
        x=mean_price,
        line_dash="dash",
        line_color="gray",
        annotation_text=f"Î¼ = {mean_price:.2f}",
        annotation_position="top right",
        opacity=0.5,
    )

    # Ajouter ligne du prix actuel du sous-jacent
    if underlying_price is not None:
        fig.add_vline(
            x=underlying_price,
            line_dash="solid",
            line_color="red",
            annotation_text=f"Spot = {underlying_price:.4f}",
            annotation_position="bottom right",
            opacity=0.7,
        )

    # RÃ©cupÃ©rer l'underlying depuis la premiÃ¨re stratÃ©gie si disponible
    underlying_label = ""
    if comparisons and len(comparisons) > 0:
        first_comp = comparisons[0]
        if first_comp.all_options and len(first_comp.all_options) > 0:
            first_opt = first_comp.all_options[0]
            if hasattr(first_opt, 'underlying_symbol') and first_opt.underlying_symbol:
                underlying_label = f" - {first_opt.underlying_symbol}"

    # Configuration du layout
    if mixture is not None:
        fig.update_layout(
            title=f"Diagramme de P&L à l'Expiration{underlying_label} avec Distribution Gaussienne",
            xaxis_title="Prix du Sous-Jacent ($)",
            yaxis_title="Profit / Perte ($)",
            yaxis2_title="DensitÃ© de ProbabilitÃ©",
            height=600,
            hovermode="x unified",
            legend=dict(
                orientation="h", 
                yanchor="bottom", 
                y=1.02, 
                xanchor="right", 
                x=1,
                font=dict(size=9),
                itemwidth=30,
            ),
            plot_bgcolor="rgba(0,0,0,0)",  # Fond transparent
            paper_bgcolor="rgba(0,0,0,0)",  # Papier transparent
            xaxis=dict(gridcolor="rgba(128,128,128,0.2)"),
            yaxis=dict(
                gridcolor="rgba(128,128,128,0.2)",
                zeroline=True,
                zerolinecolor="rgba(128,128,128,0.3)",
            ),
            yaxis2=dict(
                gridcolor="rgba(128,128,128,0.2)", overlaying="y", side="right"
            ),
        )
    else:
        fig.update_layout(
            title=f"Diagramme de P&L à l'Expiration{underlying_label}",
            xaxis_title="Prix du Sous-Jacent ($)",
            yaxis_title="Profit / Perte ($)",
            height=500,
            hovermode="x unified",
            legend=dict(
                orientation="h", 
                yanchor="bottom", 
                y=1.02, 
                xanchor="right", 
                x=1,
                font=dict(size=9),
                itemwidth=30,
            ),
            plot_bgcolor="rgba(0,0,0,0)",  # Fond transparent
            paper_bgcolor="rgba(0,0,0,0)",  # Papier transparent
            xaxis=dict(gridcolor="rgba(128,128,128,0.2)"),
            yaxis=dict(
                gridcolor="rgba(128,128,128,0.2)",
                zeroline=True,
                zerolinecolor="rgba(128,128,128,0.3)",
            ),
        )
    
    st.plotly_chart(fig, width="stretch", key=key)
    return fig