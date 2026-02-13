"""
Onglet History - Historique des recherches avec possibilité de restauration
Persistance JSON pour conserver l'historique entre les sessions
"""

import streamlit as st
from datetime import datetime
from typing import Dict, Any, List
from dataclasses import dataclass, field
import json
import uuid
from pathlib import Path


# Chemin du fichier d'historique (à la racine du projet)
HISTORY_FILE = Path(__file__).parent.parent.parent.parent.parent / "search_history.json"


@dataclass
class HistoryEntry:
    """Une entrée dans l'historique des recherches."""
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
    # Données pour restauration des paramètres
    params: Dict[str, Any] = field(default_factory=dict)
    scenarios: List[Dict] = field(default_factory=list)
    filter_data: Dict[str, Any] = field(default_factory=dict)
    scoring_weights: Any = field(default_factory=dict)  # Dict[str,float] or List[Dict[str,float]]
    # Résumé des top stratégies (pour affichage, sérialisable en JSON)
    top_strategies_summary: List[Dict] = field(default_factory=list)
    # Données runtime (non persistées en JSON)
    comparisons: List[Any] = field(default_factory=list)
    mixture: Any = None
    future_data: Any = None


def save_history_to_json():
    """Sauvegarde l'historique dans un fichier JSON."""
    if "search_history" not in st.session_state:
        return
    
    history_data = []
    for entry in st.session_state.search_history:
        # Convertir en dict, en excluant les objets non-sérialisables
        entry_dict = {
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
        }
        history_data.append(entry_dict)
    
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Erreur sauvegarde historique: {e}")


def load_history_from_json() -> List[HistoryEntry]:
    """Charge l'historique depuis le fichier JSON."""
    if not HISTORY_FILE.exists():
        return []
    
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
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
        print(f"Erreur chargement historique: {e}")
        return []


def init_history():
    """Initialise l'historique dans session_state si nécessaire.
    
    Au tout premier lancement (session_state vierge), charge le JSON
    et restaure automatiquement la dernière entrée pour retrouver
    l'état de la session précédente.
    """
    if "search_history" not in st.session_state:
        # Charger depuis JSON au démarrage
        st.session_state.search_history = load_history_from_json()
    
    # Initialiser le flag de restauration pendante
    if "pending_restore" not in st.session_state:
        # Premier lancement → restaurer automatiquement la dernière entrée
        if st.session_state.search_history:
            st.session_state.pending_restore = st.session_state.search_history[0]
        else:
            st.session_state.pending_restore = None


def add_to_history(
    params: Dict[str, Any],
    comparisons: List[Any],
    mixture: Any,
    future_data: Any,
    scenarios: List[Dict],
    filter_data: Dict[str, Any],
    scoring_weights: Any
):
    """Ajoute une recherche à l'historique."""
    init_history()
    
    # Générer un ID unique basé sur le timestamp
    timestamp = datetime.now()
    entry_id = timestamp.strftime("%Y%m%d_%H%M%S")
    
    # Extraire les infos principales
    underlying = params.get("underlying", "N/A")
    months = params.get("months", [])
    years = params.get("years", [])
    price_min = params.get("price_min", 0)
    price_max = params.get("price_max", 0)
    max_legs = params.get("max_legs", 0)
    
    # Meilleure stratégie
    best_strategy = "N/A"
    best_score = 0.0
    num_strategies = len(comparisons) if comparisons else 0
    
    # Créer un résumé des top stratégies (sérialisable en JSON)
    top_strategies_summary = []
    if comparisons:
        for i, comp in enumerate(comparisons[:10]):
            summary = {
                "rank": i + 1,
                "name": getattr(comp, 'strategy_name', 'N/A'),
                "score": getattr(comp, 'score', 0.0),
                "average_pnl": getattr(comp, 'average_pnl', 0.0),
                "premium": getattr(comp, 'premium', 0.0),
                "max_loss": getattr(comp, 'max_loss', 0.0),
            }
            top_strategies_summary.append(summary)
        
        best = comparisons[0]
        best_strategy = getattr(best, 'strategy_name', 'N/A')
        best_score = getattr(best, 'score', 0.0)
    
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
        comparisons=comparisons,  # Garde en mémoire pour la session courante
        mixture=mixture,
        future_data=future_data,
        scenarios=scenarios,
        filter_data=filter_data,
        scoring_weights=scoring_weights,
        top_strategies_summary=top_strategies_summary,
    )
    
    # Ajouter en tête de liste (plus récent en premier)
    st.session_state.search_history.insert(0, entry)
    
    # Limiter à 20 entrées
    if len(st.session_state.search_history) > 20:
        st.session_state.search_history = st.session_state.search_history[:20]
    
    # Sauvegarder en JSON
    save_history_to_json()


def apply_pending_restore():
    """
    Applique une restauration pendante. 
    Doit être appelé AU DÉBUT de main() avant la création des widgets.
    Met à jour directement les clés des widgets pour que les changements soient visibles.
    """
    if "pending_restore" not in st.session_state:
        return
    
    entry = st.session_state.pending_restore
    if entry is None:
        return
    
    # =========================================================================
    # RESTAURER LES SCÉNARIOS
    # =========================================================================
    if entry.scenarios:
        # D'abord, effacer les anciennes clés de widgets des anciens scénarios
        if "scenarios" in st.session_state:
            for old_scenario in st.session_state.scenarios:
                old_id = old_scenario.get("id", "")
                # Supprimer les anciennes clés de widget
                keys_to_remove = [
                    f"price_{old_id}", f"std_{old_id}", f"std_l_{old_id}", 
                    f"std_r_{old_id}", f"weight_{old_id}", f"delete_{old_id}"
                ]
                for key in keys_to_remove:
                    if key in st.session_state:
                        del st.session_state[key]
        
        # Copier les nouveaux scénarios
        st.session_state.scenarios = [s.copy() for s in entry.scenarios]
        
        # Migration: ajouter un id aux scénarios qui n'en ont pas
        for scenario in st.session_state.scenarios:
            if "id" not in scenario:
                scenario["id"] = str(uuid.uuid4())
        
        # Mettre à jour les clés des widgets pour chaque scénario
        for scenario in st.session_state.scenarios:
            scenario_id = scenario.get("id", "")
            if scenario_id:
                st.session_state[f"price_{scenario_id}"] = float(scenario.get("price", 98.0))
                st.session_state[f"std_{scenario_id}"] = float(scenario.get("std", 0.10))
                st.session_state[f"std_l_{scenario_id}"] = float(scenario.get("std", 0.10))
                st.session_state[f"std_r_{scenario_id}"] = float(scenario.get("std_r", scenario.get("std", 0.10)))
                st.session_state[f"weight_{scenario_id}"] = float(scenario.get("weight", 50.0))
    
    # =========================================================================
    # RESTAURER LES FILTRES
    # =========================================================================
    if entry.filter_data:
        filter_data = entry.filter_data
        
        # Reconstruire un dict filter complet avec les defaults pour les clés manquantes
        defaults = {
            "max_loss_right": 0.1,
            "max_loss_left": 0.1, 
            "max_premium": 5.0, 
            "ouvert_gauche": 0, 
            "ouvert_droite": 0, 
            "min_premium_sell": 0.005,
            "delta_min": -0.75,
            "delta_max": 0.75,
            "limit_left_filter": 98.5,
            "limit_right_filter": 98,
        }
        full_filter = {**defaults, **filter_data}
        st.session_state.filter = full_filter
        
        # Mapping: clé du dict filter -> clé du widget streamlit
        filter_widget_keys = {
            "max_loss_left": "filter_max_loss",
            "max_loss_right": "filter_max_loss_right",
            "limit_left_filter": "limit_left_filter_key",
            "limit_right_filter": "limit_right_filter_key",
            "max_premium": "filter_max_premium",
            "min_premium_sell": "filter_min_premium_sell",
            "ouvert_gauche": "filter_ouvert_gauche",
            "ouvert_droite": "filter_ouvert_droite",
            "delta_min": "delta_min",
            "delta_max": "delta_max",
        }
        
        for filter_key, widget_key in filter_widget_keys.items():
            if filter_key in full_filter:
                st.session_state[widget_key] = full_filter[filter_key]
    
    # =========================================================================
    # RESTAURER LES POIDS DE SCORING
    # =========================================================================
    if entry.scoring_weights:
        from myproject.app.widget_scoring import RANKING_PRESETS, ALL_FIELDS
        
        # Support both old Dict and new List[Dict] format
        ws_list = entry.scoring_weights if isinstance(entry.scoring_weights, list) else [entry.scoring_weights]
        
        # Ajouter un id à chaque weight set pour compatibilité avec le widget
        for ws in ws_list:
            if "id" not in ws:
                ws["id"] = str(uuid.uuid4())
        
        # Stocker comme custom weight sets
        st.session_state["custom_weight_sets"] = ws_list
        
        # Désactiver tous les presets : mettre à jour le dict ET les clés widget
        st.session_state["preset_active"] = {name: False for name in RANKING_PRESETS}
        for name in RANKING_PRESETS:
            st.session_state[f"preset_cb_{name}"] = False
        
        # Mettre à jour les widget keys des custom weight sets
        for ws in ws_list:
            weight_id = ws["id"]
            for field_name in ALL_FIELDS:
                val = ws.get(field_name, 0.0)
                st.session_state[f"custom_ws_{weight_id}_{field_name}"] = int(float(val) * 100)
    
    # =========================================================================
    # RESTAURER LES PARAMÈTRES (underlying, price, max_legs, etc.)
    # =========================================================================
    if entry.params:
        params = entry.params
        
        # Underlying
        if "underlying" in params:
            st.session_state["param_underlying"] = params["underlying"]
        
        # Years (convertir en string séparé par virgules)
        if "years" in params:
            years_list = params["years"]
            if isinstance(years_list, list):
                st.session_state["param_years"] = ", ".join(str(y) for y in years_list)
        
        # Months (convertir en string séparé par virgules)
        if "months" in params:
            months_list = params["months"]
            if isinstance(months_list, list):
                st.session_state["param_months"] = ", ".join(months_list)
        
        # Price min/max/step
        if "price_min" in params:
            st.session_state["param_price_min"] = float(params["price_min"])
        if "price_max" in params:
            st.session_state["param_price_max"] = float(params["price_max"])
        if "price_step" in params:
            st.session_state["param_price_step"] = float(params["price_step"])
        
        # Max legs
        if "max_legs" in params:
            st.session_state["param_max_legs"] = int(params["max_legs"])
        
        # Brut code
        brut_code = params.get("brut_code")
        if brut_code and isinstance(brut_code, list) and len(brut_code) > 0:
            st.session_state["brut_code_check"] = True
            st.session_state["param_brut_code"] = ", ".join(brut_code)
        else:
            st.session_state["brut_code_check"] = False
        
        # Roll expiries
        roll_expiries = params.get("roll_expiries")
        if roll_expiries and isinstance(roll_expiries, list) and len(roll_expiries) > 0:
            st.session_state["param_custom_roll"] = True
            # Reconstruire le string "H6, Z5" à partir de [["H", 6], ["Z", 5]]
            roll_parts = []
            for roll in roll_expiries:
                if isinstance(roll, (list, tuple)) and len(roll) == 2:
                    roll_parts.append(f"{roll[0]}{roll[1]}")
            st.session_state["param_roll_input"] = ", ".join(roll_parts)
        else:
            st.session_state["param_custom_roll"] = False
    
    # =========================================================================
    # RESTAURER LES RÉSULTATS (si disponibles)
    # =========================================================================
    if entry.comparisons:
        st.session_state.comparisons = entry.comparisons
        st.session_state.mixture = entry.mixture
        st.session_state.future_data = entry.future_data
    
    # Marquer comme restauré
    st.session_state.restored_from_history = entry.id
    
    # Effacer la restauration pendante
    st.session_state.pending_restore = None


def request_restore(entry: HistoryEntry):
    """Demande une restauration (sera appliquée au prochain rerun)."""
    st.session_state.pending_restore = entry


def clear_history():
    """Efface tout l'historique."""
    st.session_state.search_history = []
    save_history_to_json()


def delete_history_entry(entry_id: str):
    """Supprime une entrée spécifique de l'historique."""
    if "search_history" not in st.session_state:
        return
    
    st.session_state.search_history = [
        e for e in st.session_state.search_history if e.id != entry_id
    ]
    save_history_to_json()


def run():
    """Affiche l'onglet historique."""
    init_history()
    
    st.header("📜 Historique des Recherches")
    
    history = st.session_state.search_history
    
    if not history:
        st.info("Aucune recherche dans l'historique. Lancez une comparaison pour commencer.")
        st.markdown("""
        **💾 Persistance:** L'historique est sauvegardé automatiquement dans `search_history.json` 
        et persiste entre les sessions.
        """)
        return
    
    # Bouton pour effacer l'historique
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🗑️ Effacer tout", type="secondary"):
            clear_history()
            st.rerun()
    
    with col1:
        st.markdown(f"**{len(history)} recherche(s)** — 💾 Sauvegardé automatiquement")
    
    st.markdown("---")
    
    # Afficher chaque entrée
    for i, entry in enumerate(history):
        with st.container():
            # En-tête de l'entrée
            col_info, col_action = st.columns([4, 1])
            
            with col_info:
                # Badge si c'est l'entrée actuellement restaurée
                is_current = st.session_state.get("restored_from_history") == entry.id
                current_badge = " 🔵 **(actif)**" if is_current else ""
                
                # Indique si les résultats complets sont disponibles (session courante)
                has_results = bool(entry.comparisons)
                results_badge = " ✅" if has_results else " 📋"
                
                st.markdown(f"### 🕐 {entry.timestamp}{current_badge}{results_badge}")
                
                # Infos principales en colonnes
                info_col1, info_col2, info_col3 = st.columns(3)
                
                with info_col1:
                    months_str = ", ".join(entry.months) if entry.months else "N/A"
                    years_str = ", ".join(str(y) for y in entry.years) if entry.years else "N/A"
                    st.markdown(f"""
                    **Sous-jacent:** `{entry.underlying}`  
                    **Mois/Années:** {months_str} / {years_str}
                    """)
                
                with info_col2:
                    st.markdown(f"""
                    **Prix:** {entry.price_range}  
                    **Max legs:** {entry.max_legs}
                    """)
                
                with info_col3:
                    best_name = entry.best_strategy[:25] + "..." if len(entry.best_strategy) > 25 else entry.best_strategy
                    st.markdown(f"""
                    **Stratégies:** {entry.num_strategies}  
                    **Meilleure:** `{best_name}`
                    """)
            
            with col_action:
                st.markdown("")  # Espacement
                # Boutons Restaurer et Supprimer
                btn_col1, btn_col2 = st.columns(2)
                with btn_col1:
                    help_text = "Restaure paramètres + résultats" if has_results else "Restaure les paramètres (relancer pour les résultats)"
                    if st.button("📂", key=f"restore_{entry.id}", type="primary", help=help_text):
                        request_restore(entry)
                        st.rerun()
                with btn_col2:
                    if st.button("🗑️", key=f"delete_{entry.id}", type="secondary", help="Supprimer cette entrée"):
                        delete_history_entry(entry.id)
                        st.rerun()
            
            # Détails supplémentaires dans un expander
            with st.expander("📋 Voir les détails"):
                detail_col1, detail_col2 = st.columns(2)
                
                with detail_col1:
                    st.markdown("**Scénarios utilisés:**")
                    if entry.scenarios:
                        for j, scenario in enumerate(entry.scenarios):
                            price = scenario.get('price', 'N/A')
                            std = scenario.get('std', 'N/A')
                            weight = scenario.get('weight', 'N/A')
                            st.markdown(f"- Scénario {j+1}: Target={price}, σ={std}, Prob={weight}%")
                    else:
                        st.markdown("- Non disponible")
                
                with detail_col2:
                    st.markdown("**Filtres:**")
                    if entry.filter_data:
                        max_loss_l = entry.filter_data.get('max_loss_left', 'N/A')
                        max_loss_r = entry.filter_data.get('max_loss_right', 'N/A')
                        delta_min = entry.filter_data.get('delta_min', 'N/A')
                        delta_max = entry.filter_data.get('delta_max', 'N/A')
                        st.markdown(f"""
                        - Max Loss: {max_loss_l} / {max_loss_r}
                        - Delta: [{delta_min}, {delta_max}]
                        """)
                    else:
                        st.markdown("- Non disponible")
                
                st.markdown("**Poids de scoring:**")
                if entry.scoring_weights:
                    ws_list = entry.scoring_weights if isinstance(entry.scoring_weights, list) else [entry.scoring_weights]
                    for wi, ws in enumerate(ws_list):
                        ws_str = ", ".join(f"{k}: {v:.0%}" for k, v in ws.items() if v > 0)
                        label = f"Set {wi+1}: " if len(ws_list) > 1 else ""
                        st.markdown(f"- {label}{ws_str}" if ws_str else "- Aucun poids actif")
                
                # Top stratégies (depuis résumé JSON ou comparisons en mémoire)
                st.markdown("**Top 5 des stratégies:**")
                if entry.comparisons and len(entry.comparisons) > 0:
                    # Données en mémoire (session courante)
                    for j, comp in enumerate(entry.comparisons[:5]):
                        name = getattr(comp, 'strategy_name', 'N/A')
                        score = getattr(comp, 'score', 0)
                        pm = getattr(comp, 'average_pnl', 0)
                        st.markdown(f"{j+1}. `{name}` - Score: {score:.4f}, PM: {pm:.4f}")
                elif entry.top_strategies_summary:
                    # Données depuis JSON (session précédente)
                    for strat in entry.top_strategies_summary[:5]:
                        name = strat.get('name', 'N/A')
                        score = strat.get('score', 0)
                        pm = strat.get('average_pnl', 0)
                        st.markdown(f"{strat.get('rank', '?')}. `{name}` - Score: {score:.4f}, PM: {pm:.4f}")
                else:
                    st.markdown("- Non disponible")
            
            st.markdown("---")
