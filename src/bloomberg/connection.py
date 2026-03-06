"""
Bloomberg Connection - Version Simplifiée
==========================================
Connexion au Bloomberg Terminal API (blpapi).
Supporte les modes synchrone et asynchrone.
"""

import blpapi
from blpapi.session import Session
from blpapi.sessionoptions import SessionOptions
from typing import Optional

from bloomberg.config import BloombergConfig, REFDATA_SERVICE, config  # noqa: F401

# Session et service globaux (mode synchrone)
_session: Optional[Session] = None
_service: Optional[blpapi.service.Service] = None


# =============================================================================
# MODE SYNCHRONE (pour ReferenceDataRequest)
# =============================================================================

def get_session() -> Session:
    """
    Retourne la session Bloomberg synchrone (la crée si nécessaire).
    """
    global _session
    
    if _session is None:
        opts = SessionOptions()
        opts.setServerHost(config.host)
        opts.setServerPort(config.port)
        opts.setAutoRestartOnDisconnection(True)
        opts.setNumStartAttempts(3)
        
        _session = Session(opts)
        
        if not _session.start():
            _session = None
            raise ConnectionError(
                f"Impossible de démarrer la session Bloomberg sur {config.host}:{config.port}"
            )
    
    return _session


def get_service(service_name: str = REFDATA_SERVICE) -> blpapi.service.Service:
    """
    Retourne le service Bloomberg (l'ouvre si nécessaire).
    """
    global _service
    
    session = get_session()
    
    if _service is None:
        if not session.openService(service_name):
            raise ConnectionError(f"Impossible d'ouvrir le service {service_name}")
        _service = session.getService(service_name)
    
    return _service


def close_session():
    """Ferme la session Bloomberg."""
    global _session, _service
    
    if _session:
        _session.stop()
        _session = None
        _service = None


def is_connected() -> bool:
    """Vérifie si la connexion est active."""
    return _session is not None
