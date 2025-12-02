import re
import json
import urllib.parse
from bs4 import BeautifulSoup
import requests
from database import connect_temp_srv


def clean_text(text):
    """Nettoie le texte des caractères problématiques pour la base de données - VERSION AMÉLIORÉE"""
    if not text:
        return text
    
    # Remplace les caractères problématiques courants
    replacements = {
        '″': '"',        # Double prime
        '′': "'",        # Prime
        ' ': ' ',        # Narrow no-break space
        '–': '-',        # En dash
        '—': '-',        # Em dash
        '―': '-',        # Horizontal bar
        '‒': '-',        # Figure dash
        '‐': '-',        # Hyphen
        '‑': '-',        # Non-breaking hyphen
        '⁃': '-',        # Hyphen bullet
        '−': '-',        # Minus sign
        '–': '-',        # En dash
        '—': '-',        # Em dash
        '‘': "'",        # Left single quotation mark
        '’': "'",        # Right single quotation mark
        '‚': "'",        # Single low-9 quotation mark
        '‛': "'",        # Single high-reversed-9 quotation mark
        '“': '"',        # Left double quotation mark
        '”': '"',        # Right double quotation mark
        '„': '"',        # Double low-9 quotation mark
        '‟': '"',        # Double high-reversed-9 quotation mark
        '…': '...',      # Ellipsis
        '«': '"',        # French left guillemet
        '»': '"',        # French right guillemet
        '‹': "'",        # Single left-pointing angle quotation mark
        '›': "''",        # Single right-pointing angle quotation mark
        '×': 'x',        # Multiplication sign
        '÷': '/',        # Division sign
        '±': '+/-',      # Plus-minus sign
        '•': '-',        # Bullet
        '·': '-',        # Middle dot
        '⋅': '.',        # Dot operator
        '◦': '-',        # White bullet
        '☐': '[ ]',      # Ballot box
        '☑': '[X]',      # Ballot box with check
        '☒': '[X]',      # Ballot box with X
        '✓': '[OK]',     # Check mark
        '✔': '[OK]',     # Heavy check mark
        '♡': '[HEART]',  # Heart
        '♥': '[HEART]',  # Heart
        '❦': '[FLOWER]', # Floral heart
        '☺': ':)',       # Smiling face
        '☻': ':)',       # Smiling face
        '😊': ':)',      # Smiling face with smiling eyes
        '🙂': ':)',      # Slightly smiling face
        '🤔': '[:thinking]', # Thinking face
        '⭐': '[STAR]',   # Star
        '★': '[STAR]',   # Star
        '☆': '[STAR]',   # Star
        '⚡': '[ZAP]',    # High voltage
        '🔥': '[FIRE]',   # Fire
        '❤': '[HEART]',  # Heart
        '✅': '[OK]',     # Check mark button
        '✔️': '[OK]',     # Check mark
        '➡️': '[->]',     # Right arrow
        '⬅️': '[<-]',     # Left arrow
        '⬆️': '[UP]',     # Up arrow
        '⬇️': '[DOWN]',   # Down arrow
        '↔️': '[<->]',    # Left-right arrow
        '↕️': '[UP-DOWN]', # Up-down arrow
        '©': '(c)',      # Copyright
        '®': '(R)',      # Registered
        '™': '(TM)',     # Trademark
        '℠': '(SM)',     # Service mark
        '‰': '%',        # Per mille
        '‱': '%',        # Per ten thousand
        '¶': 'P',        # Pilcrow
        '§': 'S',        # Section
        '†': '*',        # Dagger
        '‡': '**',       # Double dagger
        '♠': '[SPADE]',  # Spade suit
        '♣': '[CLUB]',   # Club suit
        '♥': '[HEART]',  # Heart suit
        '♦': '[DIAMOND]', # Diamond suit
        '♤': '[SPADE]',  # Spade suit white
        '♧': '[CLUB]',   # Club suit white
        '♡': '[HEART]',  # Heart suit white
        '♢': '[DIAMOND]', # Diamond suit white
        '☆': '[STAR]',   # White star
        '✓': '[OK]',     # Check mark
        '✗': '[X]',      # Ballot X
        '✘': '[X]',      # Heavy ballot X
        '•': '-',        # Bullet
        '‣': '-',        # Triangle bullet
        '⁃': '-',        # Hyphen bullet
        '◦': '-',        # White bullet
        '⦾': '-',        # Circled bullet
        '⦿': '-',        # Circled bullet
        '\u200b': '',    # ZERO WIDTH SPACE
        '\u200c': '',    # ZERO WIDTH NON-JOINER
        '\u200d': '',    # ZERO WIDTH JOINER
        '\u200e': '',    # LEFT-TO-RIGHT MARK
        '\u200f': '',    # RIGHT-TO-LEFT MARK
        '\u202a': '',    # LEFT-TO-RIGHT EMBEDDING
        '\u202b': '',    # RIGHT-TO-LEFT EMBEDDING
        '\u202c': '',    # POP DIRECTIONAL FORMATTING
        '\u202d': '',    # LEFT-TO-RIGHT OVERRIDE
        '\u202e': '',    # RIGHT-TO-LEFT OVERRIDE
        '\u2060': '',    # WORD JOINER
        '\u2066': '',    # LEFT-TO-RIGHT ISOLATE
        '\u2067': '',    # RIGHT-TO-LEFT ISOLATE
        '\u2068': '',    # FIRST STRONG ISOLATE
        '\u2069': '',    # POP DIRECTIONAL ISOLATE
        '\ufeff': '',    # BYTE ORDER MARK
        '\u00a0': ' ',   # NO-BREAK SPACE
        '\u1680': ' ',   # OGHAM SPACE MARK
        '\u2000': ' ',   # EN QUAD
        '\u2001': ' ',   # EM QUAD
        '\u2002': ' ',   # EN SPACE
        '\u2003': ' ',   # EM SPACE
        '\u2004': ' ',   # THREE-PER-EM SPACE
        '\u2005': ' ',   # FOUR-PER-EM SPACE
        '\u2006': ' ',   # SIX-PER-EM SPACE
        '\u2007': ' ',   # FIGURE SPACE
        '\u2008': ' ',   # PUNCTUATION SPACE
        '\u2009': ' ',   # THIN SPACE
        '\u200a': ' ',   # HAIR SPACE
        '\u202f': ' ',   # NARROW NO-BREAK SPACE
        '\u205f': ' ',   # MEDIUM MATHEMATICAL SPACE
        '\u3000': ' ',   # IDEOGRAPHIC SPACE
        '\u180e': '',    # MONGOLIAN VOWEL SEPARATOR
        '\u200b': '',    # ZERO WIDTH SPACE
        '\u200c': '',    # ZERO WIDTH NON-JOINER
        '\u200d': '',    # ZERO WIDTH JOINER
        '\u2060': '',    # WORD JOINER
        '\ufeff': '',    # ZERO WIDTH NO-BREAK SPACE
        '\u2011': '-',   # NON-BREAKING HYPHEN (le caractère problématique)
        '\u2010': '-',   # HYPHEN
        '\u2012': '-',   # FIGURE DASH
        '\u2013': '-',   # EN DASH
        '\u2014': '-',   # EM DASH
        '\u2015': '-',   # HORIZONTAL BAR
        '\u2043': '-',   # HYPHEN BULLET
        '\u2212': '-',   # MINUS SIGN
        '\uFE58': '-',   # SMALL EM DASH
        '\uFE63': '-',   # SMALL HYPHEN-MINUS
        '\uFF0D': '-',   # FULLWIDTH HYPHEN-MINUS
    }
    
    # Appliquer les remplacements
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    # Nettoyer les caractères de contrôle (0x00-0x1F, 0x7F)
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    
    # Nettoyer les caractères Unicode problématiques supplémentaires
    # Plages de caractères à supprimer
    problematic_ranges = [
        '\u2000-\u200F',    # Espaces et marques de formatage
        '\u2028-\u202F',    # Séparateurs et marques de formatage
        '\u205F-\u206F',    # Espaces mathématiques et marques de formatage
        '\uFE00-\uFE0F',    # Variation Selectors
        '\uFEFF',           # Byte Order Mark
        '\uFFF0-\uFFFF',    # Specials
        '\uE000-\uF8FF',    # Private Use Area
        '\uDC00-\uDFFF',    # Low Surrogates
        '\uD800-\uDBFF',    # High Surrogates
    ]
    
    for char_range in problematic_ranges:
        text = re.sub(f'[{char_range}]', '', text)
    
    # Supprimer les autres caractères non-ASCII problématiques
    # Garder les caractères ASCII étendus (Latin-1) mais nettoyer le reste
    text = re.sub(r'[^\x00-\x7F\u00A0-\u00FF\u0152\u0153\u0178\u017D\u017E\u0192\u02C6\u02DC\u2013\u2014\u2018\u2019\u201A\u201C\u201D\u201E\u2020\u2021\u2022\u2026\u2030\u2039\u203A\u20AC\u2122]', '', text)
    
    # Nettoyer les espaces multiples
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()

def clean_site_names_from_title(title):
    """Nettoie les noms de sites et marques de distributeurs depuis le titre"""
    if not title:
        return title
    
    # Liste des patterns à supprimer (noms de sites et marques)
    patterns_to_remove = [
        r'\s*[-|~•]\s*Linksolutions.*$',
        r'\s*[-|~•]\s*Links? Solutions?.*$', 
        r'\s*[-|~•]\s*Maroc.*$',
        r'\s*[-|~•]\s*Crenova.*$',
        r'\s*[-|~•]\s*Duga.*$',
        r'\s*[-|~•]\s*Tabtel.*$',
        r'\s*[-|~•]\s*Tech.*$',
        r'\s*[-|~•]\s*Store.*$',
        r'\s*[-|~•]\s*Shop.*$',
        r'\s*[-|~•]\s*Boutique.*$',
        r'\s*[-|~•]\s*Market.*$',
        r'\s*[-|~•]\s*Electro.*$',
        r'\s*[-|~•]\s*Info.*$',
        r'\s*à\s*.*$',  # Pour "à Linksolutions Maroc" etc.
        r'\s*–\s*.*$',  # Pour le tiret cadratin
        r'\s*—\s*.*$',  # Pour le tiret long
    ]
    
    original_title = title
    for pattern in patterns_to_remove:
        title = re.sub(pattern, '', title, flags=re.IGNORECASE)
    
    # Supprimer les espaces multiples et trimmer
    title = re.sub(r'\s+', ' ', title).strip()
    
    # Si le nettoyage a trop raccourci le titre, garder l'original
    if len(title) < 10 and len(original_title) > 20:
        return original_title
        
    return title

def clean_brand_name(brand_text):
    """Nettoie et normalise le nom de la marque - VERSION AVEC REMPLACEMENT PAR DIX"""
    if not brand_text:
        return None
    
    # Convertir en majuscules pour la normalisation
    brand_text = str(brand_text).upper().strip()
    
    # 🔥 REMPLACER LES NOMS DE SITES/DISTRIBUTEURS PAR "DIX"
    SITE_NAMES_REPLACEMENT = {
        'CRENOVA': 'DIX',
        'LINKSOLUTIONS': 'DIX', 
        'LINK SOLUTIONS': 'DIX',
        'DUGA': 'DIX',
        'TABTEL': 'DIX',
        'TABTEL.MA': 'DIX',
        'TABTEL MA': 'DIX',
        'TABTELMAROC': 'DIX',
        'TABTEL MAROC': 'DIX',
        'MAROC': 'DIX',
        'MOROCCO': 'DIX',
        'MA': 'DIX',
        'YITH': 'DIX',
        'WCBR': 'DIX'
    }
    
    # Vérifier si c'est exactement un nom de site (remplacer par DIX)
    if brand_text in SITE_NAMES_REPLACEMENT:
        print(f"🔄 Marque remplacée (nom de site): '{brand_text}' → 'DIX'")
        return 'DIX'
    
    # Vérifier si le texte contient un nom de site (remplacer par DIX)
    for site_name, replacement in SITE_NAMES_REPLACEMENT.items():
        if site_name in brand_text:
            print(f"🔄 Marque remplacée (contient nom de site): '{brand_text}' → 'DIX'")
            return 'DIX'
    
    # Dictionnaire des sous-marques et leurs marques principales
    SUB_BRANDS = {
        # ASUS
        'ASUS ROG': 'ASUS',
        'ROG': 'ASUS',
        'ASUS TUF': 'ASUS',
        'TUF GAMING': 'ASUS',
        'ASUS ZENBOOK': 'ASUS',
        'ZENBOOK': 'ASUS',
        'ASUS VIVOBOOK': 'ASUS',
        'VIVOBOOK': 'ASUS',
        
        # HP
        'HP OMEN': 'HP',
        'OMEN': 'HP',
        'HP PAVILION': 'HP',
        'PAVILION': 'HP',
        'HP ENVY': 'HP',
        'ENVY': 'HP',
        'HP SPECTRE': 'HP',
        'SPECTRE': 'HP',
        'HP ELITE': 'HP',
        'ELITE': 'HP',
        'HP PRO': 'HP',
        
        # DELL
        'DELL ALIENWARE': 'DELL',
        'ALIENWARE': 'DELL',
        'DELL XPS': 'DELL',
        'XPS': 'DELL',
        'DELL INSPIRON': 'DELL',
        'INSPIRON': 'DELL',
        'DELL LATITUDE': 'DELL',
        'LATITUDE': 'DELL',
        'DELL PRECISION': 'DELL',
        'PRECISION': 'DELL',
        
        # LENOVO
        'LENOVO THINKPAD': 'LENOVO',
        'THINKPAD': 'LENOVO',
        'LENOVO THINKBOOK': 'LENOVO',
        'THINKBOOK': 'LENOVO',
        'LENOVO IDEAPAD': 'LENOVO',
        'IDEAPAD': 'LENOVO',
        'LENOVO LEGION': 'LENOVO',
        'LEGION': 'LENOVO',
        'LENOVO YOGA': 'LENOVO',
        'YOGA': 'LENOVO',
        
        # ACER
        'ACER PREDATOR': 'ACER',
        'PREDATOR': 'ACER',
        'ACER ASPIRE': 'ACER',
        'ASPIRE': 'ACER',
        'ACER NITRO': 'ACER',
        'NITRO': 'ACER',
        'ACER SWIFT': 'ACER',
        'SWIFT': 'ACER',
        
        # MSI
        'MSI GAMING': 'MSI',
        'MSI DRAGON': 'MSI',
        
        # GIGABYTE
        'GIGABYTE AORUS': 'GIGABYTE',
        'AORUS': 'GIGABYTE',
        
        # APPLE
        'MACBOOK': 'APPLE',
        'IMAC': 'APPLE',
        'IPHONE': 'APPLE',
        'IPAD': 'APPLE',
        
        # SAMSUNG
        'SAMSUNG GALAXY': 'SAMSUNG',
        'GALAXY': 'SAMSUNG',
        'SAMSUNG ODYSSEY': 'SAMSUNG',
        'ODYSSEY': 'SAMSUNG',
    }
    
    # Vérifier d'abord si c'est une sous-marque connue
    for sub_brand, main_brand in SUB_BRANDS.items():
        if sub_brand in brand_text:
            print(f"🔍 Sous-marque détectée: '{sub_brand}' → marque principale: '{main_brand}'")
            return main_brand
    
    # Si pas une sous-marque, continuer avec le nettoyage normal
    # Supprimer les textes indésirables spécifiques
    unwanted_patterns = [
        r'LISTE DES PRODUITS DE\s*',
        r'LISTE DES PRODUITS DE LA MARQUE\s*',
        r'PRODUITS DE LA MARQUE\s*',
        r'MA\s+.*TECHNOLOGIES AGRÉÉ\s*',
        r'MA\s+PARTENER WITH\s*',
        r'MA\s+.*AGRÉÉ\s*',
        r'PC\s+PARTNER\s+AUTHORIZED\s*',
        r'PARTNER\s+AUTHORIZED\s*',
        r'TABTEL\.MA\s+PARTENAIRE\s*',
        r'CLIQUEZ ICI POUR VOIR TOUS LES PRODUITS\s*',
        r'TOUS LES PRODUITS DE CETTE MARQUE\s*',
    ]
    
    for pattern in unwanted_patterns:
        brand_text = re.sub(pattern, '', brand_text, flags=re.IGNORECASE)
    
    # Si c'est un nom de fichier, extraire juste le nom sans extension
    if '.' in brand_text and any(ext in brand_text.lower() for ext in ['.png', '.jpg', '.jpeg', '.webp']):
        brand_text = brand_text.split('.')[0]
    
    # Supprimer les caractères spéciaux mais garder les lettres, chiffres, espaces et traits d'union
    cleaned = re.sub(r'[^\w\s-]', ' ', brand_text)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    # 🔥 VÉRIFICATION FINALE : Remplacer les noms de sites même après nettoyage
    if cleaned in SITE_NAMES_REPLACEMENT:
        print(f"🔄 Marque remplacée après nettoyage: '{cleaned}' → 'DIX'")
        return 'DIX'
    
    # Liste des marques valides connues (marques principales)
    valid_brands = {
        'ASUS', 'HP', 'DELL', 'LENOVO', 'ACER', 'SAMSUNG', 'CANON', 'EPSON', 
        'BROTHER', 'LEXMARK', 'APC', 'TP-LINK', 'LOGITECH', 'MICROSOFT',
        'JABRA', 'EATON', 'INTEL', 'ADATA', 'SANDISK', 'LACIE', 'TARGUS', 
        'MOBILIS', 'ORAY', 'HISENSE', 'V7', 'MSI', 'GIGABYTE', 'APPLE',
        'HUAWEI', 'WESTERN DIGITAL', 'SEAGATE', 'TOSHIBA', 
        'KINGSTON', 'CRUCIAL', 'CORSAIR', 'G.SKILL', 'HYPERX', 'PATRIOT', 
        'GEIL', 'TEAMGROUP', 'SILICON POWER', 'TRANSCEND', 'SYNOLOGY', 'QNAP',
        'DIX'  # AJOUT DE DIX COMME MARQUE VALIDE
    }
    
    # Vérifier si le texte nettoyé est une marque valide
    if cleaned in valid_brands:
        return cleaned
    
    # Vérifier si le texte contient une marque valide
    for brand in valid_brands:
        if brand in cleaned:
            return brand
    
    # Supprimer les mots communs non désirables
    unwanted_words = [
        'MARQUE', 'BRAND', 'LOGO', 'FABRICANT', 'MANUFACTURER', 
        'PARTENAIRE', 'PARTNER', 'SUR', 'ON', 'LE', 'LA', 'LES', 'DES', 'DU', 'DE',
        'MOROCCO', 'MAROC', 'TABTEL', 'LINKSOLUTIONS', 'CRENOVA', 'DUGA',  # Sites (seront remplacés)
        'YITH', 'WCBR', 'BRANDS', 'PRODUITS', 'PRODUCTS', 'TECHNOLOGIES',
        'AGRÉÉ', 'AUTHORIZED', 'WITH', 'MA ', 'FR', 'PC', 'TABLET', 'PHONE',
        'GAMING', 'SERIES', 'EDITION', 'PRO', 'MAX', 'PLUS', 'ULTRA' , 'ACCESSOIRES INFORMATIQUE'  # Termes produits
    ]
    
    words = cleaned.split()
    filtered_words = [word for word in words if word not in unwanted_words and len(word) > 1]
    
    cleaned = ' '.join(filtered_words).strip()
    
    # 🔥 DERNIÈRE VÉRIFICATION : Remplacer les noms de sites résiduels
    if cleaned in SITE_NAMES_REPLACEMENT:
        print(f"🔄 Marque remplacée après filtrage mots: '{cleaned}' → 'DIX'")
        return 'DIX'
    
    # Vérifications finales
    if (cleaned and 
        len(cleaned) >= 2 and 
        len(cleaned) <= 30 and
        any(c.isalpha() for c in cleaned) and
        not cleaned.isnumeric() and
        not any(unwanted in cleaned for unwanted in [
            'D4ES01-8G', '02311VGN', '90NR0LR1-M00AM0'  # Codes produits à exclure
        ])):
        return cleaned
    
    return None

def normalize_image_url(url, base_url):
    """Normalise l'URL de l'image"""
    if not url:
        return url
    
    if url.startswith('//'):
        return 'https:' + url
    elif url.startswith('/'):
        return base_url + url
    
    return url

def ensure_data_consistency(data):
    """Garantit que les données sont cohérentes avant insertion - AVEC MARQUE"""
    if not data:
        return data
    
    # Dupliquer categories en subcategories si nécessaire
    if data.get('categories') and not data.get('subcategories'):
        data['subcategories'] = data['categories']
        print(f"🔄 COHÉRENCE: Catégories dupliquées en sous-catégories: {data['categories']}")
    
    # Utiliser short_description comme description si nécessaire
    if not data.get('description') and data.get('short_description'):
        data['description'] = data['short_description']
        print(f"🔄 COHÉRENCE: Description courte utilisée comme description")
    
    # Normaliser la marque si elle existe
    if data.get('brand'):
        data['brand'] = clean_brand_name(data['brand'])
        print(f"🔄 COHÉRENCE: Marque normalisée: {data['brand']}")
    
    return data


def get_all_products_from_db(site_name):
    try:
        conn = connect_temp_srv()
        cursor = conn.cursor()
        
        # Récupérer les produits qui ont au moins un site en 'pending'
        query = f"""
        SELECT id, reference, {site_name}_title, {site_name}_description, {site_name}_short_description, 
               {site_name}_categories, {site_name}_subcategories, {site_name}_brand, {site_name}_image, 
               {site_name}_url, {site_name}_scraped_at
        FROM ps_products_comparison_V2
        WHERE {site_name}_status = 'pending'
        """
        
        cursor.execute(query)
        products = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        print(f"✅ {len(products)} produits avec statut 'pending' récupérés")
        return products
        
    except Exception as e:
        print(f"❌ Erreur base de données: {e}")
        return []
    
def get_product_info_for_scraping(reference, site_name):
    try:
        # Vérifier que le site est valide
        valid_sites = ['crenova', 'duga', 'linksolutions', 'tabtel', 'mies', 'rightech']
        if site_name not in valid_sites:
            print(f"❌ Nom de site invalide: {site_name}")
            return None
        
        conn = connect_temp_srv()
        cursor = conn.cursor()
        
        # Récupérer l'ID et la référence si le produit a statut 'pending' pour ce site
        # CORRECTION: Supprimer la virgule en trop après {site_name}_scraped_at
        query = f"""
        SELECT id, reference, {site_name}_title, {site_name}_description, {site_name}_short_description, 
               {site_name}_categories, {site_name}_subcategories, {site_name}_brand, {site_name}_image, 
               {site_name}_url, {site_name}_scraped_at
        FROM ps_products_comparison_V2
        WHERE reference = %s
          AND {site_name}_status = 0
        """
        
        cursor.execute(query, (reference,))
        product = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if product:
            print(f"✅ Produit {reference} disponible pour scraping sur {site_name}")
            
            # Afficher un aperçu des informations récupérées
            print(f"📋 Informations récupérées:")
            print(f"  - ID: {product[0]}")
            print(f"  - Référence: {product[1]}")
            print(f"  - Titre: {product[2][:50] if product[2] else 'Non disponible'}...")
            print(f"  - URL: {product[9] if product[9] else 'Non disponible'}")
            
            return product
        else:
            print(f"ℹ️ Produit {reference} non disponible pour scraping sur {site_name}")
            return None
        
    except Exception as e:
        print(f"❌ Erreur lors de la récupération des infos pour {reference}: {e}")
        return None
    

def update_product_in_database(product_id, data, site_name):
    try:
        conn = connect_temp_srv()
        cursor = conn.cursor()
        
        # 🔥 CORRECTION: Assurer la cohérence des données
        final_categories = data.get('categories')
        final_subcategories = data.get('subcategories')
        final_description = data.get('description')
        final_short_description = data.get('short_description')
        
        # Si pas de sous-catégories mais on a des catégories, on duplique
        if not final_subcategories and final_categories:
            final_subcategories = final_categories
            print(f"🔄 DB: Catégories dupliquées en sous-catégories: {final_categories}")
        
        # Si pas de description mais on a une description courte, on l'utilise
        if not final_description and final_short_description:
            final_description = final_short_description
            print(f"🔄 DB: Description courte utilisée comme description")
        
        # Nettoyer les données avant insertion
        cleaned_data = {
            'title': clean_text(data.get('title', ''))[:255] if data.get('title') else None,
            'description': clean_text(final_description) if final_description else None,
            'short_description': clean_text(final_short_description)[:65535] if final_short_description else None,
            'categories': clean_text(final_categories)[:255] if final_categories else None,
            'subcategories': clean_text(final_subcategories)[:255] if final_subcategories else None,
            'image': data.get('image', '')[:500] if data.get('image') else None,
            'url': data.get('product_url', '')[:500] if data.get('product_url') else None,
            'brand': clean_brand_name(data.get('brand', ''))[:100] if data.get('brand') else None
        }
        
        # 🔥 CORRECTION: Utiliser le bon nom de table et les bonnes colonnes
        query = f"""
        UPDATE ps_products_comparison_V2 
        SET {site_name}_title = %s,
            {site_name}_description = %s, 
            {site_name}_short_description = %s, 
            {site_name}_categories = %s, 
            {site_name}_subcategories = %s,
            {site_name}_image = %s,
            {site_name}_url = %s,
            {site_name}_brand = %s,
            {site_name}_scraped_at = NOW(),
            {site_name}_status = 1
        WHERE id = %s
        """
        
        cursor.execute(query, (
            cleaned_data['title'],
            cleaned_data['description'],
            cleaned_data['short_description'],
            cleaned_data['categories'],
            cleaned_data['subcategories'],
            cleaned_data['image'],
            cleaned_data['url'],
            cleaned_data['brand'],
            product_id
        ))

        conn.commit()
        rows_affected = cursor.rowcount
        
        cursor.close()
        conn.close()
        
        if rows_affected > 0:
            print(f"✅ Produit {product_id} mis à jour avec succès")
            print(f"📊 Données mises à jour:")
            for key, value in cleaned_data.items():
                if value:
                    print(f"  - {key}: {str(value)[:50]}...")
            return True
        else:
            print(f"⚠️ Aucune ligne mise à jour pour le produit {product_id}")
            return False
    
    except Exception as e:
        print(f"❌ Erreur lors de la mise à jour du produit {product_id}: {e}")
        return False