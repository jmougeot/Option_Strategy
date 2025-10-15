import blpapi

def test_bloomberg_connection():
    """Vérifie si une session Bloomberg API locale peut être ouverte."""
    options = blpapi.SessionOptions()
    options.setServerHost("localhost")
    options.setServerPort(8194)  # port standard Bloomberg

    session = blpapi.Session(options)
    
    if not session.start():
        print("❌ Impossible de démarrer la session Bloomberg.")
        print("→ Vérifie que ton terminal Bloomberg est ouvert.")
        return False
    
    if not session.openService("//blp/refdata"):
        print("❌ Impossible d’ouvrir le service refdata.")
        print("→ Ton terminal est ouvert mais l’API n’est pas active.")
        session.stop()
        return False
    
    print("✅ Connexion Bloomberg API réussie !")
    print("→ Service refdata disponible.")
    session.stop()
    return True


if __name__ == "__main__":
    test_bloomberg_connection()