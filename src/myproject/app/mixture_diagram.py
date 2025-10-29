import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np

from typing import Dict, List, Tuple, Optional
from myproject.strategy.comparison_class import StrategyComparison
from myproject.option.option_class import Option


def create_mixture_diagram(
    mixture: Tuple[np.ndarray, np.ndarray],
    target_price: Optional[float] = None,
    title: str = "Distribution de Probabilité Gaussienne (Mixture)"
) -> go.Figure:
    """
    Crée un diagramme de la mixture gaussienne.
    
    Args:
        mixture: Tuple (prices, probabilities) - grille de prix et densité de probabilité
        target_price: Prix cible à afficher (optionnel)
        title: Titre du graphique
        
    Returns:
        Figure Plotly avec la mixture gaussienne
    """
    if mixture is None or len(mixture) != 2:
        # Créer une figure vide si pas de mixture
        fig = go.Figure()
        fig.add_annotation(
            text="Aucune mixture disponible",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=16, color="gray")
        )
        return fig
    
    prices, probabilities = mixture
    
    # Créer la figure
    fig = go.Figure()
    
    # Tracer la distribution de probabilité
    fig.add_trace(go.Scatter(
        x=prices,
        y=probabilities,
        mode='lines',
        name='Distribution',
        fill='tozeroy',
        line=dict(color='#1f77b4', width=2),
        fillcolor='rgba(31, 119, 180, 0.3)'
    ))
    
    # Ajouter une ligne verticale pour le prix cible si fourni
    if target_price is not None:
        fig.add_vline(
            x=target_price,
            line_dash="dot",
            line_color="red",
            annotation_text=f"Target: {target_price:.2f}",
            annotation_position="top",
            opacity=0.7
        )
    
    # Calculer les statistiques
    mean_price = np.average(prices, weights=probabilities)
    variance = np.average((prices - mean_price)**2, weights=probabilities)
    std_dev = np.sqrt(variance)
    
    # Ajouter la moyenne
    fig.add_vline(
        x=mean_price,
        line_dash="dash",
        line_color="green",
        annotation_text=f"Moyenne: {mean_price:.2f}",
        annotation_position="bottom",
        opacity=0.7
    )
    
    # Mise en forme
    fig.update_layout(
        title=title,
        xaxis_title="Prix du Sous-jacent",
        yaxis_title="Densité de Probabilité",
        hovermode='x unified',
        showlegend=True,
        height=400,
        template='plotly_white'
    )
    
    # Ajouter les statistiques dans une annotation
    stats_text = f"μ = {mean_price:.2f}<br>σ = {std_dev:.2f}"
    fig.add_annotation(
        text=stats_text,
        xref="paper", yref="paper",
        x=0.98, y=0.98,
        xanchor='right', yanchor='top',
        showarrow=False,
        bgcolor="rgba(255, 255, 255, 0.8)",
        bordercolor="gray",
        borderwidth=1,
        font=dict(size=11)
    )
    
    return fig


def create_pnl_with_mixture_diagram(
    strategy: StrategyComparison,
    mixture: Optional[Tuple[np.ndarray, np.ndarray]] = None
) -> go.Figure:
    """
    Crée un diagramme P&L avec la mixture gaussienne superposée.
    
    Args:
        strategy: Stratégie à afficher
        mixture: Tuple (prices, probabilities) optionnel
        
    Returns:
        Figure Plotly avec P&L et mixture
    """
    fig = go.Figure()
    
    # Calculer le P&L de la stratégie
    if hasattr(strategy, 'all_options') and strategy.all_options:
        # Utiliser les prix de la première option qui a une mixture
        prices = None
        for opt in strategy.all_options:
            if hasattr(opt, 'prices') and opt.prices is not None:
                prices = opt.prices
                break
        
        if prices is not None:
            # Calculer le P&L total
            pnl_total = np.zeros_like(prices)
            for opt in strategy.all_options:
                if hasattr(opt, 'pnl_array') and opt.pnl_array is not None:
                    pnl_total += opt.pnl_array
            
            # Tracer le P&L
            fig.add_trace(go.Scatter(
                x=prices,
                y=pnl_total,
                mode='lines',
                name='P&L',
                line=dict(color='blue', width=2),
                yaxis='y1'
            ))
            
            # Ajouter la ligne zéro
            fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
    
    # Superposer la mixture si disponible
    if mixture is not None and len(mixture) == 2:
        prices_mix, probabilities = mixture
        
        # Normaliser les probabilités pour l'affichage (axe secondaire)
        prob_normalized = probabilities / probabilities.max()
        
        fig.add_trace(go.Scatter(
            x=prices_mix,
            y=prob_normalized,
            mode='lines',
            name='Distribution',
            fill='tozeroy',
            line=dict(color='rgba(255, 127, 14, 0.6)', width=1),
            fillcolor='rgba(255, 127, 14, 0.2)',
            yaxis='y2'
        ))
    
    # Mise en forme avec double axe Y
    fig.update_layout(
        title=f"P&L avec Distribution - {strategy.strategy_name}",
        xaxis_title="Prix du Sous-jacent",
        yaxis_title="P&L ($)",
        yaxis2=dict(
            title="Densité (normalisée)",
            overlaying='y',
            side='right',
            showgrid=False
        ),
        hovermode='x unified',
        showlegend=True,
        height=500,
        template='plotly_white'
    )
    
    return fig


def display_mixture_statistics(mixture: Optional[Tuple[np.ndarray, np.ndarray]]) -> None:
    """
    Affiche les statistiques de la mixture dans Streamlit.
    
    Args:
        mixture: Tuple (prices, probabilities)
    """
    if mixture is None or len(mixture) != 2:
        st.warning("⚠️ Aucune mixture disponible")
        return
    
    prices, probabilities = mixture
    
    # Calculer les statistiques
    mean_price = np.average(prices, weights=probabilities)
    variance = np.average((prices - mean_price)**2, weights=probabilities)
    std_dev = np.sqrt(variance)
    
    # Calculer les percentiles
    cumulative = np.cumsum(probabilities)
    cumulative /= cumulative[-1]  # Normaliser à 1
    
    p5 = prices[np.searchsorted(cumulative, 0.05)]
    p25 = prices[np.searchsorted(cumulative, 0.25)]
    p50 = prices[np.searchsorted(cumulative, 0.50)]
    p75 = prices[np.searchsorted(cumulative, 0.75)]
    p95 = prices[np.searchsorted(cumulative, 0.95)]
    
    # Afficher dans des colonnes
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Moyenne (μ)", f"{mean_price:.2f}")
        st.metric("Médiane (P50)", f"{p50:.2f}")
    
    with col2:
        st.metric("Écart-type (σ)", f"{std_dev:.2f}")
        st.metric("Intervalle P25-P75", f"{p25:.2f} - {p75:.2f}")
    
    with col3:
        st.metric("Min (P5)", f"{p5:.2f}")
        st.metric("Max (P95)", f"{p95:.2f}")




