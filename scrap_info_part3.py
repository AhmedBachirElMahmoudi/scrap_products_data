import requests
from bs4 import BeautifulSoup
from database import connect_temp_srv
import time
import re
import sys
import traceback
import html

def clean_encoding(text):
    """Nettoie l'encodage des chaînes de caractères pour MySQL - VERSION ROBUSTE"""
    if text is None:
        return None
    
    try:
        # Si c'est des bytes, décoder
        if isinstance(text, bytes):
            text = text.decode('utf-8', errors='replace')
        
        # Nettoyer les entités HTML
        text = html.unescape(text)
        
        # Supprimer les caractères problématiques plus agressivement
        # Garder seulement les caractères ASCII étendus et certains caractères spéciaux
        text = re.sub(r'[^\x00-\x7F\u00A0-\u00FF\u0100-\u017F\u0180-\u024F]', '', text)
        
        # Supprimer les caractères de contrôle
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
        
        # Normaliser les espaces
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    except Exception as e:
        print(f"⚠️ Erreur lors du nettoyage de l'encodage: {e}")
        # Dernier recours: garder seulement les caractères ASCII
        return re.sub(r'[^\x00-\x7F]', '', str(text))

def clean_html_content(html_content):
    """Nettoie spécifiquement le contenu HTML pour MySQL - VERSION ROBUSTE"""
    if html_content is None:
        return None
    
    try:
        # Parser le HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Nettoyer chaque élément de texte avec une méthode plus robuste
        for element in soup.find_all(string=True):
            cleaned_text = clean_encoding(element)
            element.replace_with(cleaned_text)
        
        # Retourner le HTML nettoyé
        cleaned_html = str(soup)
        
        # Nettoyer à nouveau l'HTML entier
        cleaned_html = clean_encoding(cleaned_html)
        
        return cleaned_html
    except Exception as e:
        print(f"⚠️ Erreur lors du nettoyage HTML: {e}")
        # Fallback: nettoyer le HTML brut
        return clean_encoding(html_content)

def strip_problematic_characters(text):
    """Supprime agressivement les caractères problématiques - SOLUTION FINALE"""
    if text is None:
        return None
    
    # Liste des caractères problématiques spécifiques
    problematic_chars = [
        '\u1D49',  # Le caractère problématique \xE1\xB5\x89
        '\u0000', '\u0001', '\u0002', '\u0003', '\u0004', '\u0005', '\u0006', '\u0007',
        '\u0008', '\u000B', '\u000C', '\u000E', '\u000F', '\u0010', '\u0011', '\u0012',
        '\u0013', '\u0014', '\u0015', '\u0016', '\u0017', '\u0018', '\u0019', '\u001A',
        '\u001B', '\u001C', '\u001D', '\u001E', '\u001F', '\u007F'
    ]
    
    for char in problematic_chars:
        text = text.replace(char, '')
    
    # Supprimer les autres caractères non-ASCII problématiques
    text = re.sub(r'[^\x09\x0A\x0D\x20-\x7E\u00A0-\u00FF]', '', text)
    
    return text

def calculate_data_score(data):
    """Calcule un score de complétude des données (0-100) - AVEC MARQUE"""
    if not data or data.get('status') != 'success':
        return 0
    
    score = 0
    fields = {
        'title': 20,
        'description': 25,
        'short_description': 15,
        'categories': 15,
        'subcategories': 10,
        'brand': 10,  # NOUVEAU: points pour la marque
        'image_url': 15
    }
    
    for field, points in fields.items():
        if data.get(field):
            score += points
    
    return score

def analyze_missing_fields(data):
    """Analyse quels champs sont manquants dans les données"""
    if not data or data.get('status') != 'success':
        return []
    
    missing_fields = []
    required_fields = ['title', 'description', 'short_description', 'categories', 'subcategories', 'brand', 'image_url']
    
    for field in required_fields:
        if not data.get(field):
            missing_fields.append(field)
    
    return missing_fields

def merge_product_data(primary_data, secondary_data):
    """Fusionne les données de deux sources en gardant les meilleures informations - VERSION AVEC MARQUE"""
    if not primary_data or primary_data.get('status') != 'success':
        return secondary_data
    
    if not secondary_data or secondary_data.get('status') != 'success':
        return primary_data
    
    merged_data = primary_data.copy()
    improvements = []
    
    # Remplir les champs manquants avec les données secondaires
    if not merged_data.get('title') and secondary_data.get('title'):
        merged_data['title'] = secondary_data['title']
        improvements.append('title')
    
    if not merged_data.get('description') and secondary_data.get('description'):
        merged_data['description'] = secondary_data['description']
        improvements.append('description')
    elif merged_data.get('description') and secondary_data.get('description'):
        # Si les deux ont une description, garder la plus longue
        if len(secondary_data['description']) > len(merged_data['description']):
            merged_data['description'] = secondary_data['description']
            improvements.append('description (améliorée)')
    
    if not merged_data.get('short_description') and secondary_data.get('short_description'):
        merged_data['short_description'] = secondary_data['short_description']
        improvements.append('short_description')
    elif merged_data.get('short_description') and secondary_data.get('short_description'):
        # Si les deux ont une description courte, garder la plus longue
        if len(secondary_data['short_description']) > len(merged_data['short_description']):
            merged_data['short_description'] = secondary_data['short_description']
            improvements.append('short_description (améliorée)')
    
    if not merged_data.get('categories') and secondary_data.get('categories'):
        merged_data['categories'] = secondary_data['categories']
        improvements.append('categories')
    
    if not merged_data.get('subcategories') and secondary_data.get('subcategories'):
        merged_data['subcategories'] = secondary_data['subcategories']
        improvements.append('subcategories')
    
    if not merged_data.get('brand') and secondary_data.get('brand'):
        merged_data['brand'] = secondary_data['brand']
        improvements.append('brand')
    
    if not merged_data.get('image_url') and secondary_data.get('image_url'):
        merged_data['image_url'] = secondary_data['image_url']
        improvements.append('image_url')
    
    # Mettre à jour le score
    merged_data['score'] = calculate_data_score(merged_data)
    merged_data['sources_used'] = list(set(['mies', 'rightech']))
    
    if improvements:
        print(f"   ✅ Améliorations apportées: {', '.join(improvements)}")
    
    return merged_data

def debug_product_data(data, source):
    """Affiche le debug des données d'un produit - VERSION AVEC MARQUE"""
    if not data or data.get('status') != 'success':
        print(f"❌ {source}: Données non disponibles")
        return
    
    print(f"\n🔍 DEBUG {source.upper()}:")
    print(f"   Titre: {data.get('title', '❌')}")
    
    # CORRECTION : Gérer le cas où description est None
    description = data.get('description')
    desc_length = len(description) if description else 0
    print(f"   Description: {'✅' if description else '❌'} ({desc_length} chars)")
    
    # CORRECTION : Gérer le cas où short_description est None
    short_desc = data.get('short_description')
    short_desc_length = len(short_desc) if short_desc else 0
    print(f"   Description courte: {'✅' if short_desc else '❌'} ({short_desc_length} chars)")
    
    print(f"   Catégories: {data.get('categories', '❌')}")
    print(f"   Sous-catégories: {data.get('subcategories', '❌')}")
    print(f"   Marque: {data.get('brand', '❌')}")  # NOUVEAU: affichage marque
    print(f"   Image: {'✅' if data.get('image_url') else '❌'}")

def get_all_products_with_missing_data():
    """Récupère tous les produits où au moins un champ est NULL"""
    try:
        conn = connect_temp_srv()
        cursor = conn.cursor()
        
        query = """
        SELECT id, reference, title 
        FROM ps_products_comparison 
        WHERE description IS NULL 
           OR short_description IS NULL 
           OR categories IS NULL 
           OR subcategories IS NULL
           OR brand IS NULL
           OR image IS NULL
        """
        cursor.execute(query)
        products = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return products
    except Exception as e:
        print(f"Erreur base de données: {e}")
        return []

def get_product_by_reference(reference):
    """Récupère un produit spécifique par sa référence"""
    try:
        conn = connect_temp_srv()
        cursor = conn.cursor()
        
        query = """
        SELECT id, reference, title 
        FROM ps_products_comparison 
        WHERE reference = %s
        """
        cursor.execute(query, (reference,))
        product = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        return product
    except Exception as e:
        print(f"Erreur base de données: {e}")
        return None

def update_product_in_database(product_id, data):
    """Met à jour le produit dans la base de données - AVEC MARQUE"""
    try:
        conn = connect_temp_srv()
        cursor = conn.cursor()
        
        # ✅ SI PRODUIT NON TROUVÉ, ON NE FAIT PAS DE MISE À JOUR
        if data.get('status') in ['not_found', 'link_not_found', 'timeout', 'network_error', 'error', 'reference_mismatch']:
            print(f"🚫 Produit {product_id} NON TROUVÉ - AUCUNE mise à jour en base")
            cursor.close()
            conn.close()
            return False
            
        # ✅ NETTOYAGE RENFORCÉ DE L'ENCODAGE AVANT INSERTION
        cleaned_data = {
            'title': strip_problematic_characters(clean_encoding(data.get('title'))),
            'description': strip_problematic_characters(clean_encoding(data.get('description'))),
            'short_description': strip_problematic_characters(clean_encoding(data.get('short_description'))),
            'categories': strip_problematic_characters(clean_encoding(data.get('categories'))),
            'subcategories': strip_problematic_characters(clean_encoding(data.get('subcategories'))),
            'brand': strip_problematic_characters(clean_encoding(data.get('brand'))),  # NOUVEAU: marque
            'image_url': data.get('image_url')
        }
        
        # Vérification finale - si description contient encore des caractères problématiques, la tronquer
        if cleaned_data['description']:
            cleaned_data['description'] = re.sub(r'[^\x09\x0A\x0D\x20-\x7E\u00A0-\u00FF]', '', cleaned_data['description'])
        
        print(f"🧹 Données nettoyées - Titre: {len(cleaned_data['title'] or '')} chars, Marque: {cleaned_data['brand'] or 'N/A'}")
        
        # ✅ Produit trouvé, mise à jour normale AVEC MARQUE
        query = """
        UPDATE ps_products_comparison 
        SET title = %s,
            description = %s, 
            short_description = %s, 
            categories = %s, 
            subcategories = %s,
            brand = %s,  -- NOUVEAU: colonne marque
            image = %s,
            updated_at = NOW()
        WHERE id = %s
        """
        
        cursor.execute(query, (
            cleaned_data['title'],
            cleaned_data['description'],
            cleaned_data['short_description'],
            cleaned_data['categories'],
            cleaned_data['subcategories'],
            cleaned_data['brand'],  # NOUVEAU: marque
            cleaned_data['image_url'],
            product_id
        ))
        print(f"✅ Produit {product_id} mis à jour avec succès (marque: {cleaned_data['brand'] or 'N/A'})")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de la mise à jour du produit {product_id}: {e}")
        return False

# ============================================================================
# FONCTIONS D'EXTRACTION DE MARQUE
# ============================================================================

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
        
        return None
    except Exception as e:
        print(f"❌ Erreur extraction marque rightech: {e}")
        return None

# ============================================================================
# FONCTIONS RIGHTECH.MA - VERSION AMÉLIORÉE AVEC MARQUE
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

def scraper_rightech_detaille(reference):
    """Scrape les données détaillées pour une référence donnée sur rightech.ma"""
    try:
        # Construire l'URL de recherche rightech.ma
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
        
        # Détection des produits non trouvés sur rightech
        if detect_no_products_rightech(soup, reference):
            print(f"🚫 PRODUIT NON TROUVÉ sur rightech.ma: '{reference}'")
            return create_not_found_response(reference, 'not_found')
        
        # Chercher le lien du produit
        product_link = find_product_link_rightech(soup, reference)
        
        if not product_link:
            print(f"❌ Aucun lien produit trouvé sur rightech.ma pour '{reference}'")
            return create_not_found_response(reference, 'link_not_found')
        
        # Continuer avec le scraping normal...
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

def scraper_rightech_product_details(product_url, expected_reference):
    """Scrape les détails complets depuis la page produit rightech.ma - VERSION AVEC MARQUE"""
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
            # On continue quand même car le produit a été trouvé
        
        print(f"✅ Produit rightech.ma confirmé: {expected_reference}")
        
        # Extraire les données
        title = extract_rightech_title(soup)
        description = extract_rightech_description(soup)
        short_description = extract_rightech_short_description(soup)
        categories_data = extract_rightech_categories(soup)
        image_url = extract_rightech_image(soup)
        brand = extract_rightech_brand(soup)  # NOUVEAU: extraction de la marque
        
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
        
        return {
            'reference': expected_reference,
            'title': title,
            'description': description,
            'short_description': short_description,
            'categories': categories_data.get('categories'),
            'subcategories': categories_data.get('subcategories'),
            'image_url': image_url,
            'brand': brand,  # NOUVEAU: ajout de la marque
            'product_url': product_url,
            'status': 'success',
            'source': 'rightech'
        }
        
    except Exception as e:
        print(f"❌ Erreur lors du scraping des détails rightech.ma: {e}")
        return None

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

# ============================================================================
# FONCTIONS MIES.MA (adaptées avec vérification flexible et marque)
# ============================================================================

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

def scraper_mies_product_details(product_url, expected_reference):
    """Scrape les détails complets depuis la page produit mies.ma - VERSION AVEC MARQUE"""
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
            # On continue quand même car le produit a été trouvé
        
        print(f"✅ Produit mies.ma confirmé: {expected_reference}")
        
        title = extract_mies_title(soup)
        description = extract_mies_description(soup)
        short_description = extract_mies_short_description(soup)
        categories_data = extract_mies_categories(soup)
        image_url = extract_mies_image(soup)
        brand = extract_mies_brand(soup)  # NOUVEAU: extraction de la marque
        
        if not description and short_description:
            description = short_description
        elif description and not short_description:
            soup_desc = BeautifulSoup(description, 'html.parser')
            text_content = soup_desc.get_text(strip=True)
            short_description = text_content[:200] + "..." if len(text_content) > 200 else text_content
        
        return {
            'reference': expected_reference,
            'title': title,
            'description': description,
            'short_description': short_description,
            'categories': categories_data.get('categories'),
            'subcategories': categories_data.get('subcategories'),
            'image_url': image_url,
            'brand': brand,  # NOUVEAU: ajout de la marque
            'product_url': product_url,
            'status': 'success',
            'source': 'mies'
        }
        
    except Exception as e:
        print(f"❌ Erreur lors du scraping des détails mies.ma: {e}")
        return None

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

def create_not_found_response(reference, status='not_found'):
    """Crée une réponse standard pour les produits non trouvés"""
    return {
        'reference': reference,
        'title': None,
        'description': None,
        'short_description': None,
        'categories': None,
        'subcategories': None,
        'brand': None,  # NOUVEAU: marque incluse
        'image_url': None,
        'product_url': None,
        'status': status
    }

# ============================================================================
# FONCTION PRINCIPALE AVEC SCORING INTELLIGENT - VERSION AVEC MARQUE
# ============================================================================

def scraper_combined(reference):
    """Scrape combiné avec scoring intelligent mies.ma + rightech.ma - VERSION AVEC MARQUE"""
    print(f"🎯 SCRAPING COMBINÉ POUR: {reference}")
    print("=" * 60)
    
    # Scraper les deux sites
    print("\n🔍 SCRAPING MIES.MA...")
    mies_data = scraper_mies_detaille(reference)
    
    print("\n🔍 SCRAPING RIGHTECH.MA...")
    rightech_data = scraper_rightech_detaille(reference)
    
    # DEBUG des données
    debug_product_data(mies_data, "mies.ma")
    debug_product_data(rightech_data, "rightech.ma")
    
    # Calculer les scores
    mies_score = calculate_data_score(mies_data) if mies_data else 0
    rightech_score = calculate_data_score(rightech_data) if rightech_data else 0
    
    print(f"\n📊 SCORES OBTENUS:")
    print(f"   mies.ma: {mies_score}/100")
    print(f"   rightech.ma: {rightech_score}/100")
    
    # ANALYSE DES CHAMPS MANQUANTS
    mies_missing = analyze_missing_fields(mies_data) if mies_data else []
    rightech_missing = analyze_missing_fields(rightech_data) if rightech_data else []
    
    if mies_missing:
        print(f"📝 Champs manquants sur mies.ma: {mies_missing}")
    if rightech_missing:
        print(f"📝 Champs manquants sur rightech.ma: {rightech_missing}")
    
    # LOGIQUE DE DÉCISION AMÉLIORÉE
    if mies_score == 100:
        print("🎯 mies.ma a TOUTES les données - Utilisation exclusive")
        final_data = mies_data
        final_data['score'] = mies_score
        final_data['sources_used'] = ['mies']
        
    elif rightech_score == 100:
        print("🎯 rightech.ma a TOUTES les données - Utilisation exclusive")
        final_data = rightech_data
        final_data['score'] = rightech_score
        final_data['sources_used'] = ['rightech']
        
    elif mies_score >= 80 and rightech_score >= 80:
        print("✅ Les deux sites ont des données complètes")
        # Vérifier s'il y a des champs manquants à compléter
        if mies_missing and not rightech_missing:
            print("🔄 rightech.ma peut compléter mies.ma")
            final_data = merge_product_data(mies_data, rightech_data)
        elif rightech_missing and not mies_missing:
            print("🔄 mies.ma peut compléter rightech.ma")
            final_data = merge_product_data(rightech_data, mies_data)
        else:
            print("🎯 Utilisation des données de mies.ma (priorité)")
            final_data = mies_data
            final_data['score'] = mies_score
            final_data['sources_used'] = ['mies']
        
    elif mies_score >= 80:
        print("✅ mies.ma a des données complètes")
        # Vérifier si rightech.ma peut apporter des améliorations
        if rightech_score > 0 and rightech_missing:
            print(f"🔄 rightech.ma peut compléter {len(rightech_missing)} champ(s) manquant(s)")
            final_data = merge_product_data(mies_data, rightech_data)
        else:
            print("🎯 Utilisation exclusive de mies.ma")
            final_data = mies_data
            final_data['score'] = mies_score
            final_data['sources_used'] = ['mies']
        
    elif rightech_score >= 80:
        print("✅ rightech.ma a des données complètes")
        # Vérifier si mies.ma peut apporter des améliorations
        if mies_score > 0 and mies_missing:
            print(f"🔄 mies.ma peut compléter {len(mies_missing)} champ(s) manquant(s)")
            final_data = merge_product_data(rightech_data, mies_data)
        else:
            print("🎯 Utilisation exclusive de rightech.ma")
            final_data = rightech_data
            final_data['score'] = rightech_score
            final_data['sources_used'] = ['rightech']
        
    elif mies_score > 0 and rightech_score > 0:
        print("🔄 Les deux sites ont des données partielles")
        print("🎯 Fusion des données...")
        
        # Déterminer la source principale (celle avec le meilleur score)
        if mies_score >= rightech_score:
            primary_data = mies_data
            secondary_data = rightech_data
            print("   Source principale: mies.ma")
        else:
            primary_data = rightech_data
            secondary_data = mies_data
            print("   Source principale: rightech.ma")
        
        final_data = merge_product_data(primary_data, secondary_data)
        print(f"   Score final après fusion: {final_data['score']}/100")
        
    elif mies_score > 0:
        print("⚠️  Seul mies.ma a des données")
        final_data = mies_data
        final_data['score'] = mies_score
        final_data['sources_used'] = ['mies']
        
    elif rightech_score > 0:
        print("⚠️  Seul rightech.ma a des données")
        final_data = rightech_data
        final_data['score'] = rightech_score
        final_data['sources_used'] = ['rightech']
        
    else:
        print("❌ Aucune donnée valide trouvée sur les deux sites")
        final_data = create_not_found_response(reference, 'not_found')
        final_data['score'] = 0
        final_data['sources_used'] = []
    
    # Afficher le résumé
    print(f"\n🎯 RÉSULTAT FINAL:")
    print(f"   Score: {final_data.get('score', 0)}/100")
    print(f"   Sources utilisées: {final_data.get('sources_used', [])}")
    print(f"   Titre: {'✅' if final_data.get('title') else '❌'}")
    print(f"   Description: {'✅' if final_data.get('description') else '❌'}")
    print(f"   Catégories: {'✅' if final_data.get('categories') else '❌'}")
    print(f"   Marque: {'✅' if final_data.get('brand') else '❌'}")  # NOUVEAU: affichage marque
    print(f"   Image: {'✅' if final_data.get('image_url') else '❌'}")
    
    return final_data

def test_and_update_single_product_combined(reference):
    """Teste ET met à jour un seul produit avec le système combiné"""
    try:
        print(f"🧪 TEST ET MISE À JOUR COMBINÉE: {reference}")
        print("=" * 60)
        
        product = get_product_by_reference(reference)
        
        if not product:
            print(f"❌ Produit {reference} non trouvé dans la base de données")
            return False
        
        product_id, db_reference, current_title = product
        print(f"🆔 ID produit: {product_id}")
        print(f"📦 Référence base: {db_reference}")
        print(f"🏷️ Titre actuel: {current_title}")
        print("-" * 50)
        
        # Scraper les données combinées
        scraped_data = scraper_combined(reference)
        
        if scraped_data and scraped_data.get('status') == 'success':
            print(f"\n🎯 DONNÉES FINALES POUR {reference}:")
            print("=" * 50)
            print(f"📝 Titre: {scraped_data['title']}")
            print(f"📄 Description: {'✅' if scraped_data['description'] else '❌'}")
            print(f"📂 Catégories: {scraped_data['categories']}")
            print(f"📁 Sous-catégories: {scraped_data['subcategories']}")
            print(f"🏷️ Marque: {scraped_data['brand'] or 'N/A'}")  # NOUVEAU: affichage marque
            print(f"🖼️ Image: {'✅' if scraped_data['image_url'] else '❌'}")
            print(f"📊 Score: {scraped_data.get('score', 0)}/100")
            print(f"🔗 Sources: {scraped_data.get('sources_used', [])}")
            
            print(f"\n💾 MISE À JOUR EN BASE DE DONNÉES...")
            if update_product_in_database(product_id, scraped_data):
                print(f"🎉 PRODUIT {reference} TRAITÉ ET MIS À JOUR AVEC SUCCÈS!")
                return True
            else:
                print(f"❌ ÉCHEC DE LA MISE À JOUR POUR {reference}")
                return False
        else:
            print(f"\n🚫 PRODUIT NON TROUVÉ - AUCUNE MISE À JOUR EFFECTUÉE")
            return False
            
    except Exception as e:
        print(f"❌ ERREUR CRITIQUE: {e}")
        print(traceback.format_exc())
        return False

def test_brand_extraction():
    """Teste l'extraction de marque sur un produit spécifique"""
    test_reference = "P60637-421"
    print(f"🧪 TEST EXTRACTION MARQUE POUR: {test_reference}")
    
    # Test sur mies.ma
    print("\n🔍 TEST MIES.MA...")
    mies_data = scraper_mies_detaille(test_reference)
    if mies_data and mies_data.get('status') == 'success':
        print(f"✅ Marque mies.ma: {mies_data.get('brand', 'Non trouvée')}")
    
    # Test sur rightech.ma
    print("\n🔍 TEST RIGHTECH.MA...")
    rightech_data = scraper_rightech_detaille(test_reference)
    if rightech_data and rightech_data.get('status') == 'success':
        print(f"✅ Marque rightech.ma: {rightech_data.get('brand', 'Non trouvée')}")

def main_combined():
    """Fonction principale avec scraping combiné"""
    print("🚀 DÉBUT DU SCRAPING COMBINÉ MIES.MA + RIGHTECH.MA")
    print("=" * 60)
    
    try:
        products = get_all_products_with_missing_data()
        
        if not products:
            print("✅ Aucun produit avec données manquantes trouvé")
            return
        
        print(f"📊 {len(products)} produits à traiter")
        print("=" * 60)
        
        stats = {
            'success': 0,
            'not_found': 0,
            'error': 0,
            'skipped': 0,
            'scores': []
        }
        
        for i, product in enumerate(products, 1):
            try:
                product_id, reference, title = product
                
                if not reference or not reference.strip():
                    print(f"⚠️ Référence vide, skip...")
                    stats['skipped'] += 1
                    continue
                    
                print(f"\n🎯 PRODUIT {i}/{len(products)}")
                print(f"📦 Référence: {reference}")
                print(f"🏷️ Titre: {title}")
                print("-" * 50)
                
                # Scraper les données combinées
                scraped_data = scraper_combined(reference.strip())
                
                if scraped_data and scraped_data.get('status') == 'success':
                    # Mise à jour normale
                    if update_product_in_database(product_id, scraped_data):
                        stats['success'] += 1
                        score = scraped_data.get('score', 0)
                        stats['scores'].append(score)
                        print(f"✅ Produit {reference} mis à jour (score: {score}/100)")
                    else:
                        stats['error'] += 1
                        print(f"❌ Erreur de mise à jour pour {reference}")
                else:
                    # Produit non trouvé
                    stats['not_found'] += 1
                    print(f"🚫 Produit {reference} NON trouvé")
                
                # Pause entre chaque requête
                if i < len(products):
                    print("⏳ Pause de 3 secondes...")
                    time.sleep(3)
                    
            except KeyboardInterrupt:
                print("\n⏹️ Arrêt demandé par l'utilisateur")
                break
            except Exception as e:
                print(f"❌ Erreur sur le produit {product_id}: {e}")
                stats['error'] += 1
                continue
        
        # STATISTIQUES FINALES
        print(f"\n🎉 SCRAPING COMBINÉ TERMINÉ!")
        print("=" * 50)
        print(f"✅ Produits trouvés et mis à jour: {stats['success']}")
        print(f"🚫 Produits non trouvés: {stats['not_found']}")
        print(f"💥 Erreurs: {stats['error']}")
        print(f"⚠️ Skippés: {stats['skipped']}")
        
        if stats['scores']:
            avg_score = sum(stats['scores']) / len(stats['scores'])
            max_score = max(stats['scores'])
            min_score = min(stats['scores'])
            print(f"📈 Score moyen: {avg_score:.1f}/100")
            print(f"🏆 Meilleur score: {max_score}/100")
            print(f"📉 Pire score: {min_score}/100")
        
        total_processed = stats['success'] + stats['not_found'] + stats['error']
        success_rate = (stats['success'] / total_processed * 100) if total_processed > 0 else 0
        print(f"📊 Taux de succès: {success_rate:.1f}%")
        print(f"📦 Total traité: {total_processed}/{len(products)}")
        
    except Exception as e:
        print(f"❌ ERREUR CRITIQUE: {e}")
        print(traceback.format_exc())

if __name__ == "__main__":
    # Pour tester l'extraction de marque
    # test_brand_extraction()
    
    # Pour tester et mettre à jour un seul produit
    # test_and_update_single_product_combined("90NR0LW1-M00290")
    
    # Pour traiter tous les produits avec données manquantes
    main_combined()