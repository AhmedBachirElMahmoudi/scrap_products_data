import requests
from bs4 import BeautifulSoup
import re
import time
import traceback
from utils import get_all_products_from_db, get_product_info_for_scraping, update_product_in_database
from utils_2 import clean_encoding, clean_html_content, strip_problematic_characters
import json

def scraper_rightech_detaille(reference):
    """Scrape les données détaillées pour une référence donnée sur rightech.ma"""
    try:
        url = f"https://rightech.ma/recherche?controller=search&s={reference}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        }
        
        print(f"🔍 Recherche du produit sur rightech.ma: {reference}")
        
        session = requests.Session()
        session.headers.update(headers)
        
        response = session.get(url, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        if detect_no_products_rightech(soup, reference):
            print(f"🚫 PRODUIT NON TROUVÉ sur rightech.ma: '{reference}'")
            return create_not_found_response(reference, 'not_found')
        
        product_link = find_product_link_rightech(soup, reference)
        
        if not product_link:
            print(f"❌ Aucun lien produit trouvé sur rightech.ma pour '{reference}'")
            return create_not_found_response(reference, 'link_not_found')
        
        product_url = product_link.get('href')
        product_url = normalize_url_rightech(product_url)
        
        print(f"✅ Produit trouvé sur rightech.ma, accès à: {product_url}")
        return scraper_rightech_product_details(product_url, reference)
        
    except requests.exceptions.Timeout:
        print(f"❌ Timeout lors de la recherche rightech.ma de {reference}")
        return create_not_found_response(reference, 'timeout')
    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur réseau lors du scraping rightech.ma de {reference}: {e}")
        return create_not_found_response(reference, 'network_error')
    except Exception as e:
        print(f"❌ Erreur inattendue lors du scraping rightech.ma de {reference}: {e}")
        return create_not_found_response(reference, 'error')

def scraper_rightech_product_details(product_url, expected_reference):
    """Scrape les détails complets depuis la page produit rightech.ma"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8'
        }
        
        print(f"🌐 Accès à la page produit détaillée rightech.ma...")
        response = requests.get(product_url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Vérifier la référence - VERSION FLEXIBLE
        reference_match = verify_rightech_reference(soup, expected_reference)
        if not reference_match:
            print(f"⚠️ Référence non exacte sur rightech.ma, mais produit trouvé - continuation")
        
        print(f"✅ Produit rightech.ma confirmé: {expected_reference}")
        
        # Extraire les données
        title = extract_rightech_title(soup)
        description = extract_rightech_description(soup)
        short_description = extract_rightech_short_description(soup)
        categories_data = extract_rightech_categories(soup)
        image_url = extract_rightech_image(soup)
        brand = extract_rightech_brand(soup)
        attributes = extract_rightech_attributes(soup) # NOUVEAU
        
        # DEBUG: Afficher des informations sur la description extraite
        if description:
            desc_text = BeautifulSoup(description, 'html.parser').get_text(strip=True)
            print(f"📄 Description extraite: {len(desc_text)} caractères")
            if len(desc_text) < 100:
                print(f"⚠️  Description peut-être incomplète")
        
        # Gérer les descriptions manquantes
        if not description and short_description:
            description = short_description
            print(f"🔄 Description manquante - Utilisation de la description courte")
        elif description and not short_description:
            soup_desc = BeautifulSoup(description, 'html.parser')
            text_content = soup_desc.get_text(strip=True)
            short_description = text_content[:200] + "..." if len(text_content) > 200 else text_content
            print(f"🔄 Description courte manquante - Création d'un extrait")
        
        # Assurer la cohérence des données comme dans update_product_in_database
        if not categories_data.get('subcategories') and categories_data.get('categories'):
            categories_data['subcategories'] = categories_data['categories']
            print(f"🔄 rightech: Catégories dupliquées en sous-catégories")
        
        return {
            'reference': expected_reference,
            'title': title,
            'description': description,
            'short_description': short_description,
            'categories': categories_data.get('categories'),
            'subcategories': categories_data.get('subcategories'),
            'image': image_url,  # Note: utiliser 'image' au lieu de 'image_url' pour la cohérence
            'brand': brand,
            'attributes': json.dumps(attributes, ensure_ascii=False) if attributes else None,
            'product_url': product_url,
            'status': 'success',
            'source': 'rightech'
        }
        
    except Exception as e:
        print(f"❌ Erreur lors du scraping des détails rightech.ma: {e}")
        return None

def detect_no_products_rightech(soup, reference):
    """Détection des pages 'produit non trouvé' sur rightech.ma"""
    # Vérifier les messages d'erreur
    error_indicators = [
        '.alert-warning',
        '.no-products',
        '.search-no-results'
    ]
    
    for selector in error_indicators:
        element = soup.select_one(selector)
        if element:
            element_text = element.get_text(strip=True).lower()
            if any(phrase in element_text for phrase in ['aucun', 'aucune', 'introuvable', 'no result']):
                print(f"🚫 Message d'erreur rightech.ma trouvé: {selector}")
                return True
    
    # Vérifier s'il y a des produits
    products = soup.select('.product-miniature, .product, .ajax_block_product')
    if not products:
        print("🚫 Aucun produit trouvé sur rightech.ma")
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

def find_product_link_rightech(soup, reference):
    """Recherche du lien produit sur rightech.ma"""
    standard_selectors = [
        'a.product_img_link',
        'a.product-name', 
        '.product-title a',
        '.product-miniature a',
        '.ajax_block_product a',
        '.product-container a'
    ]
    
    for selector in standard_selectors:
        links = soup.select(selector)
        for link in links:
            if is_likely_product_link_rightech(link, reference):
                print(f"✅ Lien produit rightech.ma trouvé avec: {selector}")
                return link
    
    # Fallback: recherche dans tous les liens
    all_links = soup.find_all('a', href=True)
    for link in all_links:
        if is_likely_product_link_rightech(link, reference):
            print(f"✅ Lien produit rightech.ma trouvé par recherche globale")
            return link
    
    return None

def is_likely_product_link_rightech(link, reference):
    """Détermine si un lien mène probablement à un produit sur rightech.ma"""
    href = link.get('href', '').lower()
    text = link.get_text(strip=True).lower()
    ref_lower = reference.lower()
    
    # Exclure les liens qui ne sont probablement pas des produits
    excluded_patterns = [
        '/recherche',
        '/contact',
        '/blog',
        '/actualites',
        'controller=search'
    ]
    
    for pattern in excluded_patterns:
        if pattern in href:
            return False
    
    # Critères positifs
    positive_indicators = [
        ref_lower in href,
        ref_lower in text,
        any(ref_lower in span.get_text(strip=True).lower() 
            for span in link.find_all(['span', 'div', 'h3', 'h4']))
    ]
    
    return any(positive_indicators)

def normalize_url_rightech(url):
    """Normalise l'URL du produit pour rightech.ma"""
    if not url:
        return None
        
    if url.startswith('//'):
        return 'https:' + url
    elif url.startswith('/'):
        return 'https://rightech.ma' + url
    elif not url.startswith('http'):
        return 'https://rightech.ma/' + url
    
    return url

def verify_rightech_reference(soup, expected_reference):
    """Vérifie la référence sur rightech.ma - VERSION FLEXIBLE"""
    try:
        expected_clean = re.sub(r'[^a-zA-Z0-9]', '', expected_reference).upper()
        
        reference_selectors = [
            '.product-reference',
            '.reference',
            '[itemprop="sku"]',
            '.product_info .reference'
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
        print(f"❌ Erreur vérification référence rightech: {e}")
        return False

def extract_rightech_title(soup):
    """Extrait le titre du produit sur rightech.ma"""
    try:
        title_selectors = [
            'h1.page-title',
            'h1.product-name',
            'h1',
            '.product-title'
        ]
        
        for selector in title_selectors:
            title_element = soup.select_one(selector)
            if title_element:
                title = title_element.get_text(strip=True)
                if title:
                    return strip_problematic_characters(clean_encoding(title))
        
        return None
    except Exception as e:
        print(f"❌ Erreur extraction titre rightech: {e}")
        return None

def extract_rightech_categories(soup):
    """Extrait les catégories sur rightech.ma"""
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
        print(f"❌ Erreur extraction catégories rightech: {e}")
        return {'categories': None, 'subcategories': None}

def extract_rightech_image(soup):
    """Extrait l'image sur rightech.ma"""
    try:
        image_selectors = [
            '.product-cover img',
            '#product-cover img',
            '[itemprop="image"]',
            'img.product-image'
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
                            src = 'https://rightech.ma' + src
                    return src
        
        return None
    except Exception as e:
        print(f"❌ Erreur extraction image rightech: {e}")
        return None

def extract_rightech_brand(soup):
    """Extrait la marque du produit sur rightech.ma"""
    try:
        # Sélecteurs pour la marque sur rightech.ma
        brand_selectors = [
            '.product-manufacturer img',
            '.manufacturer-logo',
            '.product-brand img',
            '[itemprop="brand"] img',
            '.label + a img'  # Pour le sélecteur spécifique avec label "Marque"
        ]
        
        for selector in brand_selectors:
            brand_element = soup.select_one(selector)
            if brand_element:
                # Extraire le nom de la marque depuis l'attribut alt
                brand_name = brand_element.get('alt', '').strip()
                if brand_name:
                    return strip_problematic_characters(clean_encoding(brand_name))
                
                # Fallback: chercher le texte "Marque" à proximité
                parent_manufacturer = brand_element.find_parent('div', class_='product-manufacturer')
                if parent_manufacturer:
                    # Chercher le label "Marque" et prendre le contenu suivant
                    label = parent_manufacturer.find(class_='label')
                    if label and 'marque' in label.get_text(strip=True).lower():
                        # Prendre le texte après le label
                        brand_text = parent_manufacturer.get_text(strip=True)
                        brand_text = brand_text.replace('Marque', '').strip()
                        if brand_text:
                            return strip_problematic_characters(clean_encoding(brand_text))
        
        # Fallback: chercher dans les liens de marque
        brand_link = soup.find('a', href=lambda x: x and '/marque/' in x) or \
                    soup.find('a', href=lambda x: x and '/brand/' in x)
        if brand_link:
            brand_name = brand_link.get_text(strip=True)
            if brand_name:
                return strip_problematic_characters(clean_encoding(brand_name))
        
    except Exception as e:
        print(f"❌ Erreur extraction marque rightech: {e}")
        return None

def extract_rightech_attributes(soup):
    """Extrait les attributs (fiche technique) sur rightech.ma"""
    try:
        attributes = {}
        print("🔍 [RIGHTECH] Recherche des attributs...")
        
        # Méthode 1: Table data-sheet (Prestashop classique)
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
                print(f"✅ [RIGHTECH] {len(attributes)} attributs trouvés via table-data-sheet")
                return attributes
        
        # Méthode 2: Section definition list (dl)
        dl_list = soup.find_all('dl', class_='data-sheet')
        for dl in dl_list:
            dt_list = dl.find_all('dt')
            dd_list = dl.find_all('dd')
            if len(dt_list) == len(dd_list):
                for dt, dd in zip(dt_list, dd_list):
                    key = dt.get_text(strip=True).rstrip(':')
                    value = dd.get_text(strip=True)
                    if key and value:
                        attributes[key] = value

        if attributes:
            print(f"✅ [RIGHTECH] {len(attributes)} attributs trouvés")
            return attributes

        print("⚠️ [RIGHTECH] Aucun attribut trouvé")
        return None
    except Exception as e:
        print(f"❌ Erreur extraction attributs rightech: {e}")
        return None

# ============================================================================
# FONCTIONS POUR LE FILTRAGE DES DESCRIPTIONS RIGHTECH
# ============================================================================

def is_valid_description(content):
    """Vérifie si le contenu est une vraie description et non un formulaire"""
    if not content:
        return False
    
    # Liste de textes indésirables
    unwanted_phrases = [
        'Donner votre avis',
        'Donnez votre avis',
        'Votre note pour ce produit',
        'Titre:',
        'Commentaire:',
        'Votre nom:',
        'Champs requis',
        'Envoyer',
        'Annuler',
        'Cancel Rating',
        'Path:',
        'Return to Home',
        'Avis',
        'Donner votre avis !'
    ]
    
    content_lower = content.lower()
    
    # Si le contenu contient des phrases indésirables, c'est probablement un formulaire
    for phrase in unwanted_phrases:
        if phrase.lower() in content_lower:
            return False
    
    # Vérifier la longueur minimale
    if len(content.strip()) < 20:
        return False
    
    return True

def filter_rightech_description_content(desc_element):
    """Filtre le contenu de la description pour enlever les éléments non pertinents"""
    try:
        # Faire une copie pour ne pas modifier l'original
        filtered_element = BeautifulSoup(str(desc_element), 'html.parser')
        
        # Supprimer les sections non pertinentes
        sections_to_remove = [
            '#idTab5',  # Section avis
            '#new_comment_form',  # Formulaire d'avis
            '.idTabHrefShort',  # Titre "Avis"
            '.open-comment-form',  # Bouton "Donner votre avis"
            '.page-subheading',  # Titres de formulaire
            '#product_comments_block_tab',  # Bloc commentaires
            '.navigation-pipe',  # Breadcrumb
            '.tab-pane',  # Onglets
            '.product-comments',  # Commentaires
            '.ps_add_comment_tab',  # Ajout de commentaire
            '#title-new-comment',  # Titre nouveau commentaire
            '#new_comment_form_footer',  # Pied de formulaire
            '#criterions_list',  # Liste de critères
            '.cancel',  # Annulation notation
            '.star_content',  # Étoiles de notation
            '.product-comments-additional-info',  # Info supplémentaires commentaires
            '.breadcrumb',  # Fil d'Ariane
            '.navigation',  # Navigation
            'form',  # Tous les formulaires
            '.form-group',  # Groupes de formulaire
            '.required',  # Champs requis
            '.button',  # Boutons
            '.btn'  # Boutons
        ]
        
        for selector in sections_to_remove:
            elements = filtered_element.select(selector)
            for element in elements:
                element.decompose()
        
        # Supprimer les éléments avec du texte spécifique
        unwanted_texts = [
            'Donner votre avis',
            'Donnez votre avis', 
            'Votre note pour ce produit',
            'Titre:',
            'Commentaire:',
            'Votre nom:',
            'Champs requis',
            'Envoyer',
            'Annuler',
            'Cancel Rating',
            'Avis',
            'Path:',
            'Return to Home',
            'Donner votre avis !'
        ]
        
        # Supprimer les éléments contenant ces textes
        for text in unwanted_texts:
            elements = filtered_element.find_all(string=lambda s: text in s if s else False)
            for element in elements:
                parent = element.parent
                if parent:
                    parent.decompose()
        
        # Supprimer les formulaires restants
        forms = filtered_element.find_all('form')
        for form in forms:
            form.decompose()
        
        # Supprimer les input et textarea
        inputs = filtered_element.find_all(['input', 'textarea', 'select'])
        for input_elem in inputs:
            input_elem.decompose()
        
        # Vérifier si le contenu filtré est valide
        text_content = filtered_element.get_text(strip=True)
        if len(text_content) < 50:  # Trop court, probablement pas une vraie description
            return None
        
        return filtered_element
        
    except Exception as e:
        print(f"⚠️ Erreur filtrage description rightech: {e}")
        return desc_element  # Retourner l'original en cas d'erreur

def extract_rightech_description(soup):
    """Extrait la description sur rightech.ma - VERSION AMÉLIORÉE"""
    try:
        # D'abord essayer de trouver la vraie description produit
        description_selectors = [
            '.product-description',  # Le sélecteur principal
            '#description .rte',
            '[itemprop="description"]',
            '.product-details',
            '.tab-content .active',
            '#description'
        ]
        
        for selector in description_selectors:
            desc_element = soup.select_one(selector)
            if desc_element:
                print(f"✅ Élément description trouvé avec: {selector}")
                # Filtrer le contenu pour enlever les éléments non pertinents
                cleaned_content = filter_rightech_description_content(desc_element)
                if cleaned_content:
                    html_content = str(cleaned_content)
                    cleaned_html = strip_problematic_characters(clean_html_content(html_content))
                    
                    # Vérifier que c'est une vraie description
                    text_content = BeautifulSoup(cleaned_html, 'html.parser').get_text(strip=True)
                    if is_valid_description(text_content):
                        print(f"✅ Description valide extraite: {len(text_content)} caractères")
                        return cleaned_html
                    else:
                        print(f"⚠️  Description filtrée non valide, tentative suivante...")
        
        # Si aucune vraie description trouvée, essayer d'autres sections
        return extract_rightech_description_fallback(soup)
        
    except Exception as e:
        print(f"❌ Erreur extraction description rightech: {e}")
        return None

def extract_rightech_description_fallback(soup):
    """Méthode de secours pour extraire la description sur rightech.ma"""
    try:
        print("🔄 Utilisation de la méthode de secours pour la description...")
        
        # Essayer d'autres sélecteurs possibles
        fallback_selectors = [
            '.tab-content',
            '.product-features',
            '.data-sheet',
            '.product-info',
            '.rte',
            '.product-description-short'
        ]
        
        for selector in fallback_selectors:
            element = soup.select_one(selector)
            if element:
                print(f"✅ Élément fallback trouvé avec: {selector}")
                # Appliquer le même filtrage
                filtered_content = filter_rightech_description_content(element)
                if filtered_content:
                    html_content = str(filtered_content)
                    cleaned_html = strip_problematic_characters(clean_html_content(html_content))
                    
                    # Vérifier que c'est une vraie description
                    text_content = BeautifulSoup(cleaned_html, 'html.parser').get_text(strip=True)
                    if is_valid_description(text_content):
                        print(f"✅ Description fallback valide: {len(text_content)} caractères")
                        return cleaned_html
        
        print("❌ Aucune description valide trouvée avec les méthodes de secours")
        return None
        
    except Exception as e:
        print(f"❌ Erreur extraction fallback rightech: {e}")
        return None

def extract_rightech_short_description(soup):
    """Extrait la description courte sur rightech.ma - VERSION AMÉLIORÉE"""
    try:
        short_desc_selectors = [
            '.product-description-short',
            '.short-description',
            '#product-description-short',
            '[itemprop="description"]',
            '.product-features'
        ]
        
        for selector in short_desc_selectors:
            short_desc_element = soup.select_one(selector)
            if short_desc_element:
                html_content = str(short_desc_element)
                cleaned_content = strip_problematic_characters(clean_html_content(html_content))
                
                # Vérifier que ce n'est pas un formulaire ou autre élément non pertinent
                text_content = BeautifulSoup(cleaned_content, 'html.parser').get_text(strip=True)
                if is_valid_description(text_content):
                    print(f"✅ Description courte valide trouvée: {len(text_content)} caractères")
                    return cleaned_content
        
        # Si pas de description courte, créer un extrait de la description longue
        description = extract_rightech_description(soup)
        if description:
            soup_desc = BeautifulSoup(description, 'html.parser')
            text_content = soup_desc.get_text(strip=True)
            if len(text_content) > 200:
                short_desc = text_content[:200] + "..."
                print(f"🔄 Description courte créée depuis description longue: {len(short_desc)} caractères")
                return short_desc
            else:
                print(f"🔄 Description courte = description longue: {len(text_content)} caractères")
                return text_content
        
        print("❌ Aucune description courte trouvée")
        return None
    except Exception as e:
        print(f"❌ Erreur extraction description courte rightech: {e}")
        return None

# ============================================================================
# FONCTION PRINCIPALE POUR RIGHTECH.MA
# ============================================================================

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
        
        # Appeler le scraper rightech
        scraped_data = scraper_rightech_detaille(reference)
        
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
            print(f"🚫 Produit non trouvé sur rightech.ma pour {reference}")
            update_product_in_database(product_id, None, site_name, scraping_success=False)
            return None
            
    except Exception as e:
        print(f"❌ Erreur lors du scraping de {reference} sur {site_name}: {e}")
        return None

def main():
    """Fonction principale"""
    products = get_all_products_from_db("rightech")

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
        scraped_data = scrap_product_for_site(reference, "rightech")
        
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
    print("📊 RÉCAPITULATIF DU SCRAPING RIGHTECH.MA")
    print(f"{'='*60}")
    print(f"✅ Produits trouvés et mis à jour: {success_count}")
    print(f"🚫 Produits non trouvés sur le site: {not_found_count}")
    print(f"❌ Erreurs de scraping: {error_count}")
    print(f"📈 Total traité: {len(products)}")
    print(f"{'='*60}")

if __name__ == "__main__":
    # Test avec un produit spécifique
    # scrap_product_for_site("VOTRE_REFERENCE", "rightech")
    
    # Lancer le scraping pour tous les produits pending
    main()