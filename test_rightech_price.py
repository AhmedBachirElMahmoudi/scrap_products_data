"""
Script de test pour vérifier l'extraction de prix sur Rightech
Sans emojis pour éviter les erreurs d'encodage Windows
"""
import requests
from bs4 import BeautifulSoup
import sys
import os

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import extract_price

def test_rightech_price_extraction():
    """Teste l'extraction de prix sur une vraie page Rightech"""
    
    # URL de test
    test_url = "https://rightech.ma/pc-portable-hp-pavilion-15-eh3000nk-845m4ea.html"
    
    print(f"[TEST] Acces a: {test_url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(test_url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        print("\n[TEST] Methode 1: Recherche meta product:price:amount")
        price_meta = soup.find('meta', property='product:price:amount')
        if price_meta:
            price_content = price_meta.get('content')
            print(f"  Meta tag trouve: content='{price_content}'")
            price = extract_price(price_content)
            if price:
                print(f"  Prix extrait: {price} MAD")
                return price
        else:
            print("  Meta tag non trouve")
        
        print("\n[TEST] Methode 2: Recherche meta itemprop='price'")
        price_meta = soup.find('meta', itemprop='price')
        if price_meta:
            price_content = price_meta.get('content')
            print(f"  Meta tag trouve: content='{price_content}'")
            price = extract_price(price_content)
            if price:
                print(f"  Prix extrait: {price} MAD")
                return price
        else:
            print("  Meta tag non trouve")
        
        print("\n[TEST] Methode 3: Recherche dans elements prix")
        price_element = soup.select_one('.price ins .woocommerce-Price-amount, .price .woocommerce-Price-amount')
        if price_element:
            price_text = price_element.get_text(strip=True)
            print(f"  Element prix trouve: '{price_text}'")
            price = extract_price(price_text)
            if price:
                print(f"  Prix extrait: {price} MAD")
                return price
        else:
            print("  Element prix non trouve")
        
        print("\n[ERROR] Aucun prix trouve")
        return None
        
    except Exception as e:
        print(f"\n[ERROR] Erreur: {e}")
        return None

if __name__ == "__main__":
    print("="*60)
    print("TEST D'EXTRACTION DE PRIX RIGHTECH")
    print("="*60)
    
    price = test_rightech_price_extraction()
    
    print("\n" + "="*60)
    if price:
        print(f"[SUCCESS] Prix final: {price} MAD")
    else:
        print("[FAIL] Echec de l'extraction")
    print("="*60)
