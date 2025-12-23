import requests
import urllib.parse
import re
from bs4 import BeautifulSoup
import json
from utils import clean_text, clean_brand_name, clean_site_names_from_title,ensure_data_consistency, normalize_image_url , get_all_products_from_db , get_product_info_for_scraping , update_product_in_database, extract_price
import time

def scraper_duga_detaille(reference):
    """Scrape les données détaillées depuis Duga.ma - VERSION AVEC ENCODAGE URL"""
    try:
        # 🔥 CORRECTION : Encoder la référence
        encoded_reference = urllib.parse.quote(reference)
        url = f"https://duga.ma/?s={encoded_reference}&product_cat=0&post_type=product"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8'
        }
        
        print(f"🔍 [DUGA] Recherche du produit: {reference}")
        print(f"🔤 Référence encodée: {encoded_reference}")
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # VÉRIFIER SI C'EST UNE PAGE DE RECHERCHE AVEC RÉSULTATS
        no_results = soup.find('p', class_='woocommerce-info')
        if no_results and "Aucun produit" in no_results.get_text():
            print(f"❌ [DUGA] Aucun produit trouvé pour '{reference}'")
            return None
        
        # Trouver les produits sur la page de recherche Duga
        products = soup.find_all('li', class_='product')
        
        if not products:
            print(f"❌ [DUGA] Aucun produit trouvé sur la page de recherche pour {reference}")
            return None
        
        print(f"📦 [DUGA] {len(products)} produits trouvés sur la page de recherche")
        
        # Chercher le produit avec la référence EXACTE
        exact_match_url = None
        
        for i, product in enumerate(products, 1):
            product_link = product.find('a', class_='woocommerce-LoopProduct-link')
            if not product_link:
                continue
                
            product_url = product_link.get('href')
            
            # Accéder à chaque page produit pour vérifier la référence
            try:
                print(f"  🔎 [DUGA] Vérification du produit {i}/{len(products)}: {product_url}")
                product_response = requests.get(product_url, headers=headers, timeout=10)
                product_response.raise_for_status()
                product_soup = BeautifulSoup(product_response.content, 'html.parser')
                
                # VÉRIFICATION STRICTE DE LA RÉFÉRENCE
                found_reference = verify_reference_duga(product_soup)
                
                if found_reference and found_reference.upper() == reference.upper():
                    print(f"  ✅ [DUGA] RÉFÉRENCE EXACTE TROUVÉE: {reference}")
                    exact_match_url = product_url
                    break
                else:
                    if found_reference:
                        print(f"  ❌ [DUGA] Référence différente: '{found_reference}' (attendu: '{reference}')")
                    else:
                        print(f"  ⚠️  [DUGA] Référence non trouvée sur la page")
                    
            except Exception as e:
                print(f"  ⚠️  [DUGA] Erreur vérification produit: {e}")
                continue
        
        if not exact_match_url:
            print(f"❌ [DUGA] Aucun produit avec la référence exacte '{reference}' trouvé")
            return None
        
        print(f"🌐 [DUGA] Accès à la page produit exacte: {exact_match_url}")
        
        # Maintenant scraper la page détaillée du produit
        return scraper_duga_product_details(exact_match_url, reference)
        
    except Exception as e:
        print(f"❌ [DUGA] Erreur lors du scraping de {reference}: {e}")
        return None

def verify_reference_duga(soup):
    """Vérifie la référence directement depuis la page produit Duga - VERSION STRICTE"""
    try:
        # Chercher le SKU dans Duga
        sku_element = soup.find('span', class_='sku')
        if sku_element:
            found_reference = sku_element.get_text(strip=True)
            return found_reference
        
        # Chercher dans les meta données
        sku_meta = soup.find('meta', itemprop='sku')
        if sku_meta:
            found_reference = sku_meta.get('content', '').strip()
            return found_reference
        
        # Chercher dans le titre
        title_element = soup.find('h1', class_='product_title')
        if title_element:
            title_text = title_element.get_text(strip=True)
            # Essayer d'extraire la référence du titre
            if '(' in title_text and ')' in title_text:
                ref_match = re.search(r'\((.*?)\)', title_text)
                if ref_match:
                    return ref_match.group(1)
        
        return None
        
    except Exception as e:
        print(f"❌ Erreur vérification référence Duga: {e}")
        return None

def scraper_duga_product_details(product_url, expected_reference):
    """Scrape les détails complets depuis la page produit Duga - VERSION AVEC MARQUE"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
            'Referer': 'https://duga.ma/'
        }
        
        print(f"🌐 [DUGA] Accès à la page produit détaillée...")
        response = requests.get(product_url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # VÉRIFICATION STRICTE DE LA RÉFÉRENCE
        reference_match = verify_reference_duga(soup)
        if not reference_match or reference_match.upper() != expected_reference.upper():
            print(f"❌ [DUGA] RÉFÉRENCE MISMATCH: Attendu '{expected_reference}' mais trouvé '{reference_match}'")
            return None
        
        print(f"✅ [DUGA] Référence vérifiée: {expected_reference}")
        
        # Extraire les données (AVEC MARQUE ET PRIX)
        title = extract_title_duga(soup)
        description = extract_specifications_table_html_duga(soup)
        short_description = extract_short_description_html_duga(soup)
        specifications_table = extract_specifications_table_duga(soup)
        categories_data = extract_categories_duga(soup)
        image_url = extract_main_image_duga(soup)
        brand = extract_brand_duga(soup)
        price, old_price = extract_price_duga(soup)  # NOUVEAU
        
        # 🔥 CORRECTION: Appliquer la cohérence immédiatement
        if categories_data.get('categories') and not categories_data.get('subcategories'):
            categories_data['subcategories'] = categories_data['categories']
        
        if not description and short_description:
            description = short_description
        
        data = {
            'source': 'duga',
            'reference': expected_reference,
            'title': title,
            'description': description,
            'short_description': short_description,
            'attributes': json.dumps(specifications_table, ensure_ascii=False) if specifications_table else None,
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
        print(f"❌ [DUGA] Erreur lors du scraping des détails: {e}")
        return None

def extract_title_duga(soup):
    """Extrait le titre du produit Duga - VERSION CORRIGÉE"""
    try:
        title_element = soup.find('h1', class_='product_title')
        if title_element:
            title = title_element.get_text(strip=True)
            return clean_site_names_from_title(title)
        
        # Fallback pour Duga
        meta_title = soup.find('meta', property='og:title')
        if meta_title and meta_title.get('content'):
            title = meta_title.get('content').strip()
            return clean_site_names_from_title(title)
        
        return None
    except Exception as e:
        print(f"❌ Erreur extraction titre Duga: {e}")
        return None

def extract_specifications_table_html_duga(soup):
    """Extrait le HTML complet de la table des spécifications techniques pour la DESCRIPTION"""
    try:
        print("🔍 [DUGA] Recherche de la table des spécifications...")
        
        # Méthode 1: Chercher directement la liste des spécifications
        specs_list = soup.find('ul', class_='duga-product-specs-attributes')
        if specs_list:
            print("✅ [DUGA] Liste des spécifications trouvée directement")
            return str(specs_list)
        
        # Méthode 2: Chercher avec sélecteur CSS plus large
        specs_list = soup.select('ul[class*="duga-product-specs-attributes"]')
        if specs_list:
            print("✅ [DUGA] Liste des spécifications trouvée avec sélecteur CSS large")
            return str(specs_list[0])
        
        # Méthode 3: Chercher la section des spécifications techniques
        specs_section = soup.find('section', class_='duga-product-details-section')
        if specs_section:
            print("✅ [DUGA] Section spécifications techniques trouvée")
            
            # Trouver le contenu des spécifications
            specs_content = specs_section.find('div', id='specifications')
            if specs_content:
                print("✅ [DUGA] Contenu des spécifications trouvé")
                
                # Extraire la liste des spécifications
                specs_list = specs_content.find('ul', class_='duga-product-specs-attributes')
                if specs_list:
                    print("✅ [DUGA] Liste des spécifications extraite pour la DESCRIPTION")
                    return str(specs_list)
        
        # Méthode 4: Chercher par texte des spécifications
        if "Processeur" in str(soup) and "Mémoire RAM" in str(soup):
            print("🔍 [DUGA] Textes de spécifications trouvés, recherche avancée...")
            # Chercher un ul qui contient à la fois "Processeur" et "Mémoire RAM"
            all_ul = soup.find_all('ul')
            for ul in all_ul:
                ul_text = ul.get_text()
                if "Processeur" in ul_text and "Mémoire RAM" in ul_text:
                    print("✅ [DUGA] Liste des spécifications trouvée par contenu texte")
                    return str(ul)
        
        print("❌ [DUGA] Aucune table de spécifications trouvée")
        return None
        
    except Exception as e:
        print(f"❌ Erreur extraction table spécifications Duga: {e}")
        return None

def extract_short_description_html_duga(soup):
    """Extrait la description courte en HTML complet depuis Duga"""
    try:
        short_desc_div = soup.find('div', class_='woocommerce-product-details__short-description')
        if short_desc_div:
            print("✅ [DUGA] Description courte HTML trouvée")
            return str(short_desc_div)
        
        return None
    except Exception as e:
        print(f"❌ Erreur extraction description courte HTML Duga: {e}")
        return None

def extract_specifications_table_duga(soup):
    """Extrait spécifiquement le tableau des spécifications techniques sous forme structurée"""
    try:
        print("🔍 [DUGA] Extraction des spécifications structurées...")
        
        # Méthode directe
        specs_list = soup.find('ul', class_='duga-product-specs-attributes')
        if not specs_list:
            # Chercher avec sélecteur CSS large
            specs_list = soup.select('ul[class*="duga-product-specs-attributes"]')
            if specs_list:
                specs_list = specs_list[0]
        
        if not specs_list:
            # Chercher par contenu texte
            all_ul = soup.find_all('ul')
            for ul in all_ul:
                ul_text = ul.get_text()
                if "Processeur" in ul_text and "Mémoire RAM" in ul_text:
                    specs_list = ul
                    break
        
        if not specs_list:
            return None
        
        # Extraire les attributs de spécifications
        specs_attributes = specs_list.find_all('li', class_='duga-product-specs-attribute')
        if not specs_attributes:
            # Si pas de classe spécifique, chercher tous les li dans la liste
            specs_attributes = specs_list.find_all('li')
        
        if not specs_attributes:
            return None
        
        specifications = {}
        
        for attribute in specs_attributes:
            # Extraire le nom de l'attribut (h6 ou premier strong)
            attribute_name_elem = attribute.find('h6')
            if not attribute_name_elem:
                attribute_name_elem = attribute.find('strong')
            if not attribute_name_elem:
                continue
                
            attribute_name = attribute_name_elem.get_text(strip=True).replace(':', '')
            
            # Extraire la valeur de l'attribut
            attribute_value_elem = attribute.find('span')
            if not attribute_value_elem:
                # Prendre le texte après le strong
                attribute_text = attribute.get_text(strip=True)
                if ':' in attribute_text:
                    attribute_value = attribute_text.split(':', 1)[1].strip()
                else:
                    attribute_value = attribute_text.replace(attribute_name, '').strip()
            else:
                attribute_value = attribute_value_elem.get_text(strip=True)
            
            if attribute_name and attribute_value:
                specifications[attribute_name] = attribute_value
        
        print(f"✅ [DUGA] {len(specifications)} spécifications techniques extraites")
        return specifications
        
    except Exception as e:
        print(f"❌ Erreur extraction tableau spécifications Duga: {e}")
        return None

def extract_categories_duga(soup):
    """Extrait les catégories depuis Duga"""
    try:
        breadcrumb = soup.select('.woocommerce-breadcrumb a')
        
        if breadcrumb and len(breadcrumb) >= 2:
            categories = []
            
            for item in breadcrumb:
                category = item.get_text(strip=True)
                if category and category.lower() not in ['accueil', 'home', '']:
                    categories.append(category)
            
            print(f"📊 [DUGA] Catégories trouvées: {categories}")
            
            if categories:
                return {
                    'categories': categories[0] if categories else None,
                    'subcategories': ', '.join(categories) if categories else None
                }
        
        return {'categories': None, 'subcategories': None}
        
    except Exception as e:
        print(f"❌ Erreur extraction catégories Duga: {e}")
        return {'categories': None, 'subcategories': None}

def extract_main_image_duga(soup):
    """Extrait l'URL de l'image principale depuis Duga"""
    try:
        # Méthode 1: Image principale WooCommerce
        main_image = soup.select_one('.woocommerce-product-gallery__image img')
        if main_image:
            src = (main_image.get('src') or 
                   main_image.get('data-src') or 
                   main_image.get('data-large_image'))
            if src:
                return normalize_image_url(src, 'https://duga.ma')
        
        # Méthode 2: Image wp-post-image
        wp_image = soup.find('img', class_='wp-post-image')
        if wp_image:
            src = wp_image.get('src') or wp_image.get('data-src')
            if src:
                return normalize_image_url(src, 'https://duga.ma')
        
        # Méthode 3: Meta og:image
        meta_image = soup.find('meta', property='og:image')
        if meta_image and meta_image.get('content'):
            return meta_image.get('content')
        
        return None
        
    except Exception as e:
        print(f"❌ Erreur extraction image Duga: {e}")
        return None

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

def extract_price_duga(soup):
    """Extrait le prix depuis Duga"""
    try:
        print("💰 [DUGA] Recherche du prix...")
        
        # Méthode 1: Meta tag product:price:amount (le plus fiable)
        price_meta = soup.find('meta', property='product:price:amount')
        if price_meta and price_meta.get('content'):
            price_text = price_meta.get('content')
            price = extract_price(price_text)
            if price:
                print(f"✅ [DUGA] Prix trouvé (meta): {price} MAD")
                
                # Chercher ancien prix dans le HTML
                old_price_element = soup.select_one('.price del .woocommerce-Price-amount bdi')
                old_price = None
                if old_price_element:
                    old_price_text = old_price_element.get_text(strip=True)
                    old_price = extract_price(old_price_text)
                    if old_price and old_price > price:
                        print(f"✅ [DUGA] Ancien prix trouvé: {old_price} MAD")
                
                return price, old_price
        
        # Méthode 2: Prix WooCommerce standard dans ins (prix en promo)
        price_element = soup.select_one('.price ins .woocommerce-Price-amount bdi')
        if price_element:
            price_text = price_element.get_text(strip=True)
            price = extract_price(price_text)
            if price:
                print(f"✅ [DUGA] Prix trouvé (ins): {price} MAD")
                
                # Chercher ancien prix
                old_price_element = soup.select_one('.price del .woocommerce-Price-amount bdi')
                old_price = None
                if old_price_element:
                    old_price_text = old_price_element.get_text(strip=True)
                    old_price = extract_price(old_price_text)
                    if old_price and old_price > price:
                        print(f"✅ [DUGA] Ancien prix trouvé: {old_price} MAD")
                
                return price, old_price
        
        # Méthode 3: Prix simple (pas de promo)
        price_element = soup.select_one('.price .woocommerce-Price-amount bdi')
        if price_element:
            price_text = price_element.get_text(strip=True)
            price = extract_price(price_text)
            if price:
                print(f"✅ [DUGA] Prix trouvé (simple): {price} MAD")
                return price, None
        
        print("⚠️ [DUGA] Aucun prix trouvé")
        return None, None
    except Exception as e:
        print(f"❌ Erreur extraction prix Duga: {e}")
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
        
        # Appeler le scraper duga
        scraped_data = scraper_duga_detaille(reference)
        
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
    products = get_all_products_from_db("duga")

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
        scraped_data = scrap_product_for_site(reference, "duga")
        
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
    # scrap_product_for_site("90NB13Y2-M00V10", "duga")
    # if scraped_data:
    #     print(f"Données récupérées: {scraped_data}")
    
    # Lancer le scraping pour tous les produits pending
    main()