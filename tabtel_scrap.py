import requests
import urllib.parse
import re
from bs4 import BeautifulSoup
import json
from utils import clean_text, clean_brand_name, clean_site_names_from_title, normalize_image_url


def extract_brand_tabtel(soup):
    """Extrait la marque depuis Tabtel - VERSION CORRIGÉE POUR LEUR FORMAT"""
    try:
        print("🔍 [TABTEL] Recherche de marque...")
        
        # MÉTHODE 1: Chercher les images de partenaire/marque avec extraction intelligente
        brand_images = soup.find_all('img', src=lambda x: x and any(
            keyword in x.lower() for keyword in ['marque', 'brand', 'partenaire', 'partner', 'logo']
        ))
        
        for img in brand_images:
            alt_text = img.get('alt', '')
            src_text = img.get('src', '')
            print(f"📝 [TABTEL] Image trouvée - alt: '{alt_text}', src: '{src_text}'")
            
            if alt_text:
                # Pattern 1: "Tabtel.ma partenaire Lenovo Technologies agréé" -> extraire "Lenovo"
                brand_match = re.search(r'partenaire\s+([^"]+?)\s+technologies', alt_text.lower())
                if brand_match:
                    brand_name = brand_match.group(1).strip()
                    brand = clean_brand_name(brand_name)
                    if brand:
                        print(f"✅ [TABTEL] Marque extraite via pattern partenaire: {brand}")
                        return brand
                
                # Pattern 2: "Marque Lenovo" -> extraire "Lenovo"
                brand_match = re.search(r'marque\s+([^"]+)', alt_text.lower())
                if brand_match:
                    brand_name = brand_match.group(1).strip()
                    brand = clean_brand_name(brand_name)
                    if brand:
                        print(f"✅ [TABTEL] Marque extraite via pattern marque: {brand}")
                        return brand
                
                # Pattern 3: Chercher des marques connues dans le alt
                known_brands = ['LENOVO', 'HP', 'DELL', 'ASUS', 'CANON', 'EPSON', 'SAMSUNG', 'ACER', 'BROTHER']
                for known_brand in known_brands:
                    if known_brand in alt_text.upper():
                        print(f"✅ [TABTEL] Marque connue trouvée dans alt: {known_brand}")
                        return known_brand
            
            # Extraire du nom de fichier si l'alt ne donne pas de résultat
            if src_text:
                filename = src_text.split('/')[-1].lower()
                print(f"📝 [TABTEL] Nom de fichier: {filename}")
                
                # Pattern: "lenovo-pc-partner-tabtel-maroc.png" -> extraire "lenovo"
                if 'partner' in filename or 'marque' in filename:
                    # Chercher le premier mot significatif avant "pc" ou "partner"
                    brand_match = re.search(r'^([a-z]+)-', filename)
                    if brand_match:
                        brand_name = brand_match.group(1)
                        brand = clean_brand_name(brand_name)
                        if brand:
                            print(f"✅ [TABTEL] Marque extraite via nom de fichier: {brand}")
                            return brand
        
        # MÉTHODE 2: Analyser le titre du produit
        title_element = soup.find('h1', itemprop='name')
        if title_element:
            title_text = title_element.get_text()
            print(f"📝 [TABTEL] Titre du produit: {title_text}")
            
            # Chercher des marques connues dans le titre
            known_brands = ['LENOVO', 'HP', 'DELL', 'ASUS', 'CANON', 'EPSON', 'SAMSUNG', 'ACER', 'BROTHER']
            for known_brand in known_brands:
                if known_brand in title_text.upper():
                    print(f"✅ [TABTEL] Marque trouvée via titre: {known_brand}")
                    return known_brand
        
        # MÉTHODE 3: Chercher dans les breadcrumbs
        breadcrumb_items = soup.find_all('span', itemprop='itemListElement')
        for item in breadcrumb_items:
            link = item.find('a')
            if link:
                text = link.get_text(strip=True)
                brand = clean_brand_name(text)
                if brand:
                    print(f"✅ [TABTEL] Marque trouvée via breadcrumb: {brand}")
                    return brand
        
        # MÉTHODE 4: Chercher dans les meta données
        meta_brand = soup.find('meta', attrs={'name': 'brand'})
        if meta_brand and meta_brand.get('content'):
            brand_name = meta_brand.get('content').strip()
            brand = clean_brand_name(brand_name)
            if brand:
                print(f"✅ [TABTEL] Marque trouvée via meta: {brand}")
                return brand
        
        print("❌ [TABTEL] Aucune marque valide trouvée")
        return None
        
    except Exception as e:
        print(f"❌ Erreur extraction marque Tabtel: {e}")
        return None

