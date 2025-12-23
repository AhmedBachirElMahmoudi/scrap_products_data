import requests
from bs4 import BeautifulSoup
import re
import time
import urllib.parse
from utils import clean_text, clean_brand_name, clean_site_names_from_title,ensure_data_consistency, normalize_image_url , get_all_products_from_db , get_product_info_for_scraping , update_product_in_database, extract_price
import json
import traceback

def scraper_joutech_detaille(reference):
    """Scrape les données détaillées pour une référence donnée sur joutech.ma"""
    try:
        # URL de recherche sur joutech.ma (WordPress/WooCommerce)
        encoded_reference = urllib.parse.quote(reference)
        url = f"https://joutech.ma/?s={encoded_reference}&post_type=product"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        }
        
        print(f"🔍 Recherche du produit sur joutech.ma: {reference}")
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Vérifier si c'est une page de recherche avec résultats
        no_results = soup.find('p', class_='woocommerce-info')
        if no_results and "Aucun résultat" in no_results.get_text():
            print(f"❌ [JOUTECH] Aucun résultat trouvé pour '{reference}'")
            return None
        
        # Trouver TOUS les liens de produits sur la page de recherche
        product_links = soup.find_all('a', class_='woocommerce-loop-product__link')
        if not product_links:
            product_links = soup.find_all('a', class_=lambda x: x and 'product' in str(x))
        
        if not product_links:
            print(f"❌ [JOUTECH] Aucun produit trouvé sur la page de recherche pour {reference}")
            return None
        
        print(f"📦 [JOUTECH] {len(product_links)} produits trouvés sur la page de recherche")
        
        # Chercher le produit avec la référence EXACTE
        exact_match_url = None
        
        for i, product_link in enumerate(product_links, 1):
            product_url = product_link.get('href')
            
            # S'assurer que l'URL est complète
            if not product_url.startswith('http'):
                if product_url.startswith('//'):
                    product_url = 'https:' + product_url
                elif product_url.startswith('/'):
                    product_url = 'https://joutech.ma' + product_url
            
            # Accéder à chaque page produit pour vérifier la référence
            try:
                print(f"  🔎 [JOUTECH] Vérification du produit {i}/{len(product_links)}: {product_url}")
                product_response = requests.get(product_url, headers=headers, timeout=10)
                product_response.raise_for_status()
                product_soup = BeautifulSoup(product_response.content, 'html.parser')
                
                # VÉRIFICATION STRICTE DE LA RÉFÉRENCE
                found_reference = verify_reference_joutech(product_soup)
                
                if found_reference and found_reference.upper() == reference.upper():
                    print(f"  ✅ [JOUTECH] RÉFÉRENCE EXACTE TROUVÉE: {reference}")
                    exact_match_url = product_url
                    break
                else:
                    if found_reference:
                        print(f"  ❌ [JOUTECH] Référence différente: '{found_reference}' (attendu: '{reference}')")
                    else:
                        print(f"  ⚠️  [JOUTECH] Référence non trouvée sur la page")
                    
            except Exception as e:
                print(f"  ⚠️  [JOUTECH] Erreur vérification produit: {e}")
                continue
        
        if not exact_match_url:
            print(f"❌ [JOUTECH] Aucun produit avec la référence exacte '{reference}' trouvé")
            return None
        
        print(f"🌐 [JOUTECH] Accès à la page produit exacte: {exact_match_url}")
        
        # Maintenant scraper la page détaillée du produit
        return scraper_joutech_product_details(exact_match_url, reference)
        
    except Exception as e:
        print(f"❌ [JOUTECH] Erreur lors du scraping de {reference}: {e}")
        return None

def scraper_joutech_product_details(product_url, expected_reference):
    """Scrape les détails complets depuis la page produit joutech.ma - VERSION AVEC MARQUE"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
            'Referer': 'https://joutech.ma/'
        }
        
        print(f"🌐 [JOUTECH] Accès à la page produit détaillée...")
        response = requests.get(product_url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # VÉRIFICATION STRICTE DE LA RÉFÉRENCE
        reference_match = verify_reference_joutech(soup)
        if not reference_match or reference_match.upper() != expected_reference.upper():
            print(f"❌ [JOUTECH] RÉFÉRENCE MISMATCH: Attendu '{expected_reference}' mais trouvé '{reference_match}'")
            return None
        
        print(f"✅ [JOUTECH] Référence vérifiée: {expected_reference}")
        
        # Extraire les données (AVEC MARQUE)
        title = extract_title_joutech(soup)
        description = extract_description_joutech(soup)
        short_description = extract_short_description_joutech(soup)
        categories_data = extract_categories_joutech(soup)
        image_url = extract_main_image_joutech(soup)
        image_url = extract_main_image_joutech(soup)
        brand = extract_brand_joutech(soup)
        price, old_price = extract_price_joutech(soup)  # NOUVEAU
        attributes = extract_attributes_joutech(soup) # NOUVEAU
        
        # 🔥 CORRECTION: Appliquer la cohérence immédiatement
        if categories_data.get('categories') and not categories_data.get('subcategories'):
            categories_data['subcategories'] = categories_data['categories']
        
        if not description and short_description:
            description = short_description
        
        data = {
            'source': 'joutech',
            'reference': expected_reference,
            'title': title,
            'description': description,
            'short_description': short_description,
            'short_description': short_description,
            'attributes': json.dumps(attributes, ensure_ascii=False) if attributes else None,
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
        print(f"❌ [JOUTECH] Erreur lors du scraping des détails: {e}")
        return None

def verify_reference_joutech(soup):
    """Vérifie la référence directement depuis la page produit joutech.ma - VERSION STRICTE"""
    try:
        # Méthode PRINCIPALE: Chercher le SKU dans WooCommerce
        sku_element = soup.find('span', class_='sku')
        
        if sku_element:
            found_reference = sku_element.get_text(strip=True)
            return found_reference
        
        # Fallback: chercher d'autres éléments SKU
        sku_selectors = [
            'span[itemprop="sku"]',
            'meta[itemprop="sku"]',
            '.product_meta .sku',
            '.product-reference',
            '.reference-value'
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
        
        # Méthode 3: Chercher dans les tableaux d'attributs
        attribute_tables = soup.find_all('table', class_='woocommerce-product-attributes-table')
        for table in attribute_tables:
            rows = table.find_all('tr')
            for row in rows:
                th = row.find('th')
                td = row.find('td')
                if th and td:
                    if 'référence' in th.get_text(strip=True).lower() or 'sku' in th.get_text(strip=True).lower():
                        found_reference = td.get_text(strip=True)
                        if found_reference:
                            return found_reference
        
        return None
        
    except Exception as e:
        print(f"❌ Erreur vérification référence joutech: {e}")
        return None

def extract_title_joutech(soup):
    """Extrait le titre du produit joutech.ma"""
    try:
        title_selectors = [
            'h1.product_title',
            'h1.entry-title',
            'h1',
            '.product-title',
            '.product_title.entry-title'
        ]
        
        for selector in title_selectors:
            title_element = soup.select_one(selector)
            if title_element:
                title = title_element.get_text(strip=True)
                if title:
                    # Nettoyer le titre
                    title = re.sub(r'\s+', ' ', title).strip()
                    return clean_text(title)
        
        return None
    except Exception as e:
        print(f"❌ Erreur extraction titre joutech: {e}")
        return None

def extract_description_joutech(soup):
    """Extrait la description depuis joutech.ma"""
    try:
        # Méthode 1: Onglet description WooCommerce
        description_tab = soup.select_one('#tab-description')
        if description_tab:
            print("✅ [JOUTECH] Onglet description trouvé")
            return str(description_tab)
        
        # Méthode 2: Contenu principal
        description_div = soup.find('div', class_='woocommerce-Tabs-panel--description')
        if description_div:
            print("✅ [JOUTECH] Div description trouvée")
            return str(description_div)
        
        # Méthode 3: Contenu du produit
        product_description = soup.select_one('.product_description, .description')
        if product_description:
            print("✅ [JOUTECH] Description produit trouvée")
            return str(product_description)
        
        return None
    except Exception as e:
        print(f"❌ Erreur extraction description joutech: {e}")
        return None

def extract_short_description_joutech(soup):
    """Extrait la description courte depuis joutech.ma"""
    try:
        short_desc_selectors = [
            '.woocommerce-product-details__short-description',
            '.product_short_description',
            '.short-description',
            '.summary .woocommerce-product-details__short-description'
        ]
        
        for selector in short_desc_selectors:
            short_desc_element = soup.select_one(selector)
            if short_desc_element:
                print("✅ [JOUTECH] Description courte trouvée")
                
                # Extraire le texte
                text_content = short_desc_element.get_text(strip=True)
                if text_content:
                    print(f"📏 [JOUTECH] Longueur description courte: {len(text_content)} caractères")
                    return text_content
        
        # Si pas de description courte, créer un extrait de la description longue
        description = extract_description_joutech(soup)
        if description:
            soup_desc = BeautifulSoup(description, 'html.parser')
            text_content = soup_desc.get_text(strip=True)
            if len(text_content) > 200:
                short_desc = text_content[:200] + "..."
                print(f"🔄 [JOUTECH] Description courte créée depuis description longue")
                return short_desc
        
        return None
    except Exception as e:
        print(f"❌ Erreur extraction description courte joutech: {e}")
        return None

def extract_categories_joutech(soup):
    """Extrait les catégories depuis joutech.ma"""
    try:
        # Méthode 1: Breadcrumb WooCommerce
        breadcrumb = soup.select('.woocommerce-breadcrumb a')
        
        if not breadcrumb:
            # Méthode 2: Breadcrumb standard
            breadcrumb = soup.select('.breadcrumb a, nav.breadcrumbs a')
        
        if breadcrumb:
            categories = []
            
            for item in breadcrumb:
                category = item.get_text(strip=True)
                if category and category.lower() not in ['accueil', 'home', 'shop', 'boutique', '']:
                    categories.append(category)
            
            print(f"📊 [JOUTECH] Catégories trouvées: {categories}")
            
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
        
        # Méthode 3: Catégories dans la meta
        posted_in = soup.select_one('.product_meta .posted_in')
        if posted_in:
            categories_links = posted_in.find_all('a')
            if categories_links:
                categories = [link.get_text(strip=True) for link in categories_links]
                print(f"📊 [JOUTECH] Catégories meta trouvées: {categories}")
                
                if len(categories) >= 2:
                    return {
                        'categories': categories[0],
                        'subcategories': categories[1]
                    }
                elif len(categories) == 1:
                    return {
                        'categories': categories[0],
                        'subcategories': categories[0]
                    }
        
        return {'categories': None, 'subcategories': None}
        
    except Exception as e:
        print(f"❌ Erreur extraction catégories joutech: {e}")
        return {'categories': None, 'subcategories': None}

def extract_main_image_joutech(soup):
    """Extrait l'URL de l'image principale depuis joutech.ma"""
    try:
        # Méthode 1: Image principale WooCommerce
        main_image = soup.select_one('.woocommerce-product-gallery__image img')
        if main_image:
            src = main_image.get('src') or main_image.get('data-src') or main_image.get('data-large_image')
            if src:
                return normalize_image_url(src, 'https://joutech.ma')
        
        # Méthode 2: Image produit WordPress
        product_image = soup.select_one('.product-image img, .wp-post-image')
        if product_image:
            src = product_image.get('src') or product_image.get('data-src')
            if src:
                return normalize_image_url(src, 'https://joutech.ma')
        
        # Méthode 3: Image avec itemprop="image"
        image_itemprop = soup.find('img', itemprop='image')
        if image_itemprop:
            src = image_itemprop.get('src') or image_itemprop.get('data-src')
            if src:
                return normalize_image_url(src, 'https://joutech.ma')
        
        return None
        
    except Exception as e:
        print(f"❌ Erreur extraction image joutech: {e}")
        return None

def normalize_image_url(url, base_url):
    """Normalise l'URL de l'image"""
    if not url:
        return None
    
    if url.startswith('//'):
        return 'https:' + url
    elif url.startswith('/'):
        return base_url + url
    elif not url.startswith('http'):
        return base_url + '/' + url
    
    return url

def extract_brand_joutech(soup):
    """Extrait la marque depuis joutech.ma - VERSION ULTRA-CORRIGÉE"""
    try:
        print("🔍 [JOUTECH] Recherche de marque...")
        
        # Liste noire des faux positifs
        BLACKLISTED_BRANDS = [
            'ÉTATNEUF', 'ETATNEUF', 'NEUF', 'OCCASION', 'OCCASIONNEUF',
            'RECONDITIONNÉ', 'RECONDITIONNE', 'REFURBISHED', 'GARANTIE',
            'LIVRAISON', 'GRATUITE', 'PROMOTION', 'SOLDE', 'STOCK',
            'ACCUEIL', 'HOME', 'BOUTIQUE', 'SHOP', 'CATÉGORIE', 'CATEGORY',
            'PRODUITS', 'PRODUCTS', 'RECHERCHE', 'SEARCH', 'CONTACT', 'À PROPOS',
            'JOUTECH', 'MARQUE', 'BRAND'
        ]
        
        # MÉTHODE 1: Analyser le titre du produit (TRÈS FIABLE)
        title_element = soup.find('h1', class_='product_title')
        if not title_element:
            title_element = soup.find('h1')
        
        if title_element:
            title_text = title_element.get_text()
            print(f"📝 [JOUTECH] Titre du produit: {title_text}")
            
            # Liste des marques connues
            known_brands = [
                'SYNOLOGY', 'HUAWEI', 'LENOVO', 'HP', 'DELL', 'ASUS', 'CANON', 'EPSON', 
                'SAMSUNG', 'ACER', 'BROTHER', 'LEXMARK', 'APC', 'TP-LINK', 'LOGITECH', 
                'MICROSOFT', 'JABRA', 'EATON', 'INTEL', 'ADATA', 'SANDISK', 'LACIE', 
                'TARGUS', 'MOBILIS', 'ORAY', 'HISENSE', 'V7', 'OMEN', 'ASUSROG', 
                'SPIRIT OF GAMER', 'PORT DESIGNS', 'WESTERN DIGITAL',
                'SEAGATE', 'TOSHIBA', 'KINGSTON', 'CRUCIAL', 'CORSAIR', 'G.SKILL',
                'HYPERX', 'PATRIOT', 'GEIL', 'TEAMGROUP', 'SILICON POWER', 'TRANSCEND',
                'APPLE', 'MSI', 'LG', 'SONY', 'RAZER', 'NVIDIA', 'AMD'
            ]
            
            # Chercher chaque marque dans le titre (en majuscules)
            title_upper = title_text.upper()
            for known_brand in known_brands:
                if known_brand in title_upper:
                    print(f"✅ [JOUTECH] Marque trouvée dans le titre: {known_brand}")
                    return known_brand
        
        # MÉTHODE 2: Attributs du produit WooCommerce
        attribute_tables = soup.find_all('table', class_='woocommerce-product-attributes-table')
        for table in attribute_tables:
            rows = table.find_all('tr')
            for row in rows:
                th = row.find('th')
                td = row.find('td')
                if th and td:
                    attribute_name = th.get_text(strip=True).lower()
                    if 'marque' in attribute_name or 'brand' in attribute_name or 'fabricant' in attribute_name:
                        brand_name = td.get_text(strip=True)
                        brand = clean_brand_name(brand_name)
                        if brand and brand not in BLACKLISTED_BRANDS:
                            print(f"✅ [JOUTECH] Marque trouvée via attribut produit: {brand}")
                            return brand
        
        # MÉTHODE 3: Meta du produit (posted_in, sku_wrapper, etc.)
        product_meta = soup.select_one('.product_meta')
        if product_meta:
            # Chercher "Marque:" dans le texte
            meta_text = product_meta.get_text()
            if 'Marque:' in meta_text or 'Brand:' in meta_text:
                # Extraire la marque après "Marque:"
                brand_match = re.search(r'Marque:\s*([^\n\r]+)', meta_text, re.IGNORECASE)
                if not brand_match:
                    brand_match = re.search(r'Brand:\s*([^\n\r]+)', meta_text, re.IGNORECASE)
                
                if brand_match:
                    brand_name = brand_match.group(1).strip()
                    brand = clean_brand_name(brand_name)
                    if brand and brand not in BLACKLISTED_BRANDS:
                        print(f"✅ [JOUTECH] Marque trouvée via meta produit: {brand}")
                        return brand
        
        # MÉTHODE 4: Breadcrumbs mais IGNORER "ACCUEIL" et autres éléments de navigation
        breadcrumb = soup.select('.woocommerce-breadcrumb a, .breadcrumb a')
        breadcrumb_brands = []
        
        for item in breadcrumb:
            text = item.get_text(strip=True)
            brand = clean_brand_name(text)
            if brand and brand not in BLACKLISTED_BRANDS and len(brand) > 2:
                breadcrumb_brands.append(brand)
                print(f"📝 [JOUTECH] Candidat breadcrumb: {brand}")
        
        # Prendre le DERNIER élément du breadcrumb (le plus spécifique)
        if breadcrumb_brands:
            final_brand = breadcrumb_brands[-1]
            print(f"✅ [JOUTECH] Marque trouvée via breadcrumb (dernier): {final_brand}")
            return final_brand
        
        # MÉTHODE 5: Catégories du produit
        posted_in = soup.select_one('.product_meta .posted_in')
        if posted_in:
            categories_text = posted_in.get_text()
            # Chercher des marques connues dans les catégories
            for known_brand in known_brands:
                if known_brand in categories_text.upper():
                    print(f"✅ [JOUTECH] Marque trouvée via catégories: {known_brand}")
                    return known_brand
        
        print("❌ [JOUTECH] Aucune marque valide trouvée")
        return None
        
    except Exception as e:
        print(f"❌ Erreur extraction marque joutech: {e}")
    except Exception as e:
        print(f"❌ Erreur extraction marque joutech: {e}")
        return None

def extract_attributes_joutech(soup):
    """Extrait les attributs (fiche technique) sur joutech.ma"""
    try:
        attributes = {}
        print("🔍 [JOUTECH] Recherche des attributs...")
        
        # Méthode 1: Table standard WooCommerce
        table = soup.find('table', class_='woocommerce-product-attributes')
        if table:
            rows = table.find_all('tr')
            for row in rows:
                key_elem = row.find(['th', 'td'], class_='woocommerce-product-attributes-item__label')
                val_elem = row.find(['td', 'th'], class_='woocommerce-product-attributes-item__value')
                
                if key_elem and val_elem:
                    key = key_elem.get_text(strip=True).rstrip(':')
                    value = val_elem.get_text(strip=True)
                    if key and value:
                        attributes[key] = value
        
        if attributes:
            print(f"✅ [JOUTECH] {len(attributes)} attributs trouvés")
            return attributes

        print("⚠️ [JOUTECH] Aucun attribut trouvé")
        return None
    except Exception as e:
        print(f"❌ Erreur extraction attributs joutech: {e}")
        return None

def ensure_data_consistency(data):
    """Assure la cohérence des données scrapées"""
    if not data:
        return None
    
    # Dupliquer les catégories en sous-catégories si nécessaire
    if data.get('categories') and not data.get('subcategories'):
        data['subcategories'] = data['categories']
        print(f"🔄 Cohérence: Catégories dupliquées en sous-catégories")
    
    # Utiliser la description courte comme description si nécessaire
    if not data.get('description') and data.get('short_description'):
        data['description'] = data['short_description']
        print(f"🔄 Cohérence: Description courte utilisée comme description")
    
    # Normaliser la marque
    if data.get('brand'):
        data['brand'] = clean_brand_name(data['brand'])
        print(f"🔄 Cohérence: Marque normalisée: {data['brand']}")
    
    # Nettoyer les textes
    if data.get('title'):
        data['title'] = clean_text(data['title'])
    
    return data


def extract_price_joutech(soup):
    """Extrait le prix depuis JOUTECH"""
    try:
        print("💰 [JOUTECH] Recherche du prix...")
        
        # Méthode 1: Prix avec itemprop="price"
        price_meta = soup.find('meta', itemprop='price')
        if price_meta:
            price_text = price_meta.get('content')
            if price_text:
                price = extract_price(price_text)
                if price:
                    print(f"✅ [JOUTECH] Prix trouvé (meta): {price} MAD")
                    return price, None
        
        # Méthode 2: Prix WooCommerce
        price_selectors = [
            '.price ins .woocommerce-Price-amount',
            '.price .woocommerce-Price-amount',
            '.current-price span[itemprop="price"]',
            '.product-price',
            '.price',
            'span.price'
        ]
        
        for selector in price_selectors:
            price_element = soup.select_one(selector)
            if price_element:
                price_text = price_element.get_text(strip=True)
                price = extract_price(price_text)
                if price:
                    print(f"✅ [JOUTECH] Prix trouvé ({selector}): {price} MAD")
                    
                    # Chercher ancien prix
                    old_price = None
                    old_price_selectors = [
                        '.price del .woocommerce-Price-amount',
                        '.regular-price',
                        '.old-price',
                        '.was-price'
                    ]
                    
                    for old_selector in old_price_selectors:
                        old_price_element = soup.select_one(old_selector)
                        if old_price_element:
                            old_price_text = old_price_element.get_text(strip=True)
                            old_price = extract_price(old_price_text)
                            if old_price and old_price > price:
                                print(f"✅ [JOUTECH] Ancien prix trouvé: {old_price} MAD")
                                break
                    
                    return price, old_price
        
        print("⚠️ [JOUTECH] Aucun prix trouvé")
        return None, None
    except Exception as e:
        print(f"❌ Erreur extraction prix JOUTECH: {e}")
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
        
        # Appeler le scraper joutech
        scraped_data = scraper_joutech_detaille(reference)
        
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
    """Fonction principale"""
    products = get_all_products_from_db("joutech")

    if not products:
        print("✅ Aucun produit avec statut 'pending' trouvé")
        return
    
    print(f"📊 {len(products)} produits à traiter")
    print("=" * 60)

    success_count = 0
    not_found_count = 0
    error_count = 0

    for i, product in enumerate(products, 1):
        product_id, reference, existing_title, existing_description, existing_short_description, \
        existing_categories, existing_subcategories, existing_brand, existing_image, existing_url, \
        existing_scraped_at = product
        
        print(f"\n🎯 PRODUIT {i}/{len(products)}")
        print(f"📦 Référence: {reference}")
        print(f"🆔 ID: {product_id}")
        
        # Scraper le produit
        scraped_data = scrap_product_for_site(reference, "joutech")
        
        # Compter les résultats
        if scraped_data:
            if scraped_data.get('status') == 'success':
                success_count += 1
                print(f"✅ Données récupérées pour {reference}")
            else:
                not_found_count += 1
                print(f"🚫 Produit non trouvé pour {reference}")
        else:
            error_count += 1
            print(f"❌ Échec pour {reference}")
        
        # Pause pour éviter de surcharger le serveur
        if i < len(products):
            print(f"\n⏳ Pause de 2 secondes...")
            time.sleep(2)
    
    # Résumé
    print(f"\n{'='*60}")
    print("📊 RÉCAPITULATIF DU SCRAPING JOUTECH.MA")
    print(f"{'='*60}")
    print(f"✅ Produits trouvés et mis à jour: {success_count}")
    print(f"🚫 Produits non trouvés sur le site: {not_found_count}")
    print(f"❌ Erreurs de scraping: {error_count}")
    print(f"📈 Total traité: {len(products)}")
    print(f"{'='*60}")

if __name__ == "__main__":
    # Test avec un produit spécifique
    # scrap_product_for_site("85A36EA", "joutech")
    
    # Lancer le scraping pour tous les produits pending
    main()