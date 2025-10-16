"""
Bloomberg Connection Management
===============================
Gestion de la connexion au Bloomberg Terminal API (blpapi).

Ce module centralise toute la logique de connexion/déconnexion,
permettant de réutiliser la session à travers différents modules.

Auteur: BGC Trading Desk
Date: 2025-10-16
"""

import blpapi
from typing import Optional


class BloombergConnection:
    """
    Gestionnaire de connexion Bloomberg avec pattern Context Manager.
    
    Usage basique:
        conn = BloombergConnection()
        conn.connect()
        # ... utiliser conn.session ...
        conn.disconnect()
    
    Usage avec context manager (recommandé):
        with BloombergConnection() as conn:
            # ... utiliser conn.session ...
            pass
        # Déconnexion automatique
    
    Attributs:
        session: Session blpapi active (None si non connecté)
        service: Service Bloomberg "//blp/refdata" (None si non connecté)
    """
    
    def __init__(self, host: str = "localhost", port: int = 8194):
        """
        Initialise les paramètres de connexion.
        
        Args:
            host: Adresse du Bloomberg Terminal (défaut: localhost)
            port: Port de connexion (défaut: 8194)
        
        Note:
            Le Bloomberg Terminal doit être lancé et connecté avant d'utiliser l'API.
        """
        self.host = host
        self.port = port
        self.session: Optional[blpapi.Session] = None
        self.service: Optional[blpapi.Service] = None
    
    def connect(self) -> bool:
        """
        Établit la connexion au Bloomberg Terminal.
        
        Returns:
            True si connexion réussie, False sinon
        
        Raises:
            ConnectionError: Si le Terminal n'est pas accessible
        
        Exemple:
            >>> conn = BloombergConnection()
            >>> if conn.connect():
            ...     print("Connecté à Bloomberg")
            ... else:
            ...     print("Erreur de connexion")
        """
        # Créer les options de session
        sessionOptions = blpapi.SessionOptions()
        sessionOptions.setServerHost(self.host)
        sessionOptions.setServerPort(self.port)
        
        # Créer et démarrer la session
        self.session = blpapi.Session(sessionOptions)
        
        if not self.session.start():
            raise ConnectionError(
                f"Impossible de démarrer la session Bloomberg sur {self.host}:{self.port}. "
                "Vérifiez que le Bloomberg Terminal est lancé et connecté."
            )
        
        # Ouvrir le service de données de référence
        if not self.session.openService("//blp/refdata"):
            raise ConnectionError("Impossible d'ouvrir le service //blp/refdata")
        
        # Récupérer le service pour les requêtes futures
        self.service = self.session.getService("//blp/refdata")
        
        return True
    
    def disconnect(self):
        """
        Ferme proprement la connexion Bloomberg.
        
        À appeler systématiquement après usage pour libérer les ressources.
        Avec le context manager, c'est automatique.
        """
        if self.session:
            self.session.stop()
            self.session = None
            self.service = None
    
    def is_connected(self) -> bool:
        """
        Vérifie si la connexion est active.
        
        Returns:
            True si session et service sont disponibles
        """
        return self.session is not None and self.service is not None
    
    # Context Manager Protocol (pour utilisation avec 'with')
    def __enter__(self):
        """Appelé automatiquement lors du 'with BloombergConnection() as conn:'"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Appelé automatiquement à la sortie du bloc 'with'"""
        self.disconnect()
        return False  # Ne pas supprimer les exceptions


def test_connection(host: str = "localhost", port: int = 8194) -> bool:
    """
    Fonction utilitaire pour tester rapidement la connexion Bloomberg.
    
    Args:
        host: Adresse du Terminal (défaut: localhost)
        port: Port (défaut: 8194)
    
    Returns:
        True si la connexion fonctionne
    
    Exemple:
        >>> if test_connection():
        ...     print("Bloomberg Terminal accessible")
        ... else:
        ...     print("Vérifiez que le Terminal est lancé")
    """
    try:
        with BloombergConnection(host, port) as conn:
            return conn.is_connected()
    except Exception as e:
        print(f"Erreur de connexion: {e}")
        return False


if __name__ == "__main__":
    # Test de connexion rapide
    print("Test de connexion au Bloomberg Terminal...")
    if test_connection():
        print("✓ Connexion réussie!")
    else:
        print("✗ Échec de connexion. Assurez-vous que Bloomberg Terminal est ouvert.")
