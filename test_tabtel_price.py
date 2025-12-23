"""
Script de test pour vérifier la correction de l'extraction de prix sur Tabtel
"""
import requests
from bs4 import BeautifulSoup
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import extract_price

def test_tabtel_price_extraction():
    """Teste l'extraction de prix sur une vraie page Tabtel"""
    
    test_url = "https://tabtel.ma/fr/pc-portable/7276-ordinateur-portable-asus-vivobook-15-x1504va-nj1950w-90nb10j2-m02en0.html"
    
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
                print(f"  [OK] Prix correct: 6970 MAD attendu")
                return price
        else:
            print("  Meta tag non trouve")
        
        print("\n[TEST] Methode 2: Recherche #our_price_display")
        price_element = soup.select_one('#our_price_display')
        if price_element:
            price_text = price_element.get_text(strip=True)
            print(f"  Element trouve: '{price_text}'")
            price = extract_price(price_text)
            if price:
                print(f"  Prix extrait: {price} MAD")
                return price
        else:
            print("  Element non trouve")
        
        print("\n[TEST] Verification de l'ancien selecteur .product-price")
        wrong_element = soup.select_one('.product-price')
        if wrong_element:
            wrong_text = wrong_element.get_text(strip=True)
            wrong_price = extract_price(wrong_text)
            print(f"  [WARNING] Ancien selecteur trouve: '{wrong_text}' -> {wrong_price} MAD")
            print(f"  [WARNING] Ceci est le mauvais prix (probablement du menu)")
        
        print("\n[ERROR] Aucun prix trouve avec les nouveaux selecteurs")
        return None
        
    except Exception as e:
        print(f"\n[ERROR] Erreur: {e}")
        return None

if __name__ == "__main__":
    print("="*60)
    print("TEST D'EXTRACTION DE PRIX TABTEL (CORRIGE)")
    print("="*60)
    
    price = test_tabtel_price_extraction()
    
    print("\n" + "="*60)
    if price and price == 6970.0:
        print(f"[SUCCESS] Prix correct extrait: {price} MAD")
    elif price:
        print(f"[PARTIAL] Prix extrait: {price} MAD (attendu: 6970 MAD)")
    else:
        print("[FAIL] Echec de l'extraction")
    print("="*60)
