import requests
import urllib.parse
import re
from bs4 import BeautifulSoup
import json
from utils import clean_text, clean_brand_name, clean_site_names_from_title, normalize_image_url



def extract_brand_duga(soup):
    """Extrait la marque depuis Duga - VERSION CORRIGÉE ET PRIORISÉE"""
    try:
        print("🔍 [DUGA] Recherche de marque...")
        
        # MÉTHODE 1: Chercher dans les spans yith-wcbr-brands-logo (SPÉCIFIQUE À DUGA)
        brand_spans = soup.find_all('span', class_='yith-wcbr-brands-logo')
        for span in brand_spans:
            print("✅ [DUGA] Span yith-wcbr-brands-logo trouvé")
            
            # Chercher l'image dans le span
            img = span.find('img')
            if img:
                alt_text = img.get('alt', '')
                print(f"📝 [DUGA] Texte alt dans yith-wcbr: {alt_text}")
                
                # Extraire la marque du texte descriptif
                brand_match = re.search(r'marque\s+([^"]+)', alt_text.lower())
                if brand_match:
                    brand_name = brand_match.group(1).strip()
                    brand = clean_brand_name(brand_name)
                    if brand:
                        print(f"✅ [DUGA] Marque extraite du yith-wcbr alt: {brand}")
                        return brand
                
                # Fallback: chercher des marques connues dans le alt
                known_brands = ['LENOVO', 'HP', 'DELL', 'ASUS', 'CANON', 'EPSON', 'SAMSUNG', 'ACER', 'BROTHER']
                for known_brand in known_brands:
                    if known_brand in alt_text.upper():
                        print(f"✅ [DUGA] Marque connue trouvée dans yith-wcbr alt: {known_brand}")
                        return known_brand
            
            # Chercher dans le lien à l'intérieur du span
            link = span.find('a', href=lambda x: x and '/brand/' in x)
            if link:
                href = link.get('href', '')
                print(f"📝 [DUGA] Lien trouvé dans yith-wcbr: {href}")
                
                # Extraire la marque de l'URL
                brand_match = re.search(r'/brand/([^/]+)', href)
                if brand_match:
                    brand_name = brand_match.group(1)
                    brand = clean_brand_name(brand_name)
                    if brand:
                        print(f"✅ [DUGA] Marque trouvée via yith-wcbr URL: {brand}")
                        return brand

        # MÉTHODE 2: Analyser le titre du produit (très fiable)
        title_element = soup.find('h1', class_='product_title')
        if title_element:
            title_text = title_element.get_text()
            print(f"📝 [DUGA] Titre du produit: {title_text}")
            
            # Chercher des marques connues dans le titre (en majuscules pour éviter les faux positifs)
            known_brands = ['LENOVO', 'HP', 'DELL', 'ASUS', 'CANON', 'EPSON', 'SAMSUNG', 'ACER', 'BROTHER', 'HUAWEI']
            for known_brand in known_brands:
                if known_brand in title_text.upper():
                    print(f"✅ [DUGA] Marque trouvée via titre: {known_brand}")
                    return known_brand

        # MÉTHODE 3: Chercher dans les breadcrumbs (catégories)
        breadcrumbs = soup.find_all(['nav', 'div'], class_=lambda x: x and any(
            keyword in str(x).lower() for keyword in ['breadcrumb', 'breadcrumbs']
        ))
        for breadcrumb in breadcrumbs:
            links = breadcrumb.find_all('a')
            for link in links:
                text = link.get_text(strip=True)
                brand = clean_brand_name(text)
                if brand and brand != 'HUAWEI':  # Exclure Huawei spécifiquement
                    print(f"✅ [DUGA] Marque trouvée via breadcrumb: {brand}")
                    return brand

        # MÉTHODE 4: Chercher dans les images avec le pattern DUGA-*-PARTNER (en dernier)
        all_images = soup.find_all('img', src=True)
        for img in all_images:
            src = img.get('src', '').lower()
            if 'duga' in src and 'partner' in src:
                filename = src.split('/')[-1]
                print(f"📝 [DUGA] Image partner trouvée: {filename}")
                
                # Extraire le nom entre "DUGA-" et "-Partner"
                brand_match = re.search(r'duga-([^-]+)-', filename, re.IGNORECASE)
                if brand_match:
                    brand_name = brand_match.group(1)
                    brand = clean_brand_name(brand_name)
                    if brand and brand != 'HUAWEI':  # Exclure Huawei
                        print(f"✅ [DUGA] Marque trouvée via nom de fichier partner: {brand}")
                        return brand

        # MÉTHODE 5: Chercher dans TOUS les liens /brand/ mais avec priorité
        brand_links = soup.find_all('a', href=lambda x: x and '/brand/' in x)
        valid_brands_found = []
        
        for link in brand_links:
            href = link.get('href', '')
            brand_match = re.search(r'/brand/([^/]+)', href)
            if brand_match:
                brand_name = brand_match.group(1)
                brand = clean_brand_name(brand_name)
                if brand and brand != 'HUAWEI':  # Exclure Huawei
                    valid_brands_found.append(brand)
                    print(f"📝 [DUGA] Marque candidate trouvée via URL: {brand}")
        
        # Prendre la première marque valide (sauf Huawei)
        if valid_brands_found:
            final_brand = valid_brands_found[0]
            print(f"✅ [DUGA] Marque sélectionnée parmi les candidats: {final_brand}")
            return final_brand

        print("❌ [DUGA] Aucune marque valide trouvée")
        return None
        
    except Exception as e:
        print(f"❌ Erreur extraction marque Duga: {e}")
        return None

  