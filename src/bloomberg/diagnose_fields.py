"""
Diagnostic Bloomberg - Affichage de TOUS les champs retournés
==============================================================
Ce script récupère une option EURIBOR et affiche TOUS les champs
que Bloomberg retourne, pour identifier les bons noms de champs.

Usage:
    python diagnose_fields.py

Auteur: BGC Trading Desk
Date: 2025-10-17
"""

import sys
from connection import BloombergConnection


def diagnose_bloomberg_fields():
    """
    Récupère une option et affiche tous les champs retournés par Bloomberg
    """
    print("="*70)
    print(" DIAGNOSTIC BLOOMBERG - ANALYSE DES CHAMPS")
    print("="*70)
    print()
    
    # Configuration
    ticker = "ERH6C 97.5 Comdty"  # EURIBOR Mars 2025 Call Strike 97.5
    
    # Liste de tous les champs possibles à tester
    all_fields = [
        # Prix
        'PX_LAST', 'PX_BID', 'PX_ASK', 'PX_MID', 'PX_VOLUME', 'OPEN_INT',
        'PX_SETTLE', 'PX_OPEN', 'PX_HIGH', 'PX_LOW',
        
        # Greeks - version OPT_
        'OPT_DELTA', 'OPT_GAMMA', 'OPT_VEGA', 'OPT_THETA', 'OPT_RHO',
        
        # Greeks - version sans OPT_
        'DELTA', 'GAMMA', 'VEGA', 'THETA', 'RHO',
        
        # Volatilité
        'OPT_IMP_VOL', 'OPT_IVOL_BID', 'OPT_IVOL_ASK', 'IVOL_MID',
        'IMPLIED_VOLATILITY_LAST', 'IVOL_LAST',
        
        # Delta bid/ask
        'OPT_DELTA_BID', 'OPT_DELTA_ASK',
        'DELTA_BID', 'DELTA_ASK',
        
        # Infos contractuelles
        'OPT_STRIKE_PX', 'OPT_EXPIR_DT', 'OPT_PUT_CALL',
        'OPT_UNDL_PX', 'OPT_REF_PRICE',
        'STRIKE', 'MATURITY', 'CONTRACT_VALUE',
        
        # Autres champs possibles
        'OPT_DAYS_TO_EXP', 'OPT_CONT_SIZE', 'OPT_TICK_VAL',
        'VOLUME', 'OPEN_INTEREST',
    ]
    
    print(f"Ticker testé: {ticker}")
    print(f"Nombre de champs à tester: {len(all_fields)}")
    print()
    print("-"*70)
    print()
    
    try:
        print("Connexion à Bloomberg...")
        with BloombergConnection() as conn:
            print("✓ Connecté\n")
            
            # Créer la requête
            request = conn.create_request("ReferenceDataRequest")
            request.append("securities", ticker)
            
            # Ajouter tous les champs
            for field in all_fields:
                request.append("fields", field)
            
            # Envoyer la requête
            print("Envoi de la requête à Bloomberg...")
            conn.send_request(request)
            
            # Récupérer la réponse
            print("Réception de la réponse...\n")
            print("="*70)
            print(" CHAMPS RETOURNÉS PAR BLOOMBERG")
            print("="*70)
            print()
            
            fields_found = {}
            
            while True:
                event = conn.next_event(500)
                
                for msg in event:
                    if msg.hasElement("securityData"):
                        sec_data = msg.getElement("securityData")
                        sec_data_element = sec_data.getValueAsElement(0)
                        
                        # Vérifier les erreurs
                        if sec_data_element.hasElement("securityError"):
                            error = sec_data_element.getElement("securityError")
                            error_msg = error.getElementAsString("message") if error.hasElement("message") else "Unknown error"
                            print(f"⚠️  ERREUR Bloomberg: {error_msg}")
                            return False
                        
                        # Récupérer les données de champs
                        if sec_data_element.hasElement("fieldData"):
                            field_data = sec_data_element.getElement("fieldData")
                            
                            for field in all_fields:
                                if field_data.hasElement(field):
                                    try:
                                        value = field_data.getElement(field)
                                        if not value.isNull():
                                            # Extraire la valeur selon le type
                                            try:
                                                val = value.getValueAsFloat()
                                            except:
                                                try:
                                                    val = value.getValueAsInteger()
                                                except:
                                                    try:
                                                        val = value.getValueAsString()
                                                    except:
                                                        val = str(value.getValue())
                                            
                                            fields_found[field] = val
                                    except:
                                        pass
                
                # Sortir si réponse complète
                if event.eventType() == 5:  # RESPONSE
                    break
            
            # Afficher les résultats
            if fields_found:
                print(f"✓ {len(fields_found)} champs trouvés avec des valeurs:\n")
                
                # Grouper par catégorie
                categories = {
                    'Prix': ['PX_', 'VOLUME', 'OPEN'],
                    'Greeks Delta': ['DELTA'],
                    'Greeks Autres': ['GAMMA', 'VEGA', 'THETA', 'RHO'],
                    'Volatilité': ['VOL', 'IVOL'],
                    'Contractuel': ['OPT_', 'STRIKE', 'EXPIR', 'UNDL', 'MATURITY'],
                }
                
                for category, patterns in categories.items():
                    matching = {k: v for k, v in fields_found.items() 
                               if any(p in k for p in patterns)}
                    
                    if matching:
                        print(f"{category}:")
                        for field, value in sorted(matching.items()):
                            print(f"  ✓ {field:25} = {value}")
                        print()
                
                # Afficher tous les autres
                shown = set()
                for patterns in categories.values():
                    for k in fields_found.keys():
                        if any(p in k for p in patterns):
                            shown.add(k)
                
                others = {k: v for k, v in fields_found.items() if k not in shown}
                if others:
                    print("Autres champs:")
                    for field, value in sorted(others.items()):
                        print(f"  ✓ {field:25} = {value}")
                    print()
                
                print("="*70)
                print("\n🔍 ANALYSE:")
                
                # Vérifier les champs Delta
                delta_fields = [k for k in fields_found.keys() if 'DELTA' in k]
                if delta_fields:
                    print(f"\n✓ Champs DELTA trouvés: {', '.join(delta_fields)}")
                    print(f"  → Utiliser: {delta_fields[0]}")
                else:
                    print("\n✗ Aucun champ DELTA trouvé!")
                
                return True
            else:
                print("✗ Aucun champ retourné avec des valeurs")
                print("\nPossibles causes:")
                print("  - Le ticker n'existe pas ou a expiré")
                print("  - Pas de droits d'accès aux données")
                print("  - Les noms de champs sont incorrects")
                return False
                
    except Exception as e:
        print(f"✗ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print()
    print("Ce script teste TOUS les champs possibles pour identifier")
    print("les bons noms de champs Bloomberg pour le delta et les Greeks.")
    print()
    input("Appuyez sur Entrée pour lancer le diagnostic...")
    print()
    
    success = diagnose_bloomberg_fields()
    
    if success:
        print("\n✓ Diagnostic terminé - Consultez les résultats ci-dessus")
        return 0
    else:
        print("\n✗ Diagnostic échoué")
        return 1


if __name__ == "__main__":
    sys.exit(main())
