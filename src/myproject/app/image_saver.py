"""
Module de sauvegarde d'images robuste pour les diagrammes de stratégies.
Gère la création des répertoires, les fallbacks et les erreurs.
"""
from pathlib import Path
from typing import List, Optional, Tuple
import numpy as np
import plotly.graph_objects as go




# Cache pour le répertoire de sortie
_OUTPUT_DIR: Optional[Path] = None


def get_output_directory() -> Path:
    """
    Retourne le répertoire de sortie pour les images.
    Crée le répertoire s'il n'existe pas.
    
    Returns:
        Path vers le répertoire de sortie
    """
    global _OUTPUT_DIR
    
    if _OUTPUT_DIR is not None and _OUTPUT_DIR.exists():
        return _OUTPUT_DIR
    
    # Essayer plusieurs emplacements possibles
    possible_dirs = []
    
    # 1. Relatif au fichier courant (app/image_saver.py -> assets/payoff_diagrams)
    current_file = Path(__file__).resolve()
    app_dir = current_file.parent  # app/
    myproject_dir = app_dir.parent  # myproject/
    src_dir = myproject_dir.parent  # src/
    project_root = src_dir.parent  # Option_Strategy/
    
    possible_dirs.append(project_root / "assets" / "payoff_diagrams")
    
    # 2. Depuis le répertoire de travail
    cwd = Path.cwd()
    possible_dirs.append(cwd / "assets" / "payoff_diagrams")
    
    # 3. Dossier temporaire utilisateur
    home = Path.home()
    possible_dirs.append(home / "Documents" / "Option_Strategy_Images")
    
    # 4. Temp système
    import tempfile
    possible_dirs.append(Path(tempfile.gettempdir()) / "option_strategy_images")
    
    # Essayer de créer chaque répertoire
    for output_dir in possible_dirs:
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            # Vérifier qu'on peut écrire dedans
            test_file = output_dir / ".write_test"
            test_file.write_text("test")
            test_file.unlink()
            _OUTPUT_DIR = output_dir
            return output_dir
        except Exception:
            continue
    
    # Fallback ultime: répertoire courant
    _OUTPUT_DIR = Path.cwd()
    return _OUTPUT_DIR

def save_figure_to_png(
    fig,
    filename: str,
    width: int = 1200,
    height: int = 700,
    scale: int = 2,
    background_white: bool = True
) -> Optional[str]:
    """
    Sauvegarde une figure Plotly en PNG de manière robuste.
    
    Args:
        fig: Figure Plotly à sauvegarder
        filename: Nom du fichier (sans extension si besoin, .png sera ajouté)
        width: Largeur en pixels
        height: Hauteur en pixels
        scale: Facteur d'échelle (2 = haute résolution)
        background_white: Si True, force un fond blanc
    
    Returns:
        Chemin complet du fichier sauvegardé, ou None si échec
    """
    if fig is None:
        print("[ImageSaver] Erreur: Figure est None")
        return None
    
    # S'assurer que le filename a l'extension .png
    if not filename.endswith('.png'):
        filename = f"{filename}.png"
    
    # Nettoyer le nom de fichier
    filename = "".join(c for c in filename if c.isalnum() or c in ('_', '-', '.'))
    
    # Obtenir le répertoire de sortie
    output_dir = get_output_directory()
    filepath = output_dir / filename
    
    # Appliquer fond blanc si demandé
    if background_white:
        fig.update_layout(
            plot_bgcolor="white",
            paper_bgcolor="white",
        )
    # Méthode 1: Essayer avec kaleido
    try:
        fig.write_image(str(filepath), width=width, height=height, scale=scale)
        print(f"[ImageSaver] ✓ Image sauvegardée: {filepath}")
        return str(filepath)
    except Exception as e:
        print(f"[ImageSaver] Erreur kaleido: {e}")

def save_payoff_diagram_png(
    comparisons: List,
    mixture: Tuple[np.ndarray, np.ndarray, float],
    filename: str = "payoff_diagram.png",
    max_strategies: int = 5
) -> Optional[str]:
    """
    Sauvegarde le diagramme de payoff.
    
    Args:
        comparisons: Liste de StrategyComparison
        mixture: Tuple (prices, probabilities, mean) optionnel
        filename: Nom du fichier
        max_strategies: Nombre max de stratégies à afficher (défaut: 5)
    
    Returns:
        Chemin du fichier sauvegardé ou None
    """
  
    limited_comparisons = comparisons[:max_strategies]
    # Import local pour éviter l'import circulaire
    from myproject.app.payoff_diagram import create_payoff_diagram
    fig = create_payoff_diagram(mixture, limited_comparisons)
    return save_figure_to_png(fig, filename, width=500, height=250)

def save_top10_summary(
    comparisons: List,
    filename: str = "top10_summary.png"
) -> Optional[str]:
    """
    Sauvegarde le résumé des top 10 stratégies.
    
    Returns:
        Chemin du fichier sauvegardé ou None
    """        
    top10 = comparisons[:10]
    
    if not top10:
        print("[ImageSaver] Aucune stratégie à afficher")
        return None
    
    # Préparer les données du tableau
    headers = ["Rank", "Strategy", "Score", "Premium", "Avg P&L", "Delta"]
    
    cells_data = [
        [str(i) for i in range(1, len(top10) + 1)],
        [c.strategy_name[:40] if hasattr(c, 'strategy_name') else "N/A" for c in top10],
        [f"{c.score:.4f}" if hasattr(c, 'score') else "N/A" for c in top10],
        [f"${c.premium:.2f}" if hasattr(c, 'premium') else "N/A" for c in top10],
        [f"${c.max_profit:.2f}" if hasattr(c, 'max_profit') else "N/A" for c in top10],
        [f"${c.average_pnl:.2f}" if hasattr(c, 'average_pnl') and c.average_pnl else "N/A" for c in top10],
        [f"{c.total_delta:.3f}" if hasattr(c, 'total_delta') else "N/A" for c in top10],
    ]
    
    # Alternance de couleurs pour les lignes
    row_colors = [['#f0f8ff' if i % 2 == 0 else 'white' for i in range(len(top10))] for _ in headers]
    
    fig = go.Figure(data=[go.Table(
        header=dict(
            values=[f"<b>{h}</b>" for h in headers],
            fill_color='#1f77b4',
            font=dict(color='white', size=12),
            align='center',
            height=35
        ),
        cells=dict(
            values=cells_data,
            fill_color=row_colors,
            font=dict(size=11),
            align=['center', 'left', 'center', 'right', 'right', 'right', 'center'],
            height=28
        )
    )])
    
    fig.update_layout(
        title=dict(text="<b>Top 10 Strategies Summary</b>", font=dict(size=16), x=0.5),
        width=1000,
        height=420,  # Plus grand pour 10 lignes
        margin=dict(l=20, r=20, t=50, b=20),
        paper_bgcolor='white'
    )
    
    return save_figure_to_png(fig, filename, width=1000, height=500)

def save_all_diagrams(
    comparisons: List,
    mixture: Tuple[np.ndarray, np.ndarray, float]
) -> dict:
    """
    Sauvegarde tous les diagrammes (payoff + summary)
    Returns:
        Dict avec les chemins des fichiers sauvegardés
    """
    results = {}
    
    if comparisons:
        results['payoff'] = save_payoff_diagram_png(comparisons, mixture)
        results['summary'] = save_top10_summary(comparisons)
    
    return results