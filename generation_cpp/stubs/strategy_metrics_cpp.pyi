"""
Module optimisé pour les calculs de métriques de stratégies d'options
"""
from __future__ import annotations
import numpy
import numpy.typing
import typing
__all__: list[str] = ['init_options_cache', 'process_combinations_batch_with_multi_scoring', 'stop', 'reset_stop', 'is_stop_requested']
def init_options_cache(premiums: typing.Annotated[numpy.typing.ArrayLike, numpy.float64], deltas: typing.Annotated[numpy.typing.ArrayLike, numpy.float64], gammas: typing.Annotated[numpy.typing.ArrayLike, numpy.float64], vegas: typing.Annotated[numpy.typing.ArrayLike, numpy.float64], thetas: typing.Annotated[numpy.typing.ArrayLike, numpy.float64], ivs: typing.Annotated[numpy.typing.ArrayLike, numpy.float64], average_pnls: typing.Annotated[numpy.typing.ArrayLike, numpy.float64], sigma_pnls: typing.Annotated[numpy.typing.ArrayLike, numpy.float64], strikes: typing.Annotated[numpy.typing.ArrayLike, numpy.float64], is_calls: typing.Annotated[numpy.typing.ArrayLike, numpy.bool], rolls: typing.Annotated[numpy.typing.ArrayLike, numpy.float64], rolls_quarterly: typing.Annotated[numpy.typing.ArrayLike, numpy.float64], rolls_sum: typing.Annotated[numpy.typing.ArrayLike, numpy.float64], pnl_matrix: typing.Annotated[numpy.typing.ArrayLike, numpy.float64], prices: typing.Annotated[numpy.typing.ArrayLike, numpy.float64], mixture: typing.Annotated[numpy.typing.ArrayLike, numpy.float64], average_mix: typing.SupportsFloat) -> None:
    """
                  Initialise le cache global avec toutes les données des options.
                  Doit être appelé une seule fois avant process_combinations_batch.
    """
def process_combinations_batch_with_multi_scoring(n_legs: typing.SupportsInt, max_loss_left: typing.SupportsFloat, max_loss_right: typing.SupportsFloat, max_premium_params: typing.SupportsFloat, ouvert_gauche: typing.SupportsInt, ouvert_droite: typing.SupportsInt, min_premium_sell: typing.SupportsFloat, delta_min: typing.SupportsFloat, delta_max: typing.SupportsFloat, limit_left: typing.SupportsFloat, limit_right: typing.SupportsFloat, top_n: typing.SupportsInt = 10, weight_sets: list = []) -> dict:
    """
                  Génère les combinaisons et applique N systèmes de poids simultanément.
                  Retourne un dict avec per_set, consensus, n_weight_sets, n_candidates.
    """
def stop() -> None:
    """
                Arrete le processus en cours
    """
def reset_stop() -> None:
    """
                Reinitialise le flag d'arret
    """

def is_stop_requested() -> bool:
    """
                Verifie si un arret a ete demande
    """