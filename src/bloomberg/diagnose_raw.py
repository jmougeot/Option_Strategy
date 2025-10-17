"""
Diagnostic Bloomberg - Version Ultra Simple
============================================
Affiche EXACTEMENT ce que Bloomberg retourne, sans filtre.

Usage:
    python diagnose_raw.py

Auteur: BGC Trading Desk
Date: 2025-10-17
"""

import sys
from connection import BloombergConnection


def diagnose_raw():
    """
    Récupère une option et affiche TOUT ce que Bloomberg retourne
    """
    print("="*70)
    print(" DIAGNOSTIC RAW - CE QUE BLOOMBERG RETOURNE VRAIMENT")
    print("="*70)
    print()
    
    ticker = "ERH5C 97.5 Comdty"
    
    # Tous les champs qu'on a listés
    fields = [
        'PX_LAST', 'PX_BID', 'PX_ASK', 'PX_MID', 'PX_VOLUME', 'OPEN_INT',
        'OPT_DELTA', 'OPT_GAMMA', 'OPT_VEGA', 'OPT_THETA', 'OPT_RHO',
        'DELTA', 'GAMMA', 'VEGA', 'THETA', 'RHO',
        'OPT_IMP_VOL', 'OPT_IVOL_BID', 'OPT_IVOL_ASK',
        'OPT_DELTA_BID', 'OPT_DELTA_ASK',
        'OPT_STRIKE_PX', 'OPT_EXPIR_DT', 'OPT_PUT_CALL',
        'OPT_UNDL_PX', 'OPT_REF_PRICE',
    ]
    
    print(f"Ticker: {ticker}")
    print(f"Champs demandés: {len(fields)}")
    print()
    
    try:
        with BloombergConnection() as conn:
            request = conn.create_request("ReferenceDataRequest")
            request.append("securities", ticker)
            
            for field in fields:
                request.append("fields", field)
            
            conn.send_request(request)
            
            print("Réponse de Bloomberg:")
            print("-"*70)
            
            count = 0
            
            while True:
                event = conn.next_event(500)
                
                for msg in event:
                    if msg.hasElement("securityData"):
                        sec_data = msg.getElement("securityData")
                        sec_data_element = sec_data.getValueAsElement(0)
                        
                        if sec_data_element.hasElement("securityError"):
                            error = sec_data_element.getElement("securityError")
                            print(f"\n⚠️  ERREUR: {error}")
                            return
                        
                        if sec_data_element.hasElement("fieldData"):
                            field_data = sec_data_element.getElement("fieldData")
                            
                            print(f"\nNombre d'éléments dans fieldData: {field_data.numElements()}")
                            print()
                            
                            for i in range(field_data.numElements()):
                                element = field_data.getElement(i)
                                name = str(element.name())
                                
                                try:
                                    if not element.isNull():
                                        value = element.getValue()
                                        print(f"  [{count+1}] {name:25} = {value}")
                                        count += 1
                                    else:
                                        print(f"  [ ] {name:25} = NULL")
                                except Exception as e:
                                    print(f"  [?] {name:25} = Erreur: {e}")
                
                if event.eventType() == 5:  # RESPONSE
                    break
            
            print()
            print("-"*70)
            print(f"\n✓ Total: {count} champs retournés avec des valeurs")
            print()
            
            if count <= 5:
                print("⚠️  ATTENTION: Très peu de champs retournés!")
                print()
                print("Causes possibles:")
                print("  1. Le ticker n'est pas correct")
                print("  2. L'option a expiré")
                print("  3. Pas de droits d'accès à certains champs")
                print("  4. Les noms de champs sont incorrects pour ce type d'instrument")
                print()
                print("💡 SOLUTION:")
                print("  → Testez manuellement dans Bloomberg Terminal:")
                print(f"     Tapez: {ticker} <GO>")
                print("     Puis: FLDS <GO>")
                print("     Pour voir la liste des champs disponibles")
            
    except Exception as e:
        print(f"\n✗ Erreur: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print()
    print("Ce script affiche exactement ce que Bloomberg retourne")
    print("pour le ticker ERH5C 97.5 Comdty")
    print()
    input("Appuyez sur Entrée...")
    print()
    diagnose_raw()
