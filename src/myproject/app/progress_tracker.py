"""
Module de gestion de la progression pour l'interface Streamlit
===============================================================
Affiche une barre de progression avec les différentes étapes du traitement.
"""

import streamlit as st
from typing import Optional, Callable
from dataclasses import dataclass
from enum import Enum


class ProcessingStep(Enum):
    """Étapes du traitement."""
    INIT = "init"
    FETCH_DATA = "fetch_data"
    GENERATE_1_LEG = "generate_1_leg"
    GENERATE_2_LEG = "generate_2_leg"
    GENERATE_3_LEG = "generate_3_leg"
    GENERATE_4_LEG = "generate_4_leg"
    GENERATE_5_LEG = "generate_5_leg"
    GENERATE_6_LEG = "generate_6_leg"
    RANKING = "ranking"
    DISPLAY = "display"
    COMPLETE = "complete"


@dataclass
class StepInfo:
    """Information sur une étape."""
    name: str
    description: str
    progress: float  # 0.0 à 1.0


# Configuration des étapes avec leurs poids relatifs
STEPS_CONFIG = {
    ProcessingStep.INIT: StepInfo("Initialisation", "Préparation du traitement...", 0.0),
    ProcessingStep.FETCH_DATA: StepInfo("Récupération", "📡 Récupération des données Bloomberg...", 0.10),
    ProcessingStep.GENERATE_1_LEG: StepInfo("1 Leg", "🔄 Génération des stratégies 1 leg...", 0.20),
    ProcessingStep.GENERATE_2_LEG: StepInfo("2 Legs", "🔄 Génération des stratégies 2 legs...", 0.35),
    ProcessingStep.GENERATE_3_LEG: StepInfo("3 Legs", "🔄 Génération des stratégies 3 legs...", 0.50),
    ProcessingStep.GENERATE_4_LEG: StepInfo("4 Legs", "🔄 Génération des stratégies 4 legs...", 0.65),
    ProcessingStep.GENERATE_5_LEG: StepInfo("5 Legs", "🔄 Génération des stratégies 5 legs...", 0.75),
    ProcessingStep.GENERATE_6_LEG: StepInfo("6 Legs", "🔄 Génération des stratégies 6 legs...", 0.82),
    ProcessingStep.RANKING: StepInfo("Ranking", "🏆 Classement des stratégies...", 0.90),
    ProcessingStep.DISPLAY: StepInfo("Affichage", "📊 Préparation de l'affichage...", 0.95),
    ProcessingStep.COMPLETE: StepInfo("Terminé", "✅ Traitement terminé!", 1.0),
}


class ProgressTracker:
    """
    Gestionnaire de progression pour suivre et afficher l'avancement du traitement.
    Utilise les éléments Streamlit pour l'affichage.
    """
    
    def __init__(self, max_legs: int = 4):
        """
        Initialise le tracker de progression.
        
        Args:
            max_legs: Nombre maximum de legs (pour calculer les étapes)
        """
        self.max_legs = max_legs
        self.current_step = ProcessingStep.INIT
        self.progress_bar = None
        self.status_text = None
        self.detail_text = None
        self.stats_container = None
        self._initialized = False
        
    def init_ui(self):
        """Initialise les éléments UI de Streamlit."""
        if self._initialized:
            return
            
        # Conteneur principal pour la progression
        self.progress_container = st.container()
        
        with self.progress_container:
            st.markdown("### 🚀 Traitement en cours")
            
            # Barre de progression
            self.progress_bar = st.progress(0)
            
            # Texte de statut
            self.status_text = st.empty()
            
            # Détails supplémentaires
            self.detail_text = st.empty()
            
            # Statistiques en temps réel
            self.stats_container = st.empty()
            
        self._initialized = True
    
    def update(self, step: ProcessingStep, detail: str, stats: dict = None):
        """
        Met à jour la progression.
        
        Args:
            step: Étape actuelle
            detail: Détail supplémentaire à afficher
            stats: Statistiques à afficher (optionnel)
        """
        if not self._initialized:
            self.init_ui()
            
        self.current_step = step
        step_info = STEPS_CONFIG.get(step, STEPS_CONFIG[ProcessingStep.INIT])
        
        # Mise à jour de la barre de progression
        self.progress_bar.progress(step_info.progress)
        
        # Mise à jour du texte de statut
        self.status_text.markdown(f"**{step_info.description}**")
        
        # Mise à jour des détails
        if detail:
            self.detail_text.markdown(f"*{detail}*")
        else:
            self.detail_text.empty()
        
        # Mise à jour des statistiques
        if stats:
            stats_md = self._format_stats(stats)
            self.stats_container.markdown(stats_md)
    
    def update_substep(self, progress: float, detail: str = "", current: int = None, total: int = None):
        """
        Met à jour la sous-progression dans une étape.
        
        Args:
            progress: Progression dans l'étape actuelle (0.0 à 1.0)
            detail: Détail à afficher
            current: Nombre actuel de stratégies traitées (optionnel)
            total: Nombre total de stratégies à traiter (optionnel)
        """
        if not self._initialized:
            return
            
        # Calculer la progression globale en interpolant
        current_info = STEPS_CONFIG.get(self.current_step)
        
        # Trouver l'étape suivante
        steps_list = list(ProcessingStep)
        current_idx = steps_list.index(self.current_step)
        next_idx = min(current_idx + 1, len(steps_list) - 1)
        next_step = steps_list[next_idx]
        next_info = STEPS_CONFIG.get(next_step)
        
        if current_info and next_info:
            # Interpoler entre l'étape actuelle et la suivante
            global_progress = current_info.progress + progress * (next_info.progress - current_info.progress)
            self.progress_bar.progress(min(global_progress, 1.0))
        
        if detail:
            # Format avec compteur [current / total] si fourni
            if current is not None and total is not None:
                pct = int(progress * 100)
                detail_formatted = f"[{current:,} / {total:,}] {detail} ({pct}%)"
            else:
                detail_formatted = detail
            self.detail_text.markdown(f"*{detail_formatted}*")
    
    def _format_stats(self, stats: dict) -> str:
        """Formate les statistiques en markdown."""
        lines = ["📈 **Statistiques:**"]
        
        if "nb_options" in stats:
            lines.append(f"- Options analyzed: **{stats['nb_options']}**")
        if "nb_strategies_1_leg" in stats:
            lines.append(f"- Stratégies 1 leg: **{stats['nb_strategies_1_leg']}**")
        if "nb_strategies_2_leg" in stats:
            lines.append(f"- Stratégies 2 legs: **{stats['nb_strategies_2_leg']}**")
        if "nb_strategies_3_leg" in stats:
            lines.append(f"- Stratégies 3 legs: **{stats['nb_strategies_3_leg']}**")
        if "nb_strategies_4_leg" in stats:
            lines.append(f"- Stratégies 4 legs: **{stats['nb_strategies_4_leg']}**")
        if "nb_strategies_totales" in stats:
            lines.append(f"- Distinct combinations generated: {stats['nb_strategies_possibles']:,}")
        if "nb_strategies_totales" in stats:
            lines.append(f"- Strategies ranked: {stats['nb_strategies_totales']:,}")
        if "nb_strategies_classees" in stats:
            lines.append(f"- Top-ranked strategies: **{stats['nb_strategies_classees']}**")
        return "\n".join(lines)
    
    def complete(self, stats: dict = None):
        """Marque le traitement comme terminé."""
        self.update(ProcessingStep.COMPLETE, "", stats=stats)
    
    def error(self, message: str):
        """Affiche une erreur."""
        if self._initialized:
            self.progress_bar.progress(0)
            self.status_text.markdown(f"**❌ Erreur**")
            self.detail_text.markdown(f"*{message}*")
            with self.progress_container:
                st.error(message)
    
    def clear(self):
        """Efface les éléments de progression."""
        if self._initialized:
            self.progress_container.empty()
            self._initialized = False


def get_step_for_leg(n_legs: int) -> ProcessingStep:
    """Retourne l'étape correspondant au nombre de legs."""
    mapping = {
        1: ProcessingStep.GENERATE_1_LEG,
        2: ProcessingStep.GENERATE_2_LEG,
        3: ProcessingStep.GENERATE_3_LEG,
        4: ProcessingStep.GENERATE_4_LEG,
        5: ProcessingStep.GENERATE_5_LEG,
        6: ProcessingStep.GENERATE_6_LEG,
    }
    return mapping.get(n_legs, ProcessingStep.GENERATE_4_LEG)
