import requests
import urllib.parse
import re
from bs4 import BeautifulSoup
import json
import time
from utils import clean_text, clean_brand_name, clean_site_names_from_title,ensure_data_consistency, normalize_image_url , get_all_products_from_db , get_product_info_for_scraping , update_product_in_database, extract_price

def scraper_crenova_detaille(reference):
    """Scrape les données détaillées pour une référence donnée - VERSION AVEC ENCODAGE URL"""
    try:
        # 🔥 CORRECTION : Encoder la référence
        encoded_reference = urllib.parse.quote(reference)
        url = f"https://www.crenova.ma/recherche?controller=search&s={encoded_reference}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8'
        }
        
        print(f"🔍 [CRENOVA] Recherche du produit: {reference}")
        print(f"🔤 Référence encodée: {encoded_reference}")
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # VÉRIFIER SI C'EST UNE PAGE DE RECHERCHE AVEC RÉSULTATS
        no_results = soup.find('p', class_='alert alert-warning')
        if no_results and "Aucun résultat" in no_results.get_text():
            print(f"❌ [CRENOVA] Aucun résultat trouvé pour '{reference}'")
            return None
        
        # Trouver TOUS les liens de produits sur la page de recherche
        product_links = soup.find_all('a', class_='product_img_link')
        if not product_links:
            product_links = soup.find_all('a', class_=lambda x: x and 'product' in str(x))
        
        if not product_links:
            print(f"❌ [CRENOVA] Aucun produit trouvé sur la page de recherche pour {reference}")
            return None
        
        print(f"📦 [CRENOVA] {len(product_links)} produits trouvés sur la page de recherche")
        
        # Chercher le produit avec la référence EXACTE
        exact_match_url = None
        
        for i, product_link in enumerate(product_links, 1):
            product_url = product_link.get('href')
            
            # S'assurer que l'URL est complète
            if not product_url.startswith('http'):
                if product_url.startswith('//'):
                    product_url = 'https:' + product_url
                elif product_url.startswith('/'):
                    product_url = 'https://www.crenova.ma' + product_url
            
            # Accéder à chaque page produit pour vérifier la référence
            try:
                print(f"  🔎 [CRENOVA] Vérification du produit {i}/{len(product_links)}: {product_url}")
                product_response = requests.get(product_url, headers=headers, timeout=10)
                product_response.raise_for_status()
                product_soup = BeautifulSoup(product_response.content, 'html.parser')
                
                # VÉRIFICATION STRICTE DE LA RÉFÉRENCE
                found_reference = verify_reference_crenova(product_soup)
                
                if found_reference and found_reference.upper() == reference.upper():
                    print(f"  ✅ [CRENOVA] RÉFÉRENCE EXACTE TROUVÉE: {reference}")
                    exact_match_url = product_url
                    break
                else:
                    if found_reference:
                        print(f"  ❌ [CRENOVA] Référence différente: '{found_reference}' (attendu: '{reference}')")
                    else:
                        print(f"  ⚠️  [CRENOVA] Référence non trouvée sur la page")
                    
            except Exception as e:
                print(f"  ⚠️  [CRENOVA] Erreur vérification produit: {e}")
                continue
        
        if not exact_match_url:
            print(f"❌ [CRENOVA] Aucun produit avec la référence exacte '{reference}' trouvé")
            return None
        
        print(f"🌐 [CRENOVA] Accès à la page produit exacte: {exact_match_url}")
        
        # Maintenant scraper la page détaillée du produit
        return scraper_crenova_product_details(exact_match_url, reference)
        
    except Exception as e:
        print(f"❌ [CRENOVA] Erreur lors du scraping de {reference}: {e}")
        return None

def scraper_crenova_product_details(product_url, expected_reference):
    """Scrape les détails complets depuis la page produit Crenova - VERSION AVEC MARQUE"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
            'Referer': 'https://www.crenova.ma/'
        }
        
        print(f"🌐 [CRENOVA] Accès à la page produit détaillée...")
        response = requests.get(product_url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # VÉRIFICATION STRICTE DE LA RÉFÉRENCE
        reference_match = verify_reference_crenova(soup)
        if not reference_match or reference_match.upper() != expected_reference.upper():
            print(f"❌ [CRENOVA] RÉFÉRENCE MISMATCH: Attendu '{expected_reference}' mais trouvé '{reference_match}'")
            return None
        
        print(f"✅ [CRENOVA] Référence vérifiée: {expected_reference}")
        
        # Extraire les données (AVEC MARQUE ET PRIX)
        title = extract_title_crenova(soup)
        description = extract_description_crenova(soup)
        short_description = extract_short_description_crenova(soup)
        categories_data = extract_categories_crenova(soup)
        image_url = extract_main_image_crenova(soup)
        brand = extract_brand_crenova(soup)
        attributes = extract_attributes_crenova(soup)
        price, old_price = extract_price_crenova(soup)  # NOUVEAU
        
        # 🔥 CORRECTION: Appliquer la cohérence immédiatement
        if categories_data.get('categories') and not categories_data.get('subcategories'):
            categories_data['subcategories'] = categories_data['categories']
        
        if not description and short_description:
            description = short_description
        
        data = {
            'source': 'crenova',
            'reference': expected_reference,
            'title': title,
            'description': description,
            'short_description': short_description,
            'attributes': attributes,
            'categories': categories_data.get('categories'),
            'subcategories': categories_data.get('subcategories'),
            'product_url': product_url,
            'image': image_url,
            'brand': brand,
            'price': price,  # NOUVEAU
            'old_price': old_price  # NOUVEAU
        }
        
        return ensure_data_consistency(data)
        
    except Exception as e:
        print(f"❌ [CRENOVA] Erreur lors du scraping des détails: {e}")
        return None


def verify_reference_crenova(soup):
    """Vérifie la référence directement depuis la page produit Crenova - VERSION STRICTE"""
    try:
        # Méthode PRINCIPALE: Chercher la div avec itemprop="sku"
        sku_div = soup.find('div', class_='pro_extra_info_content', itemprop='sku')
        
        if sku_div:
            found_reference = sku_div.get_text(strip=True)
            return found_reference
        
        # Fallback: chercher d'autres éléments SKU
        sku_selectors = [
            'span[itemprop="sku"]',
            'meta[itemprop="sku"]',
            '.sku',
            '.product-sku',
            '.reference'
        ]
        
        for selector in sku_selectors:
            sku_element = soup.select_one(selector)
            if sku_element:
                if sku_element.name == 'meta':
                    found_reference = sku_element.get('content', '').strip()
                else:
                    found_reference = sku_element.get_text(strip=True)
                
                if found_reference:
                    return found_reference
        
        return None
        
    except Exception as e:
        print(f"❌ Erreur vérification référence Crenova: {e}")
        return None

def extract_title_crenova(soup):
    """Extrait le titre du produit Crenova - VERSION CORRIGÉE"""
    try:
        title_selectors = [
            'h1[itemprop="name"]',
            'h1.product-name',
            '.page-title',
            'h1.product-title',
            'h1'
        ]
        
        for selector in title_selectors:
            title_element = soup.select_one(selector)
            if title_element:
                title = title_element.get_text(strip=True)
                if title:
                    return clean_site_names_from_title(title)
        
        return None
    except Exception as e:
        print(f"❌ Erreur extraction titre Crenova: {e}")
        return None

def extract_description_crenova(soup):
    """Extrait la description depuis Crenova"""
    try:
        description_div = soup.find('div', class_='product-description')
        if description_div:
            print("✅ [CRENOVA] Div product-description trouvée")
            return str(description_div)
        
        return None
    except Exception as e:
        print(f"❌ Erreur extraction description Crenova: {e}")
        return None

def extract_short_description_crenova(soup):
    """Extrait la description courte depuis Crenova"""
    try:
        description_divs = soup.find_all('div', class_='st_read_more_box')
        
        for description_div in description_divs:
            ul_element = description_div.find('ul')
            if ul_element:
                print("✅ [CRENOVA] Description courte trouvée")
                li_elements = ul_element.find_all('li')
                if li_elements:
                    description_lines = []
                    for li in li_elements:
                        text = li.get_text(strip=True)
                        if text:
                            description_lines.append(text)
                    
                    if description_lines:
                        short_desc = ' | '.join(description_lines)
                        print(f"📏 [CRENOVA] Longueur description courte: {len(short_desc)} caractères")
                        return short_desc
        
        return None
    except Exception as e:
        print(f"❌ Erreur extraction description courte Crenova: {e}")
        return None


def extract_categories_crenova(soup):
    """Extrait les catégories depuis Crenova"""
    try:
        breadcrumb = soup.select('.breadcrumb_nav a')
        
        if breadcrumb and len(breadcrumb) >= 2:
            categories = []
            
            for item in breadcrumb:
                category = item.get_text(strip=True)
                if category and category.lower() not in ['accueil', 'home', '']:
                    categories.append(category)
            
            print(f"📊 [CRENOVA] Catégories trouvées: {categories}")
            
            if len(categories) >= 2:
                main_categories = categories[:1]
                sub_categories = categories[1:]
            else:
                main_categories = categories
                sub_categories = []
            
            return {
                'categories': ', '.join(main_categories) if main_categories else None,
                'subcategories': ', '.join(sub_categories) if sub_categories else None
            }
        
        return {'categories': None, 'subcategories': None}
        
    except Exception as e:
        print(f"❌ Erreur extraction catégories Crenova: {e}")
        return {'categories': None, 'subcategories': None}

def extract_main_image_crenova(soup):
    """Extrait l'URL de l'image principale depuis Crenova"""
    try:
        # Méthode 1: Image principale avec itemprop="image"
        main_image = soup.find('img', itemprop='image')
        if main_image:
            src = main_image.get('src') or main_image.get('data-src')
            if src:
                return normalize_image_url(src, 'https://www.crenova.ma')
        
        # Méthode 2: Image dans la galerie principale
        gallery_image = soup.select_one('.pb-image-frame img')
        if gallery_image:
            src = gallery_image.get('src') or gallery_image.get('data-src')
            if src:
                return normalize_image_url(src, 'https://www.crenova.ma')
        
        # Méthode 3: Image produit standard
        product_image = soup.select_one('.product-image img')
        if product_image:
            src = product_image.get('src') or product_image.get('data-src')
            if src:
                return normalize_image_url(src, 'https://www.crenova.ma')
        
        return None
        
    except Exception as e:
        print(f"❌ Erreur extraction image Crenova: {e}")
        return None

def extract_brand_crenova(soup):
    """Extrait la marque depuis Crenova - VERSION ULTRA-CORRIGÉE"""
    try:
        print("🔍 [CRENOVA] Recherche de marque...")
        
        # Liste noire ÉTENDUE des faux positifs
        BLACKLISTED_BRANDS = [
            'ÉTATNEUF', 'ETATNEUF', 'NEUF', 'OCCASION', 'OCCASIONNEUF',
            'RECONDITIONNÉ', 'RECONDITIONNE', 'REFURBISHED', 'GARANTIE',
            'LIVRAISON', 'GRATUITE', 'PROMOTION', 'SOLDE', 'STOCK',
            'ACCUEIL', 'HOME', 'BOUTIQUE', 'SHOP', 'CATÉGORIE', 'CATEGORY',
            'PRODUITS', 'PRODUCTS', 'RECHERCHE', 'SEARCH', 'CONTACT', 'À PROPOS'
        ]
        
        # MÉTHODE 1: Analyser le titre du produit (TRÈS FIABLE)
        title_element = soup.find('h1', itemprop='name')
        if title_element:
            title_text = title_element.get_text()
            print(f"📝 [CRENOVA] Titre du produit: {title_text}")
            
            # Liste ÉTENDUE des marques connues
            known_brands = [
                'SYNOLOGY', 'HUAWEI', 'LENOVO', 'HP', 'DELL', 'ASUS', 'CANON', 'EPSON', 
                'SAMSUNG', 'ACER', 'BROTHER', 'LEXMARK', 'APC', 'TP-LINK', 'LOGITECH', 
                'MICROSOFT', 'JABRA', 'EATON', 'INTEL', 'ADATA', 'SANDISK', 'LACIE', 
                'TARGUS', 'MOBILIS', 'ORAY', 'HISENSE', 'V7', 'OMEN', 'ASUSROG', 
                'SPIRIT OF GAMER', 'PORT DESIGNS', 'CRENOVA', 'WESTERN DIGITAL',
                'SEAGATE', 'TOSHIBA', 'KINGSTON', 'CRUCIAL', 'CORSAIR', 'G.SKILL',
                'HYPERX', 'PATRIOT', 'GEIL', 'TEAMGROUP', 'SILICON POWER', 'TRANSCEND'
            ]
            
            # Chercher chaque marque dans le titre (en majuscules)
            title_upper = title_text.upper()
            for known_brand in known_brands:
                if known_brand in title_upper:
                    print(f"✅ [CRENOVA] Marque trouvée dans le titre: {known_brand}")
                    return known_brand
        
        # MÉTHODE 2: Structure schema.org (source officielle)
        brand_link = soup.find('a', itemprop='brand')
        if brand_link:
            print("✅ [CRENOVA] Lien de marque schema.org trouvé")
            
            # Meta itemprop="name"
            meta_name = brand_link.find('meta', itemprop='name')
            if meta_name and meta_name.get('content'):
                brand_name = meta_name.get('content').strip()
                brand = clean_brand_name(brand_name)
                if brand and brand not in BLACKLISTED_BRANDS:
                    print(f"✅ [CRENOVA] Marque trouvée via meta name: {brand}")
                    return brand
            
            # Image itemprop="image"
            brand_img = brand_link.find('img', itemprop='image')
            if brand_img:
                alt_text = brand_img.get('alt', '')
                if alt_text:
                    brand = clean_brand_name(alt_text)
                    if brand and brand not in BLACKLISTED_BRANDS:
                        print(f"✅ [CRENOVA] Marque trouvée via alt d'image: {brand}")
                        return brand
            
            # Texte du lien
            link_text = brand_link.get_text(strip=True)
            if link_text:
                brand = clean_brand_name(link_text)
                if brand and brand not in BLACKLISTED_BRANDS:
                    print(f"✅ [CRENOVA] Marque trouvée via texte du lien: {brand}")
                    return brand
        
        # MÉTHODE 3: Breadcrumbs mais IGNORER "ACCUEIL" et autres éléments de navigation
        breadcrumb = soup.select('.breadcrumb_nav a')
        breadcrumb_brands = []
        
        for item in breadcrumb:
            text = item.get_text(strip=True)
            brand = clean_brand_name(text)
            if brand and brand not in BLACKLISTED_BRANDS and len(brand) > 2:
                breadcrumb_brands.append(brand)
                print(f"📝 [CRENOVA] Candidat breadcrumb: {brand}")
        
        # Prendre le DERNIER élément du breadcrumb (le plus spécifique)
        if breadcrumb_brands:
            final_brand = breadcrumb_brands[-1]
            print(f"✅ [CRENOVA] Marque trouvée via breadcrumb (dernier): {final_brand}")
            return final_brand
        
        # MÉTHODE 4: Sections de marque spécifiques avec filtrage RENFORCÉ
        brand_sections = soup.find_all(['div', 'section'], class_=lambda x: x and any(
            keyword in str(x).lower() for keyword in ['pro_extra_info', 'brand', 'marque', 'fabricant']
        ))
        
        for section in brand_sections:
            # Chercher des images de marque
            images = section.find_all('img', alt=True)
            for img in images:
                alt_text = img.get('alt', '')
                if alt_text and alt_text not in ['', ' ']:
                    brand = clean_brand_name(alt_text)
                    if brand and brand not in BLACKLISTED_BRANDS:
                        print(f"✅ [CRENOVA] Marque trouvée via section marque: {brand}")
                        return brand
            
            # Chercher du texte avec filtrage HYPER-STRICT
            text = section.get_text(strip=True)
            if len(text) > 10 and not any(bad_word in text.upper() for bad_word in BLACKLISTED_BRANDS):
                brand = clean_brand_name(text)
                if brand and brand not in BLACKLISTED_BRANDS:
                    print(f"✅ [CRENOVA] Marque trouvée via texte de section: {brand}")
                    return brand
        
        # MÉTHODE 5: URL de la page marque
        brand_links = soup.find_all('a', href=lambda x: x and '/marque/' in x)
        for link in brand_links:
            href = link.get('href', '')
            brand_match = re.search(r'/marque/([^/?]+)', href)
            if brand_match:
                brand_name = brand_match.group(1)
                brand = clean_brand_name(brand_name)
                if brand and brand not in BLACKLISTED_BRANDS:
                    print(f"✅ [CRENOVA] Marque trouvée via URL marque: {brand}")
                    return brand
        
        print("❌ [CRENOVA] Aucune marque valide trouvée")
        return None
        
    except Exception as e:
        print(f"❌ Erreur extraction marque Crenova: {e}")
        return None

def extract_attributes_crenova(soup):
    """Extrait les attributs (fiche technique) depuis Crenova"""
    try:
        attributes = {}
        print("🔍 [CRENOVA] Recherche des attributs...")
        
        # Méthode 1: Table standard Prestashop (table-data-sheet)
        table = soup.find('table', class_='table-data-sheet')
        if table:
            rows = table.find_all('tr')
            for row in rows:
                cols = row.find_all('td')
                if len(cols) == 2:
                    key = cols[0].get_text(strip=True).rstrip(':')
                    value = cols[1].get_text(strip=True)
                    if key and value:
                        attributes[key] = value
            
            if attributes:
                print(f"✅ [CRENOVA] {len(attributes)} attributs trouvés via table")
                return json.dumps(attributes, ensure_ascii=False)
        
        # Méthode 2: Chercher une section Fiche Technique
        sections = soup.find_all(['section', 'div'], class_=['page-product-box', 'product-features', 'tab-pane'])
        for section in sections:
            # Vérifier si c'est la bonne section via titre ou ID
            is_specs_section = False
            header = section.find(['h3', 'h4'])
            if header and 'fiche technique' in header.get_text(strip=True).lower():
                is_specs_section = True
            
            if section.get('id') == 'product-details':
                is_specs_section = True
                
            if is_specs_section:
                # Chercher table
                table = section.find('table')
                if table:
                    rows = table.find_all('tr')
                    for row in rows:
                        cols = row.find_all('td')
                        if len(cols) >= 2:
                            key = cols[0].get_text(strip=True).rstrip(':')
                            value = cols[1].get_text(strip=True)
                            if key and value:
                                attributes[key] = value
                
                # Chercher liste de définition (dl/dt/dd)
                dl_list = section.find_all('dl')
                for dl in dl_list:
                    dt_list = dl.find_all('dt')
                    dd_list = dl.find_all('dd')
                    if len(dt_list) == len(dd_list):
                        for dt, dd in zip(dt_list, dd_list):
                            key = dt.get_text(strip=True).rstrip(':')
                            value = dd.get_text(strip=True)
                            if key and value:
                                attributes[key] = value
                                
        # Méthode 3: Structure spécifique vue dans le read_url_content (liens comme valeurs)
        # Ex: [Carte graphique](url) -> clé par déduction ou structure parente
        feature_links = soup.find_all('a', href=True)
        for link in feature_links:
            # Heuristique: si le lien est dans une liste structurée
            parent_li = link.find_parent('li')
            if parent_li:
                text = parent_li.get_text(strip=True)
                if ':' in text:
                    key, value = text.split(':', 1)
                    if len(key) < 50: # Éviter les faux positifs
                        attributes[key.strip()] = value.strip()
            
        if attributes:
            print(f"✅ [CRENOVA] {len(attributes)} attributs trouvés")
            return json.dumps(attributes, ensure_ascii=False)

        print("⚠️ [CRENOVA] Aucun attribut trouvé")
        return None
    except Exception as e:
        print(f"❌ Erreur extraction attributs Crenova: {e}")
        return None

def extract_price_crenova(soup):
    """Extrait le prix depuis Crenova"""
    try:
        print("💰 [CRENOVA] Recherche du prix...")
        
        # Méthode 1: Prix avec itemprop="price" - utiliser l'attribut content
        price_span = soup.find('span', itemprop='price')
        if price_span and price_span.get('content'):
            price_text = price_span.get('content')
            price = extract_price(price_text)
            if price:
                print(f"✅ [CRENOVA] Prix trouvé (itemprop content): {price} MAD")
                
                # Chercher ancien prix
                old_price_element = soup.select_one('.regular-price, .old-price, .was-price')
                old_price = None
                if old_price_element:
                    old_price_text = old_price_element.get_text(strip=True)
                    old_price = extract_price(old_price_text)
                    if old_price and old_price > price:
                        print(f"✅ [CRENOVA] Ancien prix trouvé: {old_price} MAD")
                
                return price, old_price
        
        # Méthode 2: Div avec classe prix
        price_selectors = [
            '.current-price span[itemprop="price"]',
            '.product-price',
            '.price',
            'span.price',
            '.current-price'
        ]
        
        for selector in price_selectors:
            price_element = soup.select_one(selector)
            if price_element:
                price_text = price_element.get_text(strip=True)
                price = extract_price(price_text)
                if price:
                    print(f"✅ [CRENOVA] Prix trouvé ({selector}): {price} MAD")
                    
                    # Chercher ancien prix (si promo)
                    old_price = None
                    old_price_element = soup.select_one('.regular-price, .old-price, .was-price')
                    if old_price_element:
                        old_price_text = old_price_element.get_text(strip=True)
                        old_price = extract_price(old_price_text)
                        if old_price and old_price > price:
                            print(f"✅ [CRENOVA] Ancien prix trouvé: {old_price} MAD")
                    
                    return price, old_price
        
        print("⚠️ [CRENOVA] Aucun prix trouvé")
        return None, None
    except Exception as e:
        print(f"❌ Erreur extraction prix Crenova: {e}")
        return None, None

def scrap_product_for_site(reference, site_name):
    """
    Scrape un produit pour un site spécifique - VERSION SIMPLIFIÉE
    """
    try:
        print(f"\n🚀 LANCEMENT SCRAPING pour {reference} sur {site_name}")
        print("=" * 60)
        
        # Récupérer les informations du produit depuis la base
        product_info = get_product_info_for_scraping(reference, site_name)
        
        if not product_info:
            print(f"❌ Produit {reference} non trouvé ou pas en 'pending'")
            return None
        
        product_id = product_info[0]
        existing_url = product_info[9]
        
        print(f"📊 ID: {product_id}, URL existante: {existing_url or 'Aucune'}")
        
        # Appeler le scraper Crenova
        scraped_data = scraper_crenova_detaille(reference)
        
        if not scraped_data:
            print(f"❌ Scraping échoué pour {reference}")
            # Tenter quand même de mettre à jour le statut
            update_product_in_database(product_id, None, site_name, scraping_success=False)
            return None
        
        print(f"✅ Données scrapées avec succès pour {reference}")
        
        # Ajouter l'URL si nécessaire
        if not scraped_data.get('product_url') and existing_url:
            scraped_data['product_url'] = existing_url
            print(f"🔗 URL: {existing_url}")
        
        # Mettre à jour en base
        update_success = update_product_in_database(
            product_id, 
            scraped_data, 
            site_name, 
            scraping_success=True
        )
        
        if update_success:
            print(f"✅ Base de données mise à jour pour {reference}")
        else:
            print(f"⚠️  Problème technique lors de la mise à jour en base")
        
        # CORRECTION IMPORTANTE : Toujours retourner les données scrapées
        # même si la mise à jour en base a eu un problème
        return scraped_data
            
    except Exception as e:
        print(f"❌ Erreur lors du scraping de {reference} sur {site_name}: {e}")
        return None
    
 
def main():
    products = get_all_products_from_db("crenova")

    if not products:
        print("✅ Aucun produit avec données manquantes trouvé")
        return
    
    print(f"📊 {len(products)} produits à traiter")
    print("=" * 60)

    success_count = 0
    error_count = 0

    for i, product in enumerate(products, 1):
        product_id, reference, existing_title, existing_description, existing_short_description, \
        existing_categories, existing_subcategories, existing_brand, existing_image, existing_url, \
        existing_scraped_at = product
        
        print(f"\n🎯 PRODUIT {i}/{len(products)}")
        print(f"📦 Référence: {reference}")
        print(f"🆔 ID: {product_id}")
        
        # Scraper le produit
        scraped_data = scrap_product_for_site(reference, "crenova")
        
        # CORRECTION : Compter le succès basé sur les données récupérées, pas sur la mise à jour
        if scraped_data:
            success_count += 1
            print(f"✅ Données récupérées pour {reference}")
        else:
            error_count += 1
            print(f"❌ Échec pour {reference}")
        
        # Pause pour éviter de surcharger le serveur
        if i < len(products):
            print(f"\n⏳ Pause de 2 secondes...")
            time.sleep(2)
    
    # Résumé
    print(f"\n{'='*60}")
    print("📊 RÉCAPITULATIF DU SCRAPING")
    print(f"{'='*60}")
    print(f"✅ Données récupérées avec succès: {success_count}")
    print(f"❌ Échecs de scraping: {error_count}")
    print(f"📈 Total traité: {len(products)}")
    print(f"{'='*60}")

if __name__ == "__main__":
    # Test avec un produit spécifique
    # scrap_product_for_site("85A36EA", "crenova")
    # if scraped_data:
    #     print(f"Données récupérées: {scraped_data}")
    
    # Lancer le scraping pour tous les produits pending
    main()