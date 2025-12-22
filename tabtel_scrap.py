import requests
import urllib.parse
import re
from bs4 import BeautifulSoup
import json
from utils import clean_text, clean_brand_name, clean_site_names_from_title,ensure_data_consistency, normalize_image_url , get_all_products_from_db , get_product_info_for_scraping , update_product_in_database
import time

def scraper_tabtel_detaille(reference):
    """Scrape les données détaillées depuis Tabtel.ma - VERSION AVEC ENCODAGE URL"""
    try:
        # 🔥 CORRECTION : Encoder la référence
        encoded_reference = urllib.parse.quote(reference)
        url = f"https://tabtel.ma/fr/recherche?controller=search&orderby=position&orderway=desc&search_query={encoded_reference}&submit_search="
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        }
        
        print(f"🔍 [TABTEL] Recherche du produit: {reference}")
        print(f"🔤 Référence encodée: {encoded_reference}")
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 🔥 VÉRIFICATION CRITIQUE : Vérifier d'abord s'il y a des résultats
        no_results_alert = soup.find('p', class_='alert alert-warning')
        no_results_counter = soup.find('small', class_='heading-counter')
        
        if no_results_alert and "Aucun résultat trouvé" in no_results_alert.get_text():
            print(f"❌ [TABTEL] AUCUN RÉSULTAT TROUVÉ pour '{reference}'")
            return None
        
        if no_results_counter and "0 résultats" in no_results_counter.get_text():
            print(f"❌ [TABTEL] 0 RÉSULTAT TROUVÉ pour '{reference}'")
            return None
        
        # VÉRIFICATION : S'assurer qu'on est bien sur une page de résultats, pas une page générique
        page_heading = soup.find('h1', class_='page-heading product-listing')
        if not page_heading or "Rechercher" not in page_heading.get_text():
            print(f"❌ [TABTEL] Page de recherche non détectée")
            return None
        
        # 🔥 CORRECTION : Ne chercher les produits QUE dans la section center_column (résultats réels)
        center_column = soup.find('section', id='center_column')
        if not center_column:
            print(f"❌ [TABTEL] Section des résultats non trouvée")
            return None
        
        # TROUVER LES PRODUITS UNIQUEMENT dans les résultats de recherche (center_column)
        products = []
        
        # Méthode 1: Chercher dans center_column seulement
        products = center_column.find_all('div', class_='ajax_block_product')
        print(f"✅ [TABTEL] Trouvé {len(products)} produits dans les résultats de recherche")
        
        # Méthode 2: Si pas trouvé, chercher par product-container dans center_column
        if not products:
            products = center_column.find_all('div', class_='product-container')
            print(f"✅ [TABTEL] Trouvé {len(products)} produits avec classe 'product-container'")
        
        # Méthode 3: Chercher par product_img_link dans center_column seulement
        if not products:
            product_links = center_column.find_all('a', class_='product_img_link')
            products = [link.find_parent('div', class_='product-container') for link in product_links if link.find_parent('div', class_='product-container')]
            print(f"✅ [TABTEL] Trouvé {len(products)} produits via product_img_link")
        
        # 🔥 VÉRIFICATION FINALE : Si aucun produit dans center_column, c'est qu'il n'y a vraiment pas de résultats
        if not products:
            print(f"❌ [TABTEL] Aucun produit trouvé dans les résultats de recherche pour {reference}")
            return None
        
        print(f"📦 [TABTEL] {len(products)} produits trouvés dans les résultats de recherche")
        
        # Chercher le produit avec la référence EXACTE
        exact_match_url = None
        
        for i, product in enumerate(products, 1):
            # Trouver le lien du produit
            product_link = product.find('a', class_='product_img_link')
            if not product_link:
                product_link = product.find('a', class_='product-name')
            
            if not product_link or not product_link.get('href'):
                print(f"  ⚠️  [TABTEL] Aucun lien trouvé pour le produit {i}")
                continue
                
            product_url = product_link.get('href')
            
            # S'assurer que l'URL est complète
            if product_url and not product_url.startswith('http'):
                if product_url.startswith('//'):
                    product_url = 'https:' + product_url
                elif product_url.startswith('/'):
                    product_url = 'https://tabtel.ma' + product_url
            
            # Accéder à chaque page produit pour vérifier la référence
            try:
                print(f"  🔎 [TABTEL] Vérification du produit {i}/{len(products)}: {product_url}")
                product_response = requests.get(product_url, headers=headers, timeout=10)
                product_response.raise_for_status()
                product_soup = BeautifulSoup(product_response.content, 'html.parser')
                
                # VÉRIFICATION STRICTE DE LA RÉFÉRENCE
                found_reference = verify_reference_tabtel(product_soup, reference)
                
                if found_reference and found_reference.upper() == reference.upper():
                    print(f"  ✅ [TABTEL] RÉFÉRENCE EXACTE TROUVÉE: {reference}")
                    exact_match_url = product_url
                    break
                else:
                    if found_reference:
                        print(f"  ❌ [TABTEL] Référence différente: '{found_reference}' (attendu: '{reference}')")
                    else:
                        print(f"  ⚠️  [TABTEL] Référence non trouvée sur la page")
                    
            except Exception as e:
                print(f"  ⚠️  [TABTEL] Erreur vérification produit {i}: {e}")
                continue
        
        if not exact_match_url:
            print(f"❌ [TABTEL] Aucun produit avec la référence exacte '{reference}' trouvé")
            return None
        
        print(f"🌐 [TABTEL] Accès à la page produit exacte: {exact_match_url}")
        
        # Maintenant scraper la page détaillée du produit
        return scraper_tabtel_product_details(exact_match_url, reference)
        
    except Exception as e:
        print(f"❌ [TABTEL] Erreur lors du scraping de {reference}: {e}")
        return None

def scraper_tabtel_product_details(product_url, expected_reference):
    """Scrape les détails complets depuis la page produit Tabtel - VERSION AVEC MARQUE"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
            'Referer': 'https://tabtel.ma/'
        }
        
        print(f"🌐 [TABTEL] Accès à la page produit détaillée...")
        response = requests.get(product_url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # VÉRIFICATION STRICTE DE LA RÉFÉRENCE
        reference_match = verify_reference_tabtel(soup, expected_reference)
        if not reference_match or reference_match.upper() != expected_reference.upper():
            print(f"❌ [TABTEL] RÉFÉRENCE MISMATCH: Attendu '{expected_reference}' mais trouvé '{reference_match}'")
            return None
        
        print(f"✅ [TABTEL] Référence vérifiée: {expected_reference}")
        
        # Extraire les données (AVEC MARQUE)
        title = extract_title_tabtel(soup)
        description = extract_description_tabtel(soup)
        short_description = extract_short_description_tabtel(soup)
        attributes = extract_attributes_tabtel(soup)
        categories_data = extract_categories_tabtel(soup)
        image_url = extract_main_image_tabtel(soup)
        brand = extract_brand_tabtel(soup)  # NOUVEAU
        
        # 🔥 CORRECTION: Appliquer la cohérence immédiatement
        if categories_data.get('categories') and not categories_data.get('subcategories'):
            categories_data['subcategories'] = categories_data['categories']
        
        if not description and short_description:
            description = short_description
        
        data = {
            'source': 'tabtel',
            'reference': expected_reference,
            'title': title,
            'description': description,
            'short_description': short_description,
            'attributes': json.dumps(attributes, ensure_ascii=False) if attributes else None,
            'categories': categories_data.get('categories'),
            'subcategories': categories_data.get('subcategories'),
            'product_url': product_url,
            'image': image_url,
            'brand': brand  # NOUVEAU
        }
        
        return ensure_data_consistency(data)
        
    except Exception as e:
        print(f"❌ [TABTEL] Erreur lors du scraping des détails: {e}")
        return None

def verify_reference_tabtel(soup, expected_reference):
    """Vérifie la référence directement depuis la page produit Tabtel"""
    try:
        # 1️⃣ Méthode directe : itemprop="sku"
        sku_span = soup.find('span', itemprop='sku')
        if sku_span:
            found_reference = sku_span.get_text(strip=True)
            print(f"  📍 [TABTEL] Référence trouvée dans itemprop=sku: {found_reference}")
            return found_reference

        # 2️⃣ Méthode de secours : extraire depuis le titre <h1>
        title_element = soup.find('h1', itemprop='name')
        if title_element:
            title_text = title_element.get_text(strip=True)
            ref_match = re.search(r'\(([A-Z0-9-]+)\)', title_text)
            if ref_match:
                found_reference = ref_match.group(1)
                print(f"  📍 [TABTEL] Référence trouvée dans le titre: {found_reference}")
                return found_reference

        # 3️⃣ Méthode supplémentaire : attributs data-* (au cas où)
        product_container = soup.find('div', {'data-product-reference': True})
        if product_container:
            found_reference = product_container['data-product-reference'].strip()
            print(f"  📍 [TABTEL] Référence trouvée dans data-product-reference: {found_reference}")
            return found_reference

        print(f"  ❌ [TABTEL] Référence '{expected_reference}' non trouvée sur la page")
        return None

    except Exception as e:
        print(f"  ❌ Erreur vérification référence Tabtel: {e}")
        return None

def extract_title_tabtel(soup):
    """Extrait le titre du produit Tabtel - VERSION CORRIGÉE"""
    try:
        # Méthode 1: h1 avec itemprop="name"
        title_element = soup.find('h1', itemprop='name')
        if title_element:
            title = title_element.get_text(strip=True)
            title = re.sub(r'\s*\([^)]*\)\s*$', '', title)
            return clean_site_names_from_title(title)

        # Méthode 2: h1 avec classe page-title ou product-title
        title_element = soup.find('h1', class_=['page-title', 'product-title', 'h1'])
        if title_element:
            title = title_element.get_text(strip=True)
            title = re.sub(r'\s*\([^)]*\)\s*$', '', title)
            return clean_site_names_from_title(title)
            
        # Méthode 3: Premier h1 dans la section principale
        main_section = soup.find('section', id='main') or soup.find('div', id='content')
        if main_section:
            title_element = main_section.find('h1')
            if title_element:
                title = title_element.get_text(strip=True)
                title = re.sub(r'\s*\([^)]*\)\s*$', '', title)
                return clean_site_names_from_title(title)
        
        # Méthode 4: Fallback - chercher dans le meta title
        meta_title = soup.find('meta', property='og:title')
        if meta_title and meta_title.get('content'):
            title = meta_title.get('content').strip()
            return clean_site_names_from_title(title)
        
        print("❌ [TABTEL] Aucun titre trouvé")
        return None
    except Exception as e:
        print(f"❌ Erreur extraction titre Tabtel: {e}")
        return None

def extract_description_tabtel(soup):
    """Extrait la description complète depuis Tabtel - VERSION CORRIGÉE"""
    try:
        # Méthode 1: Chercher le tableau des caractéristiques
        description_table = soup.find('table', class_='table table-bordered table-striped')
        if description_table:
            print("✅ [TABTEL] Tableau des caractéristiques trouvé")
            
            # Convertir le tableau en HTML propre
            for element in description_table(['script', 'style']):
                element.decompose()
            
            # Ajouter un titre au tableau
            table_html = f"<h3>Caractéristiques du produit</h3>{str(description_table)}"
            return table_html
        
        # Méthode 2: Chercher dans la section description
        description_section = soup.find('section', class_='product-description')
        if description_section:
            print("✅ [TABTEL] Section description trouvée")
            # Nettoyer le HTML
            for element in description_section(['script', 'style', 'nav', 'header', 'footer']):
                element.decompose()
            return str(description_section)
        
        # Méthode 3: Chercher dans les onglets
        tabs_content = soup.find('div', class_='product-tabs-content')
        if tabs_content:
            print("✅ [TABTEL] Contenu des onglets trouvé")
            return str(tabs_content)
        
        print("❌ [TABTEL] Aucune description trouvée")
        return None
        
    except Exception as e:
        print(f"❌ Erreur extraction description Tabtel: {e}")
        return None

def extract_short_description_tabtel(soup):
    """Extrait la description courte depuis Tabtel - VERSION AMÉLIORÉE"""
    try:
        # Méthode 1: Extraire les caractéristiques principales du tableau
        description_table = soup.find('table', class_='table table-bordered table-striped')
        if description_table:
            short_desc_lines = []
            rows = description_table.find_all('tr')[:4]  # Prendre les 4 premières lignes
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    key = cells[0].get_text(strip=True)
                    value = cells[1].get_text(strip=True)
                    if key and value and key not in ['', 'Nom du produit']:
                        short_desc_lines.append(f"{key}: {value}")
            
            if short_desc_lines:
                short_desc = ' | '.join(short_desc_lines)
                print("✅ [TABTEL] Description courte générée depuis le tableau")
                return short_desc
        
        # Méthode 2: Chercher la div product-desc
        product_desc = soup.find('div', class_='product-desc')
        if product_desc:
            desc_text = product_desc.get_text(strip=True)
            if desc_text and len(desc_text) > 10:
                print("✅ [TABTEL] Description courte trouvée dans product-desc")
                return desc_text
        
        # Méthode 3: Meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            desc = meta_desc.get('content').strip()
            if 20 < len(desc) < 500:
                print("✅ [TABTEL] Description courte trouvée dans meta description")
                return desc
        
        print("❌ [TABTEL] Aucune description courte trouvée")
        return None
        
    except Exception as e:
        print(f"❌ Erreur extraction description courte Tabtel: {e}")
        return None

def extract_attributes_tabtel(soup):
    """Extrait les caractéristiques techniques depuis Tabtel - VERSION AMÉLIORÉE"""
    try:
        attributes = {}
        
        # Méthode 1: Extraire du tableau des caractéristiques
        description_table = soup.find('table', class_='table table-bordered table-striped')
        if description_table:
            print("✅ [TABTEL] Extraction des attributs depuis le tableau")
            rows = description_table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    key = cells[0].get_text(strip=True)
                    value = cells[1].get_text(strip=True)
                    if key and value and key not in ['', 'Nom du produit']:
                        attributes[key] = value
        
        # Méthode 2: Chercher dans la section caractéristiques
        if not attributes:
            features_section = soup.find('section', class_='product-features')
            if features_section:
                feature_elements = features_section.find_all('li')
                for feature in feature_elements:
                    text = feature.get_text(strip=True)
                    if ':' in text:
                        key, value = text.split(':', 1)
                        attributes[key.strip()] = value.strip()
        
        # Méthode 3: Chercher dans le tableau des caractéristiques standard
        if not attributes:
            data_sheet = soup.find('table', class_='data-sheet')
            if data_sheet:
                rows = data_sheet.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        key = cells[0].get_text(strip=True)
                        value = cells[1].get_text(strip=True)
                        if key and value:
                            attributes[key] = value
        
        if attributes:
            print(f"✅ [TABTEL] {len(attributes)} attributs extraits: {list(attributes.keys())}")
        else:
            print("❌ [TABTEL] Aucun attribut trouvé")
            
        return attributes if attributes else None
        
    except Exception as e:
        print(f"❌ Erreur extraction attributs Tabtel: {e}")
        return None

def extract_categories_tabtel(soup):
    """Extrait les catégories depuis Tabtel - VERSION CORRIGÉE"""
    try:
        # Méthode 1: Chercher dans le breadcrumb avec itemprop="itemListElement"
        breadcrumb_items = soup.find_all('span', itemprop='itemListElement')
        
        categories = []
        for item in breadcrumb_items:
            link = item.find('a')
            if link:
                category = link.get_text(strip=True)
                if category and category.lower() not in ['accueil', 'home', '']:
                    categories.append(category)
        
        # Méthode 2: Chercher dans navigation_page
        if not categories:
            navigation_page = soup.find('span', class_='navigation_page')
            if navigation_page:
                links = navigation_page.find_all('a')
                for link in links:
                    category = link.get_text(strip=True)
                    if category and category.lower() not in ['accueil', 'home', '']:
                        categories.append(category)
        
        print(f"📊 [TABTEL] Catégories trouvées: {categories}")
        
        if len(categories) >= 2:
            return {
                'categories': categories[0],  # Première catégorie (Imprimante et Scanner)
                'subcategories': categories[1] if len(categories) > 1 else categories[0]  # Deuxième catégorie (Toner)
            }
        elif len(categories) == 1:
            return {
                'categories': categories[0],
                'subcategories': categories[0]
            }
        else:
            return {'categories': None, 'subcategories': None}
        
    except Exception as e:
        print(f"❌ Erreur extraction catégories Tabtel: {e}")
        return {'categories': None, 'subcategories': None}

def extract_main_image_tabtel(soup):
    """Extrait l'URL de l'image principale depuis Tabtel - VERSION ULTRA-CORRIGÉE"""
    try:
        print("🔍 [TABTEL] Recherche de l'image principale...")
        
        # MÉTHODE 1: Chercher l'image UNIQUEMENT dans la section produit (pb-left-column)
        product_image_section = soup.find('div', class_='pb-left-column')
        if product_image_section:
            print("✅ [TABTEL] Section pb-left-column trouvée")
            
            # Chercher l'image avec itemprop="image" UNIQUEMENT dans cette section
            main_image = product_image_section.find('img', itemprop='image')
            if main_image:
                src = main_image.get('src')
                if src:
                    full_url = normalize_image_url(src, 'https://tabtel.ma')
                    print(f"✅ [TABTEL] Image principale trouvée: {full_url}")
                    return full_url
            
            # Si pas d'itemprop, chercher l'image large_default dans cette section
            all_images = product_image_section.find_all('img')
            for img in all_images:
                src = img.get('src', '')
                if 'large_default' in src or 'thickbox' in src:
                    full_url = normalize_image_url(src, 'https://tabtel.ma')
                    print(f"✅ [TABTEL] Image large_default trouvée: {full_url}")
                    return full_url
        
        # MÉTHODE 2: Chercher dans la section image-block spécifique
        image_block = soup.find('div', id='image-block')
        if image_block:
            print("✅ [TABTEL] Section image-block trouvée")
            main_image = image_block.find('img', itemprop='image')
            if main_image:
                src = main_image.get('src')
                if src:
                    full_url = normalize_image_url(src, 'https://tabtel.ma')
                    print(f"✅ [TABTEL] Image trouvée dans image-block: {full_url}")
                    return full_url
        
        # MÉTHODE 3: Chercher dans views-block (galerie produit)
        views_block = soup.find('ul', id='views-block')
        if views_block:
            print("✅ [TABTEL] Galerie views-block trouvée")
            first_view = views_block.find('li')
            if first_view:
                img = first_view.find('img')
                if img:
                    src = img.get('src')
                    if src:
                        full_url = normalize_image_url(src, 'https://tabtel.ma')
                        print(f"✅ [TABTEL] Image trouvée dans views-block: {full_url}")
                        return full_url
        
        # MÉTHODE 4: Chercher toutes les images large_default HORS navbar
        # Exclure explicitement les sections qui ne sont pas le produit
        excluded_sections = soup.find_all(['nav', 'header', 'footer', 'aside'])
        excluded_ids = ['nav', 'header', 'footer', 'top', 'menu']
        
        all_images = soup.find_all('img')
        for img in all_images:
            # Vérifier que l'image n'est pas dans une section exclue
            is_excluded = False
            for excluded in excluded_sections:
                if img in excluded.descendants:
                    is_excluded = True
                    break
            
            # Vérifier que l'image n'est pas dans un div avec id exclu
            parent_with_id = img.find_parent(id=True)
            if parent_with_id and any(excluded_id in parent_with_id.get('id', '').lower() for excluded_id in excluded_ids):
                is_excluded = True
            
            if is_excluded:
                continue
            
            src = img.get('src', '')
            # Chercher les images de produit typiques (large, thickbox, etc.)
            if any(keyword in src for keyword in ['large_default', 'thickbox', 'home_default']) and '/img/p/' in src:
                full_url = normalize_image_url(src, 'https://tabtel.ma')
                print(f"✅ [TABTEL] Image produit trouvée (hors navbar): {full_url}")
                return full_url
        
        # MÉTHODE 5: Meta og:image comme dernier recours
        meta_image = soup.find('meta', property='og:image')
        if meta_image and meta_image.get('content'):
            full_url = meta_image.get('content')
            # Vérifier que ce n'est pas le logo du site
            if 'logo' not in full_url.lower():
                print(f"✅ [TABTEL] Image meta og:image trouvée: {full_url}")
                return full_url
        
        print("❌ [TABTEL] Aucune image produit valide trouvée")
        return None
        
    except Exception as e:
        print(f"❌ Erreur extraction image Tabtel: {e}")
        import traceback
        traceback.print_exc()
        return None
 
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
        
        # Appeler le scraper tabtel
        scraped_data = scraper_tabtel_detaille(reference)
        
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
    products = get_all_products_from_db("tabtel")

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
        scraped_data = scrap_product_for_site(reference, "tabtel")
        
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
    # scrap_product_for_site("90NB13Y2-M00V10", "tabtel")
    # if scraped_data:
    #     print(f"Données récupérées: {scraped_data}")
    
    # Lancer le scraping pour tous les produits pending
    main()