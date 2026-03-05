"""
Gestion des fichiers (ouvrir, sauvegarder) pour AlarmPage.

Supporte :
  - Format JSON simple (version 1) : toutes les pages dans un seul fichier.
  - Auto-reload du dernier fichier ouvert au démarrage (via SettingsService).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, List, Dict

from PyQt6.QtWidgets import QFileDialog, QMessageBox

from alarm.services.settings_service import SettingsService

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QWidget


class FileHandler:
    """Gère save / load / auto-load pour AlarmPage."""

    def __init__(self, parent: QWidget) -> None:
        self._parent = parent
        self._settings = SettingsService()
        self._current_path: str | None = None

    # ── public API ────────────────────────────────────────────────────────────
    def save(self, pages: List[Dict]) -> None:
        """Sauvegarder — réutilise le dernier chemin, ou demande « Save As »."""
        if self._current_path:
            self._write(self._current_path, pages)
        else:
            self.save_as(pages)

    def save_as(self, pages: List[Dict]) -> None:
        """Sauvegarder sous…"""
        path, _ = QFileDialog.getSaveFileName(
            self._parent, "Sauvegarder", "", "JSON (*.json)"
        )
        if not path:
            return
        self._write(path, pages)
        self._current_path = path
        self._settings.set_last_workspace(path)
        self._settings.add_recent_workspace(path)

    def load(self) -> List[Dict] | None:
        """Ouvrir un fichier JSON — retourne la liste de pages ou None si annulé."""
        path, _ = QFileDialog.getOpenFileName(
            self._parent, "Ouvrir", "", "JSON (*.json)"
        )
        if not path:
            return None
        return self._read(path)

    def auto_load(self) -> List[Dict] | None:
        """Charge automatiquement le dernier fichier ouvert.
        Retourne la liste de pages ou None."""
        last = self._settings.get_last_workspace()
        if last and Path(last).is_file():
            try:
                return self._read(last)
            except Exception as e:
                print(f"[FileHandler] auto-load failed: {e}")
                self._settings.clear_last_workspace()
        return None

    @property
    def current_path(self) -> str | None:
        return self._current_path

    # ── internals ─────────────────────────────────────────────────────────────
    def _write(self, path: str, pages: List[Dict]) -> None:
        data = {
            "version": 1,
            "pages": [
                {
                    "name": p["name"],
                    "strategies": [s.to_dict() for s in p["strategies"]],
                }
                for p in pages
            ],
        }
        try:
            Path(path).write_text(
                json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        except Exception as e:
            QMessageBox.critical(
                self._parent, "Erreur de sauvegarde", str(e)
            )

    def _read(self, path: str) -> List[Dict]:
        """Lit un fichier JSON et retourne la liste de pages (dicts avec Strategy)."""
        from alarm.models.strategy import Strategy

        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        pages: List[Dict] = []
        for pd in raw.get("pages", []):
            strategies = [Strategy.from_dict(d) for d in pd.get("strategies", [])]
            pages.append({"name": pd["name"], "strategies": strategies})

        self._current_path = path
        self._settings.set_last_workspace(path)
        self._settings.add_recent_workspace(path)
        return pages
