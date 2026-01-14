import plotly.graph_objects as go

from typing import Dict, List, Optional, Tuple
from myproject.strategy.comparison_class import StrategyComparison
from myproject.option.option_class import Option
import numpy as np


def prepare_options_data(options: List[Option]) -> Dict[str, List[Option]]:
    """Separates calls and puts."""
    calls = [opt for opt in options if opt.option_type == "call"]
    puts = [opt for opt in options if opt.option_type == "put"]

    return {"calls": calls, "puts": puts}


def format_currency(value: float) -> str:
    """Formats a value as currency."""
    if value == float("inf"):
        return "Unlimited"
    return f"${value:.2f}"


def format_percentage(value: float) -> str:
    """Formats a percentage."""
    return f"{value:.1f}%"


def format_expiration_date(month: str, year: int) -> str:
    """
    Formats expiration date from Bloomberg month and year.

    Args:
        month: Bloomberg month code (F, G, H, K, M, N, Q, U, V, X, Z)
        year: Year (6 = 2026)

    Returns:
        Formatted date (ex: "Jun 2026")
    """
    month_names = {
        "F": "Jan",
        "G": "Feb",
        "H": "Mar",
        "K": "Apr",
        "M": "Jun",
        "N": "Jul",
        "Q": "Aug",
        "U": "Sep",
        "V": "Oct",
        "X": "Nov",
        "Z": "Dec",
    }

    month_name = month_names.get(month, month)
    full_year = 2020 + year

    return f"{month_name} {full_year}"


def create_payoff_diagram(
    comparisons: List[StrategyComparison],
    target_price: Optional[float] = None,
    mixture: Optional[Tuple[np.ndarray, np.ndarray]] = None,
):
    """
    Creates an interactive P&L diagram for all strategies with optional Gaussian mixture

    Args:
        comparisons: List of strategies to display
        target_price: Target price for vertical reference
        mixture: Tuple (prices, probabilities) for displaying Gaussian distribution (optional)

    Returns:
        Plotly figure with P&L curves and optionally the mixture
    """
    # Generate price range
    price_range = comparisons[0].prices
    if target_price is None:
        target_price = comparisons[0].target_price

    # Create a figure with two Y axes if mixture provided
    if mixture is not None:
        from plotly.subplots import make_subplots

        fig = make_subplots(rows=1, cols=1, specs=[[{"secondary_y": True}]])
    else:
        fig = go.Figure()

    # Reference lines
    if mixture is not None:
        fig.add_hline(
            y=0, line_dash="dash", line_color="gray", opacity=0.5, secondary_y=False
        )
        fig.add_vline(
            x=target_price,
            line_dash="dot",
            line_color="red",
            annotation_text="Target",
            opacity=0.7,
        )
    else:
        fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
        fig.add_vline(
            x=target_price,
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

    # Tracer chaque stratégie
    for idx, comp in enumerate(comparisons):
        color = colors[idx % len(colors)]

        # Calculer P&L (optimisé avec list comprehension)
        pnl_values = comp.pnl_array

        # Courbe P&L
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
    if mixture is not None:
        prices_mixture, probabilities = mixture

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
                hovertemplate="Prix: $%{x:.2f}<br>Probabilité: %{y:.4f}<extra></extra>",
                yaxis="y2",
            ),
            secondary_y=True,
        )

        # Calculer les statistiques de la mixture
        mean_price = np.average(prices_mixture, weights=probabilities)

        # Ajouter ligne de moyenne
        fig.add_vline(
            x=mean_price,
            line_dash="dash",
            line_color="gray",
            annotation_text=f"μ = {mean_price:.2f}",
            annotation_position="top right",
            opacity=0.5,
        )

    # Configuration du layout
    if mixture is not None:
        fig.update_layout(
            title="Diagramme de P&L à l'Expiration avec Distribution Gaussienne",
            xaxis_title="Prix du Sous-Jacent ($)",
            yaxis_title="Profit / Perte ($)",
            yaxis2_title="Densité de Probabilité",
            height=600,
            hovermode="x unified",
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
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
            title="Diagramme de P&L à l'Expiration",
            xaxis_title="Prix du Sous-Jacent ($)",
            yaxis_title="Profit / Perte ($)",
            height=500,
            hovermode="x unified",
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
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
    return fig


def create_single_strategy_payoff(
    strategy: StrategyComparison, target_price: float
) -> go.Figure:
    """
    Crée un diagramme P&L pour une seule stratégie.

    Args:
        strategy: Stratégie à afficher
        target_price: Prix cible pour la référence verticale

    Returns:
        Figure Plotly avec la courbe P&L
    """
    # Générer la plage de prix (±20% autour du prix cible)
    price_range = strategy.prices

    fig = go.Figure()

    # Lignes de référence
    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
    fig.add_vline(
        x=target_price,
        line_dash="dot",
        line_color="red",
        annotation_text="Target",
        opacity=0.7,
    )

    # Calculer P&L pour toute la plage de prix
    pnl_values = strategy.pnl_array
    # Courbe P&L
    fig.add_trace(
        go.Scatter(
            x=price_range,
            y=pnl_values,
            mode="lines",
            name=strategy.strategy_name,
            line=dict(color="#1f77b4", width=3),
            fill="tozeroy",
            fillcolor="rgba(31, 119, 180, 0.1)",
            hovertemplate="Prix: $%{x:.2f}<br>P&L: $%{y:.2f}<extra></extra>",
        )
    )

    # Markers de breakeven (si disponibles)
    if strategy.breakeven_points:
        fig.add_trace(
            go.Scatter(
                x=strategy.breakeven_points,
                y=[0] * len(strategy.breakeven_points),
                mode="markers",
                marker=dict(
                    size=12, color="red", symbol="circle-open", line=dict(width=3)
                ),
                name="Breakeven",
                hovertemplate="Breakeven: $%{x:.2f}<extra></extra>",
            )
        )

    # Marker au prix cible
    profit_at_target = strategy.profit_at_target
    fig.add_trace(
        go.Scatter(
            x=[target_price],
            y=[profit_at_target],
            mode="markers",
            marker=dict(size=15, color="green", symbol="star"),
            name="Prix Cible",
            hovertemplate=f"Target: ${target_price:.2f}<br>P&L: ${profit_at_target:.2f}<extra></extra>",
        )
    )

    # Configuration du layout
    fig.update_layout(
        title=f"P&L - {strategy.strategy_name}",
        xaxis_title="Prix du Sous-Jacent ($)",
        yaxis_title="Profit / Perte ($)",
        height=400,
        hovermode="x unified",
        showlegend=True,
        plot_bgcolor="white",
        xaxis=dict(gridcolor="lightgray"),
        yaxis=dict(gridcolor="lightgray", zeroline=True, zerolinecolor="gray"),
    )

    return fig
