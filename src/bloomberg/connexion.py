from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, date
from typing import List, Optional, Dict, Any
import logging

# --- Import blpapi (on suppose que l'environnement Bloomberg est en place) ---
import blpapi  # si besoin d'un import plus robuste, utiliser le connector dédié

# ----------------------------------------------------------------------------
# Logging
# ----------------------------------------------------------------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def connect(self) -> bool:
    """Établit la connexion avec Bloomberg Terminal."""
    try:
        logger.info(f"🔌 Connexion à Bloomberg sur {self.host}:{self.port} …")
        opts = blpapi.SessionOptions()
        opts.setServerHost(self.host)
        opts.setServerPort(int(self.port))
        self.session = blpapi.Session(opts)

        if not self.session.start():
            logger.error("Échec du démarrage de la session Bloomberg")
            return False
        if not self.session.openService("//blp/refdata"):
            logger.error("Échec de l'ouverture du service //blp/refdata")
            self.session.stop()
            return False

        self.refdata_service = self.session.getService("//blp/refdata")
        logger.info("✅ Session Bloomberg démarrée et service refdata ouvert")
        return True
    except Exception as e:
        logger.exception("Erreur lors de la connexion: %s", e)
        return False

def disconnect(self) -> None:
    """Ferme proprement la session Bloomberg."""
    if self.session:
        try:
            self.session.stop()
        finally:
            self.session = None
            self.refdata_service = None
            logger.info("🔌 Connexion Bloomberg fermée")