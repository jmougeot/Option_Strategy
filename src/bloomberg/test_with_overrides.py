"""
Test avec Overrides Bloomberg
==============================
Ce script teste la récupération de Greeks en utilisant les overrides Bloomberg,
comme dans Excel.

Usage:
    python test_with_overrides.py

Auteur: BGC Trading Desk
Date: 2025-10-17
"""

import sys
from connection import BloombergConnection


def test_with_overrides():
    """
    Teste la récupération avec overrides comme Excel
    """
    print("="*70)
    print(" TEST AVEC OVERRIDES BLOOMBERG (comme Excel)")
    print("="*70)
    print()
    
    ticker = "ERH6C 97.5 Comdty"  # Mars 2026
    
    # Champs Greeks
    fields = [
        'PX_LAST',
        'OPT_DELTA', 'OPT_GAMMA', 'OPT_VEGA', 'OPT_THETA', 'OPT_RHO',
        'OPT_IMP_VOL',
        'OPT_UNDL_PX',
        'OPT_STRIKE_PX',
    ]
    
    print(f"Ticker: {ticker}")
    print(f"Champs Greeks demandés: OPT_DELTA, OPT_GAMMA, OPT_VEGA, OPT_THETA, OPT_RHO")
    print()
    
    try:
        with BloombergConnection() as conn:
            # Créer la requête
            request = conn.create_request("ReferenceDataRequest")
            request.append("securities", ticker)
            
            # Ajouter les champs
            for field in fields:
                request.append("fields", field)
            
            # AJOUTER LES OVERRIDES - C'EST LA CLÉ!
            print("Ajout des overrides (comme dans Excel)...")
            overrides = request.getElement("overrides")
            
            # Override 1: Source de pricing
            override1 = overrides.appendElement()
            override1.setElement("fieldId", "PRICING_SOURCE")
            override1.setElement("value", "BGNE")  # Bloomberg Generic
            print("  ✓ PRICING_SOURCE = BGNE")
            
            # Override 2: Date de référence
            override2 = overrides.appendElement()
            override2.setElement("fieldId", "REFERENCE_DATE") 
            override2.setElement("value", "TODAY")
            print("  ✓ REFERENCE_DATE = TODAY")
            
            print()
            print("Envoi de la requête à Bloomberg...")
            
            # Envoyer
            conn.send_request(request)
            
            # Recevoir
            print("Réception de la réponse...")
            print()
            print("-"*70)
            
            fields_found = {}
            
            while True:
                event = conn.next_event(500)
                
                for msg in event:
                    if msg.hasElement("securityData"):
                        sec_data = msg.getElement("securityData")
                        sec_data_element = sec_data.getValueAsElement(0)
                        
                        if sec_data_element.hasElement("securityError"):
                            error = sec_data_element.getElement("securityError")
                            print(f"⚠️  ERREUR: {error}")
                            return False
                        
                        if sec_data_element.hasElement("fieldData"):
                            field_data = sec_data_element.getElement("fieldData")
                            
                            print(f"Nombre d'éléments retournés: {field_data.numElements()}")
                            print()
                            
                            for i in range(field_data.numElements()):
                                element = field_data.getElement(i)
                                name = str(element.name())
                                
                                try:
                                    if not element.isNull():
                                        value = element.getValue()
                                        fields_found[name] = value
                                        print(f"  ✓ {name:25} = {value}")
                                except Exception as e:
                                    print(f"  ✗ {name:25} = Erreur: {e}")
                
                if event.eventType() == 5:  # RESPONSE
                    break
            
            print()
            print("-"*70)
            print()
            
            # Analyse
            greeks = ['OPT_DELTA', 'OPT_GAMMA', 'OPT_VEGA', 'OPT_THETA', 'OPT_RHO']
            greeks_found = [g for g in greeks if g in fields_found]
            
            if greeks_found:
                print(f"✓ SUCCÈS! {len(greeks_found)}/{len(greeks)} Greeks trouvés:")
                for greek in greeks_found:
                    print(f"  • {greek} = {fields_found[greek]}")
                print()
                print("🎉 Les overrides fonctionnent! Comme dans Excel!")
                return True
            else:
                print("✗ ÉCHEC: Aucun Greek retourné même avec les overrides")
                print()
                print("Autres causes possibles:")
                print("  1. Les noms de champs sont différents (pas OPT_DELTA)")
                print("  2. D'autres overrides sont nécessaires")
                print("  3. Le ticker n'existe pas")
                print()
                print("💡 Dans Excel Bloomberg, quels noms de champs utilisez-vous?")
                print("   Par exemple: =BDP(\"ERH6C 97.5 Comdty\", \"DELTA\") ?")
                print("   Ou: =BDP(\"ERH6C 97.5 Comdty\", \"OPT_DELTA\") ?")
                return False
                
    except Exception as e:
        print(f"✗ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print()
    print("Ce script teste la récupération des Greeks avec les overrides")
    print("Bloomberg (comme utilisé dans Excel)")
    print()
    input("Appuyez sur Entrée...")
    print()
    
    success = test_with_overrides()
    
    if success:
        print()
        print("="*70)
        print("✓ Les Greeks sont maintenant disponibles!")
        print("  Le module fetcher.py a été mis à jour avec les overrides.")
        print("="*70)
        sys.exit(0)
    else:
        print()
        print("="*70)
        print("✗ Problème persistant")
        print("  Veuillez indiquer les noms de champs utilisés dans Excel.")
        print("="*70)
        sys.exit(1)
