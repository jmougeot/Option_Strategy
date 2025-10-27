"""
Strategy Manager - UI Components for Strategy Persistence
Gère l'affichage et l'interaction pour sauvegarder/charger les stratégies
"""

import streamlit as st
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Optional
from myproject.strategy.comparison_class import StrategyComparison
from myproject.strategy.strategy_persistence import (
    save_strategies_to_json,
    load_strategies_from_json,
    list_saved_strategies
)


def render_load_strategies_sidebar() -> Optional[Tuple[List[StrategyComparison], dict]]:
    """
    Affiche la section de chargement des stratégies dans la sidebar
    
    Returns:
        Tuple (strategies, metadata) si des stratégies sont chargées, None sinon
    """
    st.markdown("---")
    st.markdown("### 💾 Gestion des Stratégies")
    
    saved_files = list_saved_strategies()
    
    if saved_files:
        st.markdown("**Charger des stratégies :**")
        
        # Créer un selectbox avec les fichiers disponibles
        file_options = {f"{f['filename']} ({f['saved_at'][:10]})": f for f in saved_files}
        selected_file = st.selectbox(
            "Fichiers sauvegardés",
            options=list(file_options.keys()),
            key="load_strategies_select"
        )
        
        if st.button("📂 Charger", use_container_width=True, key="load_btn"):
            selected_info = file_options[selected_file]
            try:
                strategies, metadata = load_strategies_from_json(selected_info['filepath'])
                st.session_state['loaded_strategies'] = strategies
                st.session_state['loaded_metadata'] = metadata
                st.success(f"✅ {len(strategies)} stratégies chargées !")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Erreur lors du chargement : {str(e)}")
    else:
        st.info("Aucune stratégie sauvegardée trouvée")
    
    # Retourner les stratégies chargées si elles existent
    if 'loaded_strategies' in st.session_state:
        return st.session_state['loaded_strategies'], st.session_state.get('loaded_metadata', {})
    
    return None


def render_save_strategies_section(all_comparisons: List[StrategyComparison]) -> None:
    """
    Affiche la section pour sauvegarder les stratégies
    
    Args:
        all_comparisons: Liste des stratégies à sauvegarder
    """
    st.markdown("---")
    st.markdown("### 💾 Sauvegarder les Stratégies")
    
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        save_filename = st.text_input(
            "Nom du fichier (sans .json)",
            value=f"strategies_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            key="save_filename"
        )
    
    with col2:
        if st.button("💾 Sauvegarder", use_container_width=True, type="primary", key="save_btn"):
            try:
                # Créer le dossier saved_strategies s'il n'existe pas
                save_dir = Path("saved_strategies")
                save_dir.mkdir(exist_ok=True)
                
                # Créer le chemin complet
                filepath = save_dir / f"{save_filename}.json"
                
                # Préparer les métadonnées
                metadata = st.session_state.get('current_params', {})
                metadata['saved_at'] = datetime.now().isoformat()
                
                # Sauvegarder
                save_strategies_to_json(all_comparisons, str(filepath), metadata)
                
                st.success(f"✅ {len(all_comparisons)} stratégies sauvegardées dans {filepath}")
            except Exception as e:
                st.error(f"❌ Erreur lors de la sauvegarde : {str(e)}")
    
    with col3:
        st.write("")  # Espacement


def display_loaded_strategies_banner(strategies: List[StrategyComparison], metadata: dict) -> None:
    """
    Affiche une bannière indiquant que des stratégies sont chargées
    
    Args:
        strategies: Liste des stratégies chargées
        metadata: Métadonnées du fichier
    """
    col1, col2 = st.columns([3, 1])
    with col1:
        st.info(f"📂 **Stratégies chargées** : {len(strategies)} stratégies | "
                f"Sauvegardé le : {metadata.get('saved_at', 'Unknown')[:19]} | "
                f"Underlying : {metadata.get('underlying', 'Unknown')}")
    with col2:
        if st.button("🔄 Nouvelle Analyse", use_container_width=True):
            del st.session_state['loaded_strategies']
            if 'loaded_metadata' in st.session_state:
                del st.session_state['loaded_metadata']
            st.rerun()
