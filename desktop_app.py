"""
Option Strategy Desktop Application
====================================
Lance l'application Streamlit dans une fenêtre desktop native.
Compatible avec PyInstaller pour créer un .exe
"""

import subprocess
import sys
import time
import socket
import os
import webbrowser
import logging

# Configuration du logging
log_file = os.path.join(os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(__file__), "app.log")
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
APP_TITLE = "Option Strategy Analyzer"
STREAMLIT_PORT = 8501
WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 900


def get_base_path():
    """Retourne le chemin de base (différent si frozen ou non)."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))


def get_app_path():
    """Retourne le chemin vers l'application Streamlit."""
    base = get_base_path()
    
    if getattr(sys, 'frozen', False):
        possible_paths = [
            os.path.join(base, "_internal", "src", "myproject", "app.py"),
            os.path.join(base, "src", "myproject", "app.py"),
        ]
        if hasattr(sys, '_MEIPASS'):
            possible_paths.insert(0, os.path.join(sys._MEIPASS, "src", "myproject", "app.py"))
    else:
        possible_paths = [
            os.path.join(base, "src", "myproject", "app.py"),
        ]
    
    logger.debug(f"Recherche app.py dans: {possible_paths}")
    for path in possible_paths:
        if os.path.exists(path):
            logger.info(f"app.py trouvé: {path}")
            return path
    
    logger.error(f"app.py non trouvé! Chemins testés: {possible_paths}")
    return possible_paths[0]


def find_free_port(start_port: int = 8501) -> int:
    """Trouve un port libre à partir du port de départ."""
    port = start_port
    while port < start_port + 100:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('localhost', port))
                return port
            except OSError:
                port += 1
    return start_port


def is_port_in_use(port: int) -> bool:
    """Vérifie si un port est utilisé."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0


def run_streamlit_directly(port: int):
    """Lance Streamlit directement via l'import Python."""
    app_path = get_app_path()
    base_path = get_base_path()
    
    # Ajouter les paths nécessaires
    if getattr(sys, 'frozen', False):
        internal_path = os.path.join(base_path, "_internal")
        src_path = os.path.join(internal_path, "src")
        if hasattr(sys, '_MEIPASS'):
            sys.path.insert(0, sys._MEIPASS)
            sys.path.insert(0, os.path.join(sys._MEIPASS, "src"))
        if os.path.exists(src_path):
            sys.path.insert(0, src_path)
        if os.path.exists(internal_path):
            sys.path.insert(0, internal_path)
    else:
        src_path = os.path.join(base_path, "src")
        if os.path.exists(src_path):
            sys.path.insert(0, src_path)
    
    logger.debug(f"sys.path: {sys.path[:5]}")
    
    # Changer le répertoire de travail
    os.chdir(base_path)
    
    # Configuration Streamlit via variables d'environnement
    os.environ["STREAMLIT_GLOBAL_DEVELOPMENT_MODE"] = "false"
    os.environ["STREAMLIT_SERVER_PORT"] = str(port)
    os.environ["STREAMLIT_SERVER_HEADLESS"] = "true"
    os.environ["STREAMLIT_SERVER_ADDRESS"] = "localhost"
    os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    os.environ["STREAMLIT_SERVER_FILE_WATCHER_TYPE"] = "none"
    
    # Importer et lancer Streamlit
    try:
        from streamlit.web import cli as stcli
        import streamlit.runtime.scriptrunner.script_runner
        
        logger.info(f"Lancement Streamlit sur port {port}")
        sys.argv = ["streamlit", "run", app_path, f"--server.port={port}"]
        stcli.main()
    except Exception as e:
        logger.exception(f"Erreur Streamlit: {e}")
        raise


def main():
    """Point d'entrée principal de l'application desktop."""
    logger.info("="*50)
    logger.info("Démarrage Option Strategy Desktop App")
    logger.info(f"Frozen: {getattr(sys, 'frozen', False)}")
    logger.info(f"Executable: {sys.executable}")
    logger.info(f"Base path: {get_base_path()}")
    if hasattr(sys, '_MEIPASS'):
        logger.info(f"_MEIPASS: {sys._MEIPASS}")
    logger.info("="*50)
    
    port = find_free_port(STREAMLIT_PORT)
    logger.info(f"Port sélectionné: {port}")
    
    url = f"http://localhost:{port}"
    
    # Ouvrir le navigateur après un délai
    import threading
    def open_browser():
        time.sleep(3)  # Attendre que Streamlit démarre
        logger.info(f"Ouverture navigateur: {url}")
        webbrowser.open(url)
    
    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()
    
    # Lancer Streamlit directement (bloquant)
    try:
        run_streamlit_directly(port)
    except Exception as e:
        logger.exception(f"Erreur fatale: {e}")
        input("Appuyez sur Entrée pour fermer...")


if __name__ == "__main__":
    main()
