import requests
import urllib.parse
import re
import sys
import io

# Force UTF-8 stdout
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from bs4 import BeautifulSoup
import json
from utils import clean_text, clean_brand_name, clean_site_names_from_title,ensure_data_consistency, normalize_image_url , get_all_products_from_db , get_product_info_for_scraping , update_product_in_database
import time
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By


def setup_driver():
    """Configure le driver Selenium pour LinkSolutions"""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    driver = webdriver.Chrome(options=chrome_options)
    return driver

def scraper_linksolutions_detaille(reference):
    """Scrape LinkSolutions.ma avec Selenium pour gérer le JavaScript - VERSION AVEC ENCODAGE URL"""
    driver = None
    try:
        print(f"🔍 [LINKSOLUTIONS] Recherche de: {reference}")
        
        # Initialiser le driver
        driver = setup_driver()
        
        # 🔥 CORRECTION : Encoder la référence pour les caractères spéciaux
        encoded_reference = urllib.parse.quote(reference)
        search_url = f"https://linksolutions.ma/?s={encoded_reference}&post_type=product"
        
        print(f"🌐 URL encodée: {search_url}")
        print(f"📝 Référence originale: {reference}")
        print(f"🔤 Référence encodée: {encoded_reference}")
        
        # Charger la page
        driver.get(search_url)
        print(f"📡 Page chargée, attente du contenu...")
        
        # Attendre que la page soit chargée
        time.sleep(3)
        
        # VÉRIFIER SI ON A UNE REDIRECTION VERS UNE PAGE PRODUIT
        final_url = driver.current_url
        print(f"🔗 URL finale: {final_url}")
        
        # Vérifier si c'est une URL de produit
        is_product_page = any(term in final_url.lower() for term in ['/product/', '/produit/', '/shop/', 'product_id'])
        
        # Attendre que le contenu principal soit chargé
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            print(f"✅ Contenu chargé avec succès")
        except:
            print(f"⚠️  Timeout en attendant le contenu")
        
        # Récupérer le HTML complet
        html_content = driver.page_source
        
        # Parser avec BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # VÉRIFICATION STRICTE DE LA RÉFÉRENCE
        reference_match = verify_reference_linksolutions(soup, reference)
        
        if not reference_match or reference_match.upper() != reference.upper():
            print(f"❌ [LINKSOLUTIONS] RÉFÉRENCE NON TROUVÉE ou MISMATCH: Attendu '{reference}' mais trouvé '{reference_match}'")
            return None
        
        print(f"✅ [LINKSOLUTIONS] Référence vérifiée: {reference}")
        
        # Extraire les données (AVEC MARQUE)
        ref = reference_match
        title = extract_title_linksolutions(soup)
        description = extract_description_linksolutions(soup)
        short_description = extract_short_description_linksolutions(soup)
        categories_data = extract_categories_linksolutions(soup)
        image_url = extract_main_image_linksolutions(soup)
        image_url = extract_main_image_linksolutions(soup)
        brand = extract_brand_linksolutions(soup)
        attributes = extract_attributes_linksolutions(soup)  # NOUVEAU
        
        # 🔥 CORRECTION: Appliquer la cohérence immédiatement
        if categories_data.get('categories') and not categories_data.get('subcategories'):
            categories_data['subcategories'] = categories_data['categories']
        
        if not description and short_description:
            description = short_description
        
        data = {
            'source': 'linksolutions',
            'reference': ref,
            'title': title,
            'description': description,
            'short_description': short_description,
            'short_description': short_description,
            'attributes': json.dumps(attributes, ensure_ascii=False) if attributes else None,
            'categories': categories_data.get('categories'),
            'subcategories': categories_data.get('subcategories'),
            'product_url': final_url,
            'image': image_url,
            'brand': brand  # NOUVEAU
        }
        
        return ensure_data_consistency(data)
        
    except Exception as e:
        print(f"❌ [LINKSOLUTIONS] Erreur: {e}")
        return None
    finally:
        if driver:
            driver.quit()


def verify_reference_linksolutions(soup, expected_reference):
    """Vérifie la référence exacte sur la page produit LinkSolutions - VERSION STRICTE"""
    try:
        print(f"🔍 [LINKSOLUTIONS] Vérification stricte de la référence '{expected_reference}'")
        
        # VÉRIFIER D'ABORD SI C'EST UNE PAGE PRODUIT RÉELLE
        page_title = soup.find('title')
        if page_title:
            title_text = page_title.get_text(strip=True).lower()
            # Rejeter les pages de recherche ou pages génériques
            if any(term in title_text for term in ['recherche', 'search', 'vous avez cherché', 'aucun résultat']):
                print(f"❌ [LINKSOLUTIONS] Page de recherche générique détectée")
                return None
        
        # Vérifier les éléments indiquant une page produit
        product_indicators = [
            soup.find('div', class_='product'),
            soup.find('div', class_='product-details'),
            soup.find('div', class_='woocommerce-product-details'),
            soup.find('div', id='product'),
            soup.find('main', class_='single-product'),
            soup.find('form', class_='cart')
        ]
        
        has_product_structure = any(indicator for indicator in product_indicators)
        
        if not has_product_structure:
            print(f"❌ [LINKSOLUTIONS] Structure de page produit non détectée")
            return None

        # MÉTHODE 1: Chercher dans les spans avec class contenant sku/ref - PLUS STRICTE
        sku_elements = soup.find_all(['span', 'div'], class_=lambda x: x and any(word in str(x).lower() for word in ['sku', 'ref', 'reference', 'product-sku']))
        
        for element in sku_elements:
            text = element.get_text(strip=True)
            # Vérification EXACTE de la référence
            if text and text.upper() == expected_reference.upper():
                print(f"✅ [LINKSOLUTIONS] Référence exacte trouvée dans élément SKU: {text}")
                return text.upper()
        
        # MÉTHODE 2: Chercher dans les meta données
        meta_selectors = [
            'meta[property="product:sku"]',
            'meta[itemprop="sku"]',
            'meta[name="sku"]'
        ]
        
        for selector in meta_selectors:
            meta = soup.select_one(selector)
            if meta and meta.get('content'):
                content = meta.get('content').strip()
                if content.upper() == expected_reference.upper():
                    print(f"✅ [LINKSOLUTIONS] Référence exacte trouvée dans meta: {content}")
                    return content.upper()
        
        # MÉTHODE 3: Vérifier dans le contenu structuré JSON-LD
        script_tags = soup.find_all('script', type='application/ld+json')
        for script in script_tags:
            try:
                json_data = json.loads(script.string)
                # Vérifier dans les données structurées
                if isinstance(json_data, dict):
                    if json_data.get('sku') and json_data['sku'].upper() == expected_reference.upper():
                        print(f"✅ [LINKSOLUTIONS] Référence trouvée dans JSON-LD: {json_data['sku']}")
                        return json_data['sku'].upper()
                    # Vérifier dans les offres
                    if json_data.get('offers') and isinstance(json_data['offers'], dict):
                        if json_data['offers'].get('sku') and json_data['offers']['sku'].upper() == expected_reference.upper():
                            print(f"✅ [LINKSOLUTIONS] Référence trouvée dans JSON-LD offers: {json_data['offers']['sku']}")
                            return json_data['offers']['sku'].upper()
            except:
                continue
        
        print(f"❌ [LINKSOLUTIONS] Référence '{expected_reference}' non trouvée sur la page")
        return None
        
    except Exception as e:
        print(f"❌ Erreur vérification référence LinkSolutions: {e}")
        return None

def extract_brand_linksolutions(soup):
    """Extrait la marque depuis LinkSolutions - VERSION SIMPLE ET FIABLE"""
    try:
        print("🔍 [LINKSOLUTIONS] Recherche de marque...")
        
        # MÉTHODE 1: Analyser le titre du produit (LE PLUS FIABLE)
        title_element = soup.find('h1', class_='product_title') or soup.find('h1')
        if title_element:
            title_text = title_element.get_text()
            print(f"📝 [LINKSOLUTIONS] Titre: {title_text}")
            
            # Chercher directement les marques connues dans le titre
            known_brands = [
                'ASUS', 'HP', 'DELL', 'LENOVO', 'ACER', 'SAMSUNG', 'CANON', 'EPSON',
                'BROTHER', 'MICROSOFT', 'HUAWEI', 'APPLE', 'INTEL', 'LOGITECH'
            ]
            
            for brand in known_brands:
                if brand in title_text.upper():
                    print(f"✅ [LINKSOLUTIONS] Marque trouvée dans titre: {brand}")
                    return brand
        
        # MÉTHODE 2: Chercher dans les images avec "marque-" dans le src
        brand_images = soup.find_all('img', src=lambda x: x and 'marque-' in x.lower())
        
        for img in brand_images:
            # Prendre le alt de l'image
            alt_text = img.get('alt', '').strip()
            if alt_text:
                # Nettoyer simplement
                brand = alt_text.upper().strip()
                if len(brand) > 2 and len(brand) < 20:
                    print(f"✅ [LINKSOLUTIONS] Marque trouvée via image: {brand}")
                    return brand
        
        # MÉTHODE 3: Chercher dans les meta données
        meta_brand = soup.find('meta', property='product:brand')
        if meta_brand and meta_brand.get('content'):
            brand = meta_brand.get('content').strip().upper()
            if brand:
                print(f"✅ [LINKSOLUTIONS] Marque trouvée via meta: {brand}")
                return brand
        
        print("❌ [LINKSOLUTIONS] Aucune marque trouvée")
        return None
        
    except Exception as e:
        print(f"❌ Erreur extraction marque LinkSolutions: {e}")
    except Exception as e:
        print(f"❌ Erreur extraction marque LinkSolutions: {e}")
        return None

def extract_attributes_linksolutions(soup):
    """Extrait les attributs (fiche technique) depuis LinkSolutions"""
    try:
        attributes = {}
        print("🔍 [LINKSOLUTIONS] Recherche des attributs...")
        
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
                print(f"✅ [LINKSOLUTIONS] {len(attributes)} attributs trouvés via table WooCommerce")
                return attributes

        # Méthode 2: Chercher dans les onglets de description/information additionnelle
        # Souvent dans un div id="tab-additional_information"
        tab_content = soup.find('div', id='tab-additional_information') or soup.find('div', class_='additional-info')
        if tab_content:
            table = tab_content.find('table')
            if table:
                rows = table.find_all('tr')
                for row in rows:
                    cols = row.find_all(['td', 'th'])
                    if len(cols) >= 2:
                        key = cols[0].get_text(strip=True).rstrip(':')
                        value = cols[1].get_text(strip=True)
                        if key and value:
                            attributes[key] = value

            if attributes:
                print(f"✅ [LINKSOLUTIONS] {len(attributes)} attributs trouvés via onglet information")
                return attributes

        print("⚠️ [LINKSOLUTIONS] Aucun attribut trouvé")
        return None
    except Exception as e:
        print(f"❌ Erreur extraction attributs LinkSolutions: {e}")
        return None
   
def extract_title_linksolutions(soup):
    """Extrait le titre depuis LinkSolutions - VERSION CORRIGÉE"""
    try:
        # Méthode 1 (PRIORITAIRE): h1 - Le plus complet avec la référence
        h1_selectors = [
            'h1.product-title',
            'h1.entry-title',
            'h1.title',
            'h1'
        ]
        
        for selector in h1_selectors:
            h1 = soup.select_one(selector)
            if h1:
                title = h1.get_text(strip=True)
                if title and len(title) > 5:
                    return clean_site_names_from_title(title)
        
        # Méthode 2 (Fallback): Meta title (souvent tronqué)
        meta_title = soup.find('meta', property='og:title')
        if meta_title and meta_title.get('content'):
            title = meta_title.get('content').strip()
            return clean_site_names_from_title(title)
        
        # Méthode 3 (Fallback): Title tag (souvent tronqué)
        title_tag = soup.find('title')
        if title_tag:
            title = title_tag.get_text(strip=True)
            return clean_site_names_from_title(title)
        
        return None
    except Exception as e:
        print(f"❌ Erreur extraction titre LinkSolutions: {e}")
        return None 
    
def extract_description_linksolutions(soup):
    """Extrait la description complète depuis LinkSolutions"""
    # Chercher dans différentes sections
    selectors = [
        'div.product-description',
        'div.description',
        'div.woocommerce-product-details__short-description',
        'div.entry-content',
        'div.post-content',
        'div[itemprop="description"]',
        'section.description'
    ]
    
    for selector in selectors:
        desc = soup.select_one(selector)
        if desc:
            # Nettoyer le HTML
            for element in desc(['script', 'style', 'nav', 'header', 'footer']):
                element.decompose()
            return str(desc)
    
    return None

def extract_short_description_linksolutions(soup):
    """Extrait la description courte en HTML depuis LinkSolutions"""
    try:
        # Méthode 1: Chercher la div woocommerce-product-details__short-description (PRIORITAIRE)
        short_desc_div = soup.find('div', class_='woocommerce-product-details__short-description')
        if short_desc_div:
            # Vérifier que ce n'est pas juste du texte de prix
            text_content = short_desc_div.get_text(strip=True)
            # Rejeter si c'est principalement des prix (contient "DH" et des chiffres)
            if 'DH' in text_content and any(char.isdigit() for char in text_content):
                # Vérifier le ratio prix/texte
                price_indicators = text_content.count('DH') + text_content.count('prix')
                if price_indicators > 2 or len(text_content) < 100:
                    print(f"⚠️  [LINKSOLUTIONS] Description courte rejetée (contient surtout des prix)")
                else:
                    print(f"✅ [LINKSOLUTIONS] Description courte HTML trouvée (méthode 1)")
                    return str(short_desc_div)
            else:
                print(f"✅ [LINKSOLUTIONS] Description courte HTML trouvée (méthode 1)")
                return str(short_desc_div)
        
        # Méthode 2: Chercher un paragraphe avec itemprop="description"
        desc_p = soup.find('p', itemprop='description')
        if desc_p:
            text_content = desc_p.get_text(strip=True)
            if len(text_content) > 50 and 'DH' not in text_content[:50]:  # Pas de prix au début
                print(f"✅ [LINKSOLUTIONS] Description courte HTML trouvée (méthode 2)")
                return str(desc_p)
        
        # Méthode 3: Chercher dans les divs avec class contenant "short" ou "excerpt"
        for selector in ['div.short-description', 'div.product-excerpt', 'div.excerpt']:
            elem = soup.select_one(selector)
            if elem:
                text_content = elem.get_text(strip=True)
                if len(text_content) > 50:
                    print(f"✅ [LINKSOLUTIONS] Description courte HTML trouvée (méthode 3: {selector})")
                    return str(elem)
        
        print(f"❌ [LINKSOLUTIONS] Aucune description courte HTML valide trouvée")
        return None
        
    except Exception as e:
        print(f"❌ Erreur extraction description courte LinkSolutions: {e}")
        return None

def extract_categories_linksolutions(soup):
    """Extrait les catégories depuis LinkSolutions - VERSION ADAPTATIVE"""
    # Breadcrumb
    breadcrumb_selectors = [
        'nav.breadcrumb',
        'div.breadcrumbs',
        'ol.breadcrumb',
        'nav[aria-label="Breadcrumb"]',
        '.woocommerce-breadcrumb'
    ]
    
    categories = []
    
    for selector in breadcrumb_selectors:
        breadcrumb = soup.select_one(selector)
        if breadcrumb:
            # Récupérer tous les spans avec typeof="v:Breadcrumb" qui contiennent des liens
            breadcrumb_items = breadcrumb.find_all('span', typeof='v:Breadcrumb')
            
            for item in breadcrumb_items:
                link = item.find('a')
                if link:
                    cat = link.get_text(strip=True)
                    if cat and cat.lower() not in ['accueil', 'home', 'boutique', 'shop', 'linksolutions']:
                        categories.append(cat)
            
            if categories:
                break
    
    print(f"🔍 [LINKSOLUTIONS] Catégories trouvées: {categories}")
    
    if len(categories) >= 2:
        # Si on a au moins 2 catégories :
        # - categories = avant-dernière
        # - subcategories = dernière
        return {
            'categories': categories[-2],  # Avant-dernière
            'subcategories': categories[-1],  # Dernière
        }
    elif len(categories) == 1:
        # Si on a seulement 1 catégorie :
        # - categories = cette catégorie
        # - subcategories = cette même catégorie
        return {
            'categories': categories[0],
            'subcategories': categories[0],
        }
    else:
        # Si pas de catégories
        return {'categories': None, 'subcategories': None}
    
def extract_main_image_linksolutions(soup):
    """Extrait l'URL de l'image principale depuis LinkSolutions"""
    # Méthode 1: Meta og:image (image principale)
    meta_image = soup.find('meta', property='og:image')
    if meta_image and meta_image.get('content'):
        return normalize_image_url(meta_image.get('content'), 'https://linksolutions.ma')
    
    # Méthode 2: Image de la galerie principale WooCommerce
    main_image_selectors = [
        '.woocommerce-product-gallery__image img',
        '.product-gallery img',
        '.wp-post-image',
        '.product-image img',
        'img.attachment-woocommerce_single'
    ]
    
    for selector in main_image_selectors:
        img = soup.select_one(selector)
        if img:
            src = (img.get('src') or 
                   img.get('data-src') or 
                   img.get('data-large_image') or 
                   img.get('data-lazy-src'))
            if src:
                return normalize_image_url(src, 'https://linksolutions.ma')
    
    return None


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
        
        # Appeler le scraper linksolutions
        scraped_data = scraper_linksolutions_detaille(reference)
        
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
    products = get_all_products_from_db("linksolutions")

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
        scraped_data = scrap_product_for_site(reference, "linksolutions")
        
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
    # scrap_product_for_site("90NB13Y2-M00V10", "linksolutions")
    # if scraped_data:
    #     print(f"Données récupérées: {scraped_data}")
    
    # Lancer le scraping pour tous les produits pending
    main()