import requests
from bs4 import BeautifulSoup
import re
import time
from utils import get_all_products_from_db, get_product_info_for_scraping, update_product_in_database
from utils_2 import clean_encoding, clean_html_content, strip_problematic_characters
import json

def scraper_mies_detaille(reference):
    """Scrape les données détaillées pour une référence donnée sur mies.ma"""
    try:
        url = f"https://www.mies.ma/recherche?controller=search&s={reference}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        }
        
        print(f"🔍 Recherche du produit sur mies.ma: {reference}")
        
        session = requests.Session()
        session.headers.update(headers)
        
        response = session.get(url, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        if detect_no_products_mies(soup, reference):
            print(f"🚫 PRODUIT NON TROUVÉ sur mies.ma: '{reference}'")
            return create_not_found_response(reference, 'not_found')
        
        product_link = find_product_link_mies(soup, reference)
        
        if not product_link:
            print(f"❌ Aucun lien produit trouvé sur mies.ma pour '{reference}'")
            return create_not_found_response(reference, 'link_not_found')
        
        product_url = product_link.get('href')
        product_url = normalize_url_mies(product_url)
        
        print(f"✅ Produit trouvé sur mies.ma, accès à: {product_url}")
        return scraper_mies_product_details(product_url, reference)
        
    except requests.exceptions.Timeout:
        print(f"❌ Timeout lors de la recherche mies.ma de {reference}")
        return create_not_found_response(reference, 'timeout')
    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur réseau lors du scraping mies.ma de {reference}: {e}")
        return create_not_found_response(reference, 'network_error')
    except Exception as e:
        print(f"❌ Erreur inattendue lors du scraping mies.ma de {reference}: {e}")
        return create_not_found_response(reference, 'error')

def scraper_mies_product_details(product_url, expected_reference):
    """Scrape les détails complets depuis la page produit mies.ma"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8'
        }
        
        print(f"🌐 Accès à la page produit détaillée mies.ma...")
        response = requests.get(product_url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Vérification flexible de la référence
        reference_match = verify_mies_reference_flexible(soup, expected_reference)
        if not reference_match:
            print(f"⚠️ Référence non exacte sur mies.ma, mais produit trouvé - continuation")
        
        print(f"✅ Produit mies.ma confirmé: {expected_reference}")
        
        title = extract_mies_title(soup)
        description = extract_mies_description(soup)
        short_description = extract_mies_short_description(soup)
        categories_data = extract_mies_categories(soup)
        image_url = extract_mies_image(soup)
        brand = extract_mies_brand(soup)
        attributes = extract_mies_attributes(soup) # NOUVEAU
        
        # Assurer la cohérence des données comme dans update_product_in_database
        if not categories_data.get('subcategories') and categories_data.get('categories'):
            categories_data['subcategories'] = categories_data['categories']
            print(f"🔄 mies: Catégories dupliquées en sous-catégories")
        
        if not description and short_description:
            description = short_description
            print(f"🔄 mies: Description courte utilisée comme description")
        
        return {
            'reference': expected_reference,
            'title': title,
            'description': description,
            'short_description': short_description,
            'categories': categories_data.get('categories'),
            'subcategories': categories_data.get('subcategories'),
            'subcategories': categories_data.get('subcategories'),
            'image': image_url,  # Note: utiliser 'image' au lieu de 'image_url' pour la cohérence
            'brand': brand,
            'attributes': json.dumps(attributes, ensure_ascii=False) if attributes else None,
            'product_url': product_url,
            'status': 'success',
            'source': 'mies'
        }
        
    except Exception as e:
        print(f"❌ Erreur lors du scraping des détails mies.ma: {e}")
        return None

def detect_no_products_mies(soup, reference):
    """Détection des pages 'produit non trouvé' sur mies.ma"""
    error_indicators = [
        '.page-not-found',
        '.search-no-results',
        '.no-products',
        '.alert-warning'
    ]
    
    for selector in error_indicators:
        element = soup.select_one(selector)
        if element:
            element_text = element.get_text(strip=True).lower()
            if any(phrase in element_text for phrase in ['aucun', 'aucune', 'introuvable', 'no result']):
                return True
    
    products = soup.select('.product-miniature, .product, .ajax_block_product')
    if not products:
        return True
    
    return False

def create_not_found_response(reference, status='not_found'):
    """Crée une réponse standard pour les produits non trouvés"""
    return {
        'reference': reference,
        'title': None,
        'description': None,
        'short_description': None,
        'categories': None,
        'subcategories': None,
        'brand': None,
        'image': None,
        'product_url': None,
        'status': status
    }

def find_product_link_mies(soup, reference):
    """Recherche du lien produit sur mies.ma"""
    standard_selectors = [
        'a.product_img_link',
        'a.product-name', 
        '.product-title a',
        '.product-miniature a',
        '.ajax_block_product a'
    ]
    
    for selector in standard_selectors:
        links = soup.select(selector)
        for link in links:
            if is_likely_product_link_mies(link, reference):
                return link
    
    all_links = soup.find_all('a', href=True)
    for link in all_links:
        if is_likely_product_link_mies(link, reference):
            return link
    
    return None

def is_likely_product_link_mies(link, reference):
    """Détermine si un lien mène probablement à un produit sur mies.ma"""
    href = link.get('href', '').lower()
    text = link.get_text(strip=True).lower()
    ref_lower = reference.lower()
    
    excluded_patterns = [
        '/recherche',
        '/contact',
        '/blog',
        'controller=search'
    ]
    
    for pattern in excluded_patterns:
        if pattern in href:
            return False
    
    positive_indicators = [
        ref_lower in href,
        ref_lower in text,
        any(ref_lower in span.get_text(strip=True).lower() 
            for span in link.find_all(['span', 'div', 'h3', 'h4']))
    ]
    
    return any(positive_indicators)

def normalize_url_mies(url):
    """Normalise l'URL du produit pour mies.ma"""
    if not url:
        return None
        
    if url.startswith('//'):
        return 'https:' + url
    elif url.startswith('/'):
        return 'https://www.mies.ma' + url
    elif not url.startswith('http'):
        return 'https://www.mies.ma/' + url
    
    return url

def verify_mies_reference_flexible(soup, expected_reference):
    """Vérifie la référence sur mies.ma - VERSION FLEXIBLE"""
    try:
        expected_clean = re.sub(r'[^a-zA-Z0-9]', '', expected_reference).upper()
        
        reference_selectors = [
            '.product-reference',
            '.reference',
            '[itemprop="sku"]'
        ]
        
        for selector in reference_selectors:
            ref_element = soup.select_one(selector)
            if ref_element:
                found_ref = ref_element.get_text(strip=True)
                found_ref_clean = re.sub(r'[^a-zA-Z0-9]', '', found_ref).upper()
                
                if found_ref_clean and found_ref_clean == expected_clean:
                    return True
        
        # Si aucune référence exacte trouvée, vérifier dans le titre
        title_element = soup.select_one('h1.page-title, h1.product-name, h1')
        if title_element:
            title_text = title_element.get_text(strip=True).upper()
            if expected_clean in title_text:
                print(f"✅ Référence trouvée dans le titre")
                return True
        
        return False
    except Exception as e:
        print(f"❌ Erreur vérification référence mies: {e}")
        return False

def extract_mies_title(soup):
    """Extrait le titre du produit sur mies.ma"""
    try:
        title_selectors = [
            'h1.page-title',
            'h1.product-name',
            'h1'
        ]
        
        for selector in title_selectors:
            title_element = soup.select_one(selector)
            if title_element:
                title = title_element.get_text(strip=True)
                if title:
                    return strip_problematic_characters(clean_encoding(title))
        
        return None
    except Exception as e:
        print(f"❌ Erreur extraction titre mies: {e}")
        return None

def extract_mies_description(soup):
    """Extrait la description sur mies.ma"""
    try:
        description_selectors = [
            'section.product-features',
            'dl.data-sheet',
            '.product-description'
        ]
        
        for selector in description_selectors:
            desc_element = soup.select_one(selector)
            if desc_element:
                html_content = str(desc_element)
                return strip_problematic_characters(clean_html_content(html_content))
        
        return None
    except Exception as e:
        print(f"❌ Erreur extraction description mies: {e}")
        return None

def extract_mies_short_description(soup):
    """Extrait la description courte sur mies.ma"""
    try:
        short_desc_selectors = [
            '[id^="product-description-short"]',
            '.product-description-short'
        ]
        
        for selector in short_desc_selectors:
            short_desc_element = soup.select_one(selector)
            if short_desc_element:
                html_content = str(short_desc_element)
                return strip_problematic_characters(clean_html_content(html_content))
        
        return None
    except Exception as e:
        print(f"❌ Erreur extraction description courte mies: {e}")
        return None

def extract_mies_categories(soup):
    """Extrait les catégories sur mies.ma"""
    try:
        breadcrumb = soup.select('.breadcrumb a')
        
        if breadcrumb and len(breadcrumb) >= 3:
            categories = []
            
            for item in breadcrumb:
                category = item.get_text(strip=True)
                if category and category.lower() not in ['accueil', 'home']:
                    categories.append(strip_problematic_characters(clean_encoding(category)))
            
            if len(categories) >= 2:
                return {
                    'categories': categories[0],
                    'subcategories': categories[1]
                }
            elif len(categories) == 1:
                return {
                    'categories': categories[0],
                    'subcategories': None
                }
        
        return {'categories': None, 'subcategories': None}
    except Exception as e:
        print(f"❌ Erreur extraction catégories mies: {e}")
        return {'categories': None, 'subcategories': None}

def extract_mies_image(soup):
    """Extrait l'image sur mies.ma"""
    try:
        image_selectors = [
            '.product-cover img',
            '#product-cover img',
            '[itemprop="image"]'
        ]
        
        for selector in image_selectors:
            img_element = soup.select_one(selector)
            if img_element:
                src = img_element.get('data-src') or img_element.get('src')
                if src:
                    if not src.startswith('http'):
                        if src.startswith('//'):
                            src = 'https:' + src
                        elif src.startswith('/'):
                            src = 'https://www.mies.ma' + src
                    return src
        
        return None
    except Exception as e:
        print(f"❌ Erreur extraction image mies: {e}")
        return None

def extract_mies_brand(soup):
    """Extrait la marque du produit sur mies.ma"""
    try:
        # Sélecteurs pour la marque sur mies.ma
        brand_selectors = [
            '.product-manufacturer img',
            '.manufacturer-logo',
            '.product-brand img',
            '[itemprop="brand"] img'
        ]
        
        for selector in brand_selectors:
            brand_element = soup.select_one(selector)
            if brand_element:
                # Extraire le nom de la marque depuis l'attribut alt
                brand_name = brand_element.get('alt', '').strip()
                if brand_name:
                    return strip_problematic_characters(clean_encoding(brand_name))
                
                # Fallback: extraire depuis le texte autour
                parent = brand_element.find_parent('div', class_='product-manufacturer')
                if parent:
                    # Chercher le texte dans les éléments parents
                    brand_text = parent.get_text(strip=True)
                    if brand_text and brand_text.lower() not in ['marque', 'brand']:
                        return strip_problematic_characters(clean_encoding(brand_text))
        
        # Fallback: chercher dans les liens de breadcrumb ou autres éléments
        brand_link = soup.find('a', href=lambda x: x and '/marque/' in x) or \
                    soup.find('a', href=lambda x: x and '/brand/' in x)
        if brand_link:
            brand_name = brand_link.get_text(strip=True)
            if brand_name:
                return strip_problematic_characters(clean_encoding(brand_name))
        
        return None
    except Exception as e:
        print(f"❌ Erreur extraction marque mies: {e}")
        return None

def extract_mies_attributes(soup):
    """Extrait les attributs (fiche technique) sur mies.ma"""
    try:
        attributes = {}
        print("🔍 [MIES] Recherche des attributs...")
        
        # Méthode 1: Section product-features
        features_section = soup.find('section', class_='product-features')
        if features_section:
            # Chercher dl/dt/dd
            dls = features_section.find_all('dl', class_='data-sheet')
            for dl in dls:
                dt = dl.find('dt', class_='name')
                dd = dl.find('dd', class_='value')
                
                if dt and dd:
                    key = dt.get_text(strip=True).rstrip(':')
                    value = dd.get_text(strip=True)
                    if key and value:
                        attributes[key] = value
            
            if attributes:
                print(f"✅ [MIES] {len(attributes)} attributs trouvés via dl/dt/dd")
                return attributes
        
        # Méthode 2: Table
        table = soup.find('table', class_='table-data-sheet')
        if table:
            rows = table.find_all('tr')
            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 2:
                    key = cols[0].get_text(strip=True).rstrip(':')
                    value = cols[1].get_text(strip=True)
                    if key and value:
                        attributes[key] = value

            if attributes:
                print(f"✅ [MIES] {len(attributes)} attributs trouvés via table")
                return attributes

        print("⚠️ [MIES] Aucun attribut trouvé")
        return None
    except Exception as e:
        print(f"❌ Erreur extraction attributs mies: {e}")
        return None

def scrap_product_for_site(reference, site_name):
    """
    Scrape un produit pour un site spécifique
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
        
        # Appeler le scraper mies
        scraped_data = scraper_mies_detaille(reference)
        
        if not scraped_data:
            print(f"❌ Scraping échoué pour {reference}")
            # Tenter quand même de mettre à jour le statut
            update_product_in_database(product_id, None, site_name, scraping_success=False)
            return None
        
        # Vérifier si le scraping a réussi
        if scraped_data.get('status') == 'success':
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
            
            return scraped_data
        else:
            # Produit non trouvé sur le site
            print(f"🚫 Produit non trouvé sur mies.ma pour {reference}")
            update_product_in_database(product_id, None, site_name, scraping_success=False)
            return None
            
    except Exception as e:
        print(f"❌ Erreur lors du scraping de {reference} sur {site_name}: {e}")
        return None

def main():
    """Fonction principale"""
    products = get_all_products_from_db("mies")

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
        scraped_data = scrap_product_for_site(reference, "mies")
        
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
    print("📊 RÉCAPITULATIF DU SCRAPING MIES.MA")
    print(f"{'='*60}")
    print(f"✅ Produits trouvés et mis à jour: {success_count}")
    print(f"🚫 Produits non trouvés sur le site: {not_found_count}")
    print(f"❌ Erreurs de scraping: {error_count}")
    print(f"📈 Total traité: {len(products)}")
    print(f"{'='*60}")

if __name__ == "__main__":
    # Test avec un produit spécifique
    # scrap_product_for_site("VOTRE_REFERENCE", "mies")
    
    # Lancer le scraping pour tous les produits pending
    main()