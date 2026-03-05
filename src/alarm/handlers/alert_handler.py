"""
Gestion des alertes (son, popup, état des alertes).

Works with AlarmPage (table-based monitor).
"""
from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Callable, Optional

if sys.platform == "win32":
    import winsound

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QWidget


class AlertHandler:
    """Gère les alertes et notifications pour AlarmPage."""

    def __init__(self, parent: QWidget, continue_callback: Callable[[str], None]) -> None:
        self._parent = parent
        self._continue_callback = continue_callback
        self._alerted: set[str] = set()

    # ── public API ────────────────────────────────────────────────────────────
    def fire(
        self,
        strategy_id: str,
        strategy_name: str,
        current_price: Optional[float],
        target_price: float,
        is_inferior: bool,
    ) -> None:
        """Déclenche l'alerte complète (son + popup). Anti-spam intégré."""
        if strategy_id in self._alerted:
            return
        self._alerted.add(strategy_id)
        self.play_alert_sound()
        self._show_popup(strategy_name, current_price, target_price, is_inferior, strategy_id)

    def on_target_left(self, strategy_id: str) -> None:
        """Appelé quand le prix sort de la zone cible — réarme l'anti-spam."""
        self._alerted.discard(strategy_id)

    # ── son ───────────────────────────────────────────────────────────────────
    @staticmethod
    def play_alert_sound() -> None:
        """Joue un son d'alerte (cross-platform)."""
        try:
            if sys.platform == "win32":
                winsound.Beep(1000, 200)
                winsound.Beep(1500, 200)
            elif sys.platform == "darwin":
                import os
                os.system("afplay /System/Library/Sounds/Glass.aiff")
            else:
                import os
                os.system(
                    "paplay /usr/share/sounds/freedesktop/stereo/complete.oga 2>/dev/null "
                    "|| aplay /usr/share/sounds/alsa/Noise.wav 2>/dev/null"
                )
        except Exception:
            pass

    # ── popup ─────────────────────────────────────────────────────────────────
    def _show_popup(
        self,
        strategy_name: str,
        current_price: Optional[float],
        target_price: float,
        is_inferior: bool,
        strategy_id: str,
    ) -> None:
        from alarm.ui.alert_popup import AlertPopup

        popup = AlertPopup(
            strategy_name,
            current_price if current_price is not None else 0.0,
            target_price,
            is_inferior,
            strategy_id=strategy_id,
            continue_callback=self._on_continue,
            parent=self._parent,
        )
        popup.show()

    def _on_continue(self, strategy_id: str) -> None:
        """Callback du popup « Continuer l'alarme »."""
        self._alerted.discard(strategy_id)
        self._continue_callback(strategy_id)
