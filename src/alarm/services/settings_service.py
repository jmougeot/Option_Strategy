"""
Service de gestion des paramètres de l'application
Stocke les préférences utilisateur (dernier workspace, etc.)
"""
import json
from pathlib import Path
from typing import Optional


class SettingsService:
    """Gère les paramètres persistants de l'application"""
    
    # Fichier de settings dans le dossier utilisateur
    SETTINGS_FILE = Path.home() / ".strategy_monitor_settings.json"
    
    _instance: Optional['SettingsService'] = None
    
    def __new__(cls):
        """Singleton pattern"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._settings = {}
            cls._instance._load()
        return cls._instance
    
    def _load(self):
        """Charge les paramètres depuis le fichier"""
        try:
            if self.SETTINGS_FILE.exists():
                with open(self.SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    self._settings = json.load(f)
        except Exception:
            self._settings = {}
    
    def _save(self):
        """Sauvegarde les paramètres dans le fichier"""
        try:
            with open(self.SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self._settings, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Erreur sauvegarde settings: {e}")
    
    def get_last_workspace(self) -> Optional[str]:
        """Retourne le chemin du dernier workspace utilisé"""
        return self._settings.get('last_workspace')
    
    def set_last_workspace(self, path: str):
        """Définit le chemin du dernier workspace utilisé"""
        self._settings['last_workspace'] = path
        self._save()
    
    def get_recent_workspaces(self) -> list[str]:
        """Retourne la liste des workspaces récents"""
        return self._settings.get('recent_workspaces', [])
    
    def add_recent_workspace(self, path: str):
        """Ajoute un workspace à la liste des récents"""
        recent = self.get_recent_workspaces()
        
        # Supprimer si déjà présent
        if path in recent:
            recent.remove(path)
        
        # Ajouter en premier
        recent.insert(0, path)
        
        # Limiter à 10 entrées
        self._settings['recent_workspaces'] = recent[:10]
        self._save()
    
    def clear_last_workspace(self):
        """Efface le dernier workspace"""
        if 'last_workspace' in self._settings:
            del self._settings['last_workspace']
            self._save()
