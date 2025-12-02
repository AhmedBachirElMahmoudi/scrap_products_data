import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from database import connect_temp_srv
import time
import re
import mysql.connector
import json
import urllib.parse  # AJOUT IMPORT POUR ENCODAGE URL

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

# Mettre à jour les poids pour refléter l'importance relative
DATA_QUALITY_WEIGHTS = {
    'title': 3.0,           # Plus important
    'description': 4.0,     # Très important
    'short_description': 2.0, 
    'attributes': 1.0,      # Bonus pour attributs
    'categories': 2.0,      # Plus important
    'subcategories': 0.5,
    'image': 2.0,           # Plus important
    'brand': 1.5,           # Nouveau poids pour la marque
}
MAX_DATA_QUALITY_SCORE = sum(DATA_QUALITY_WEIGHTS.values())

def _text_length(value):
    """Retourne la longueur du texte normalisé (HTML nettoyé)."""
    if not value:
        return 0
    text = str(value)
    if '<' in text and '>' in text:
        text = BeautifulSoup(text, 'html.parser').get_text(" ", strip=True)
    text = re.sub(r'\s+', ' ', text)
    return len(text.strip())

def calculate_data_quality_score(data):
    """Calcule un score de qualité basé sur les champs disponibles - VERSION AVEC MARQUE"""
    score = 0.0
    
    # Titre (obligatoire) - pas de score sans titre
    if not data.get('title') or len(data['title'].strip()) < 5:
        return 0.0  # Pas de titre = score 0
    
    title_length = len(data['title'].strip())
    score += DATA_QUALITY_WEIGHTS['title']
    if title_length > 20:
        score += 0.5

    # Description (très important) - pénalité si manquant
    description_length = _text_length(data.get('description'))
    if description_length >= 50:
        score += DATA_QUALITY_WEIGHTS['description']
        if description_length > 150:
            score += 1.0
        if description_length > 300:
            score += 1.0
    else:
        # Pénalité pour description manquante ou trop courte
        score -= 2.0

    # Description courte (important mais pas critique)
    short_desc_length = _text_length(data.get('short_description'))
    if short_desc_length >= 20:
        score += DATA_QUALITY_WEIGHTS['short_description']
        if short_desc_length > 50:
            score += 0.5
    else:
        # Légère pénalité pour description courte manquante
        score -= 0.5

    # Catégories (obligatoire) - pas de score sans catégories
    if not data.get('categories'):
        return 0.0  # Pas de catégories = score 0
    
    score += DATA_QUALITY_WEIGHTS['categories']
    if len(data['categories']) > 5 and ',' not in data['categories']:
        score += 0.5

    # Sous-catégories (bonus)
    if data.get('subcategories') and data['subcategories'] != data.get('categories'):
        score += DATA_QUALITY_WEIGHTS['subcategories']

    # Image (fortement recommandée) - pénalité si manquante
    if data.get('image'):
        score += DATA_QUALITY_WEIGHTS['image']
        if data['image'].startswith('http') and any(ext in data['image'].lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
            score += 0.5
    else:
        # Pénalité pour image manquante
        score -= 1.5

    # Marque (bonus)
    if data.get('brand'):
        score += DATA_QUALITY_WEIGHTS['brand']
        print(f"✅ Bonus marque: +{DATA_QUALITY_WEIGHTS['brand']} points")

    # Attributs (bonus seulement)
    if data.get('attributes'):
        try:
            attrs = json.loads(data['attributes']) if isinstance(data['attributes'], str) else data['attributes']
            if isinstance(attrs, dict) and len(attrs) > 0:
                score += DATA_QUALITY_WEIGHTS['attributes']
                if len(attrs) >= 3:
                    score += 0.5
        except:
            pass

    # Assurer que le score ne soit pas négatif
    return max(0.0, min(score, MAX_DATA_QUALITY_SCORE))

def identify_missing_critical_fields(data):
    """Identifie les champs critiques manquants ou insuffisants - VERSION STRICTE"""
    missing = []
    
    # Champs OBLIGATOIRES
    if not data.get('title') or len(data['title'].strip()) < 5:
        missing.append('title')
    
    if _text_length(data.get('description')) < 50:
        missing.append('description')
    
    if not data.get('categories'):
        missing.append('categories')
    
    # Champs FORTEMENT RECOMMANDÉS
    if _text_length(data.get('short_description')) < 20:
        missing.append('short_description')
    
    if not data.get('image'):
        missing.append('image')
    
    return missing

def _needs_improvement(field, current_value):
    """Détermine si un champ a besoin d'être amélioré"""
    if not current_value:
        return True
    
    if field in ['description', 'short_description']:
        return _text_length(current_value) < 20
    
    if field == 'title':
        return len(current_value.strip()) < 5
    
    if field == 'image':
        return not current_value.startswith('http')
    
    if field == 'brand':
        return not current_value or len(current_value.strip()) < 2
    
    return False

def _is_better_field_value(field, new_value, current_value):
    """Détermine si la nouvelle valeur est meilleure que l'actuelle"""
    if not current_value:
        return True
    
    if field in ['description', 'short_description']:
        new_length = _text_length(new_value)
        current_length = _text_length(current_value)
        return new_length > current_length and new_length < 2000
    
    if field == 'image':
        return new_value.startswith('http') and not current_value.startswith('http')
    
    if field in ['categories', 'subcategories']:
        return len(new_value) > len(current_value) and ',' not in new_value
    
    if field == 'title':
        return len(new_value.strip()) > len(current_value.strip())
    
    if field == 'brand':
        return len(new_value.strip()) > len(current_value.strip())
    
    return True

def smart_scraper(reference):
    """Scrape intelligemment depuis les sites disponibles et combine les meilleures données"""
    print(f"🎯 SCRAPING INTELLIGENT POUR: {reference}")
    print("=" * 60)
    
    scrapers = [
        ("Crenova", scraper_crenova_detaille),
        ("Duga", scraper_duga_detaille), 
        ("LinkSolutions", scraper_linksolutions_detaille),
        ("Tabtel", scraper_tabtel_detaille),
    ]
    
    all_data = []
    base_data = None
    
    # Étape 1: Prendre la première source valide comme base
    for label, scraper_func in scrapers:
        print(f"\n🔄 Tentative sur {label}...")
        data = scraper_func(reference)
        
        if not data:
            print(f"❌ {label}: aucune donnée exploitable")
            continue
        
        # Appliquer les corrections de cohérence
        if data.get('categories') and not data.get('subcategories'):
            data['subcategories'] = data['categories']
        
        if not data.get('description') and data.get('short_description'):
            data['description'] = data['short_description']
        
        score = calculate_data_quality_score(data)
        missing_fields = identify_missing_critical_fields(data)
        
        print(f"📊 {label}: score qualité {score:.1f}/{MAX_DATA_QUALITY_SCORE:.1f}")
        if missing_fields:
            print(f"⚠️  Champs manquants: {', '.join(missing_fields)}")
        else:
            print(f"✅ Données complètes!")
        
        # Afficher la marque si trouvée
        if data.get('brand'):
            print(f"🏷️  Marque trouvée: {data['brand']}")
        
        # Prendre la première source valide comme base
        if base_data is None:
            base_data = {
                'source': label,
                'data': data,
                'score': score,
                'missing_fields': missing_fields
            }
            print(f"🏁 Base de données établie depuis {label}")
            
            # Si la base a déjà toutes les données, on peut s'arrêter
            if not missing_fields:
                print(f"🎉 Données déjà complètes, arrêt des recherches")
                return base_data['data']
        
        all_data.append({
            'source': label, 
            'data': data,
            'score': score,
            'missing_fields': missing_fields
        })
        
        # Si on a une base et qu'on a testé au moins 2 sites, on peut commencer à fusionner
        if base_data and len(all_data) >= 2:
            # Vérifier si la base a encore des champs manquants
            current_missing = identify_missing_critical_fields(base_data['data'])
            if not current_missing:
                print(f"🎉 Tous les champs critiques comblés, arrêt des recherches")
                return base_data['data']
    
    if not base_data:
        print("❌ Aucune donnée trouvée sur les quatre sites")
        return None
    
    # Étape 2: Compléter les champs manquants de la base avec les autres sources
    print(f"\n🔍 Complétion des champs manquants depuis les autres sources...")
    final_data = complete_missing_fields(base_data, all_data, reference)
    
    return final_data

def complete_missing_fields(base_data, all_data, reference):
    """Complète les champs manquants de la base avec les autres sources"""
    base_source = base_data['source']
    merged_data = base_data['data'].copy()
    
    print(f"📋 Base: {base_source}")
    print(f"📝 Champs manquants initiaux: {base_data['missing_fields']}")
    
    # Liste des champs à compléter (AJOUT DE 'brand')
    fields_to_complete = ['title', 'description', 'short_description', 'categories', 'subcategories', 'image', 'attributes', 'brand']
    
    completed_fields = []
    
    for field in fields_to_complete:
        # Si le champ est manquant ou de mauvaise qualité dans la base
        if _needs_improvement(field, merged_data.get(field)):
            # Chercher une meilleure valeur dans les autres sources
            for source_info in all_data:
                if source_info['source'] == base_source:
                    continue  # Ignorer la source de base
                    
                if source_info['data'].get(field) and _is_better_field_value(field, source_info['data'][field], merged_data.get(field)):
                    merged_data[field] = source_info['data'][field]
                    completed_fields.append(field)
                    print(f"✅ {field} complété depuis {source_info['source']}")
                    break
    
    # Vérification finale de cohérence
    merged_data = ensure_data_consistency(merged_data)
    
    # Calculer le score final
    final_score = calculate_data_quality_score(merged_data)
    final_missing = identify_missing_critical_fields(merged_data)
    
    print(f"\n🏆 RÉSULTAT FINAL:")
    print(f"📊 Score: {final_score:.1f}/{MAX_DATA_QUALITY_SCORE:.1f} (base: {base_data['score']:.1f})")
    print(f"✅ Champs complétés: {completed_fields}")
    
    if final_missing:
        print(f"⚠️  Champs toujours manquants: {', '.join(final_missing)}")
    else:
        print(f"🎉 Tous les champs critiques sont maintenant complets!")
    
    return merged_data

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
           OR image IS NULL
           OR brand IS NULL
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
    """Récupère un produit spécifique par sa référence - VERSION CORRIGÉE"""
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
        
        if product:
            print(f"✅ Produit trouvé en base: ID={product[0]}, Ref='{product[1]}', Titre='{product[2]}'")
        else:
            print(f"❌ Aucun produit trouvé avec la référence '{reference}'")
            
        return product
    except Exception as e:
        print(f"❌ Erreur base de données: {e}")
        return None

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

# FONCTIONS D'EXTRACTION DE MARQUE POUR TOUS LES SITES
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
        brand = extract_brand_linksolutions(soup)  # NOUVEAU
        
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
            'attributes': None,
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
        
        # Extraire les données (AVEC MARQUE)
        title = extract_title_crenova(soup)
        description = extract_description_crenova(soup)
        short_description = extract_short_description_crenova(soup)
        categories_data = extract_categories_crenova(soup)
        image_url = extract_main_image_crenova(soup)
        brand = extract_brand_crenova(soup)  # NOUVEAU
        
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
            'attributes': None,
            'categories': categories_data.get('categories'),
            'subcategories': categories_data.get('subcategories'),
            'product_url': product_url,
            'image': image_url,
            'brand': brand  # NOUVEAU
        }
        
        return ensure_data_consistency(data)
        
    except Exception as e:
        print(f"❌ [CRENOVA] Erreur lors du scraping des détails: {e}")
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
        
        # Extraire les données (AVEC MARQUE)
        title = extract_title_duga(soup)
        description = extract_specifications_table_html_duga(soup)
        short_description = extract_short_description_html_duga(soup)
        specifications_table = extract_specifications_table_duga(soup)
        categories_data = extract_categories_duga(soup)
        image_url = extract_main_image_duga(soup)
        brand = extract_brand_duga(soup)  # NOUVEAU
        
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
            'brand': brand  # NOUVEAU
        }
        
        return ensure_data_consistency(data)
        
    except Exception as e:
        print(f"❌ [DUGA] Erreur lors du scraping des détails: {e}")
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

# 🔥 NOUVELLE FONCTION: Garantir la cohérence des données AVEC MARQUE
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

# FONCTIONS D'EXTRACTION DES TITRES CORRIGÉES
def extract_title_linksolutions(soup):
    """Extrait le titre depuis LinkSolutions - VERSION CORRIGÉE"""
    try:
        # Méthode 1: Meta title
        meta_title = soup.find('meta', property='og:title')
        if meta_title and meta_title.get('content'):
            title = meta_title.get('content').strip()
            return clean_site_names_from_title(title)
        
        # Méthode 2: Title tag
        title_tag = soup.find('title')
        if title_tag:
            title = title_tag.get_text(strip=True)
            return clean_site_names_from_title(title)
        
        # Méthode 3: h1 avec des classes communes
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
        
        return None
    except Exception as e:
        print(f"❌ Erreur extraction titre LinkSolutions: {e}")
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

def extract_title_tabtel(soup):
    """Extrait le titre du produit Tabtel - VERSION CORRIGÉE"""
    try:
        # Méthode 1: h1 avec itemprop="name"
        title_element = soup.find('h1', itemprop='name')
        if title_element:
            title = title_element.get_text(strip=True)
            # Nettoyer le titre (enlever la référence entre parenthèses si présente)
            title = re.sub(r'\s*\([^)]*\)\s*$', '', title)
            return clean_site_names_from_title(title)
        
        # Méthode 2: Fallback - chercher dans le meta title
        meta_title = soup.find('meta', property='og:title')
        if meta_title and meta_title.get('content'):
            title = meta_title.get('content').strip()
            return clean_site_names_from_title(title)
        
        print("❌ [TABTEL] Aucun titre trouvé")
        return None
    except Exception as e:
        print(f"❌ Erreur extraction titre Tabtel: {e}")
        return None

# LES AUTRES FONCTIONS D'EXTRACTION RESTENT IDENTIQUES
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
    """Extrait la description courte depuis LinkSolutions"""
    # Chercher des éléments avec peu de texte
    selectors = [
        'p.product-short-desc',
        'div.short-description',
        'p.excerpt',
        'div.product-excerpt'
    ]
    
    for selector in selectors:
        desc = soup.select_one(selector)
        if desc:
            text = desc.get_text(strip=True)
            if 20 < len(text) < 500:
                return text
    
    # Chercher le premier paragraphe significatif
    paragraphs = soup.find_all('p')
    for p in paragraphs:
        text = p.get_text(strip=True)
        if 20 < len(text) < 300 and not any(word in text.lower() for word in ['copyright', 'mentions légales', 'contact']):
            return text
    
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
    
def normalize_image_url(url, base_url):
    """Normalise l'URL de l'image"""
    if not url:
        return url
    
    if url.startswith('//'):
        return 'https:' + url
    elif url.startswith('/'):
        return base_url + url
    
    return url

def update_product_in_database(product_id, data):
    """Met à jour le produit dans la base de données avec nettoyage des caractères - AVEC MARQUE"""
    try:
        conn = connect_temp_srv()
        cursor = conn.cursor()
        
        # 🔥 CORRECTION FINALE: Assurer que subcategories n'est jamais NULL
        final_categories = data['categories']
        final_subcategories = data['subcategories']
        
        # Si pas de sous-catégories mais on a des catégories, on duplique
        if not final_subcategories and final_categories:
            final_subcategories = final_categories
            print(f"🔄 DB: Catégories dupliquées en sous-catégories: {final_categories}")
        
        # Si pas de description mais on a une description courte, on l'utilise
        final_description = data['description']
        if not final_description and data['short_description']:
            final_description = data['short_description']
            print(f"🔄 DB: Description courte utilisée comme description")
        
        # Nettoyer les données avant insertion
        cleaned_data = {
            'title': clean_text(data['title']) if data['title'] else data['title'],
            'description': clean_text(final_description) if final_description else final_description,
            'short_description': clean_text(data['short_description']) if data['short_description'] else data['short_description'],
            'attributes': clean_text(data['attributes']) if data['attributes'] else data['attributes'],
            'categories': clean_text(final_categories) if final_categories else final_categories,
            'subcategories': clean_text(final_subcategories) if final_subcategories else final_subcategories,
            'image': data['image'],
            'brand': clean_text(data['brand']) if data['brand'] else data['brand']  # NOUVEAU
        }
        
        query = """
        UPDATE ps_products_comparison 
        SET title = %s,
            description = %s, 
            short_description = %s, 
            attributes = %s, 
            categories = %s, 
            subcategories = %s,
            image = %s,
            brand = %s,  -- NOUVEAU CHAMP
            updated_at = NOW()
        WHERE id = %s
        """
        
        cursor.execute(query, (
            cleaned_data['title'],
            cleaned_data['description'],
            cleaned_data['short_description'],
            cleaned_data['attributes'],
            cleaned_data['categories'],
            cleaned_data['subcategories'],
            cleaned_data['image'],
            cleaned_data['brand'],  # NOUVEAU
            product_id
        ))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"✅ Produit {product_id} mis à jour avec succès depuis {data.get('source', 'inconnu')}")
        print(f"📄 Description: {len(cleaned_data['description']) if cleaned_data['description'] else 0} caractères")
        print(f"📋 Description courte: {len(cleaned_data['short_description']) if cleaned_data['short_description'] else 0} caractères")
        print(f"📂 Catégories: {cleaned_data['categories']}")
        print(f"📁 Sous-catégories: {cleaned_data['subcategories']}")
        print(f"🖼️  Image: {'✅' if cleaned_data['image'] else '❌'}")
        print(f"🏷️  Marque: {cleaned_data['brand'] if cleaned_data['brand'] else '❌'}")
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de la mise à jour du produit {product_id}: {e}")
        return False

def test_and_update_single_product(reference):
    """Teste ET met à jour un seul produit spécifique dans la base de données"""
    print(f"🧪 TEST ET MISE À JOUR DU PRODUIT: {reference}")
    print("=" * 60)
    
    # Récupérer le produit depuis la base
    product = get_product_by_reference(reference)
    
    if not product:
        print(f"❌ Produit {reference} non trouvé dans la base de données")
        return False
    
    product_id, db_reference, current_title = product
    print(f"🆔 ID produit: {product_id}")
    print(f"📦 Référence base: {db_reference}")
    print(f"🏷️  Titre actuel: {current_title}")
    print("-" * 50)
    
    # Scraper les données intelligemment
    scraped_data = smart_scraper(reference)
    
    if scraped_data:
        print(f"\n🎯 DONNÉES SCRAPÉES POUR {reference}:")
        print("=" * 50)
        print(f"📝 Titre: {scraped_data['title']}")
        print(f"📄 Description: {'✅' if scraped_data['description'] else '❌'}")
        print(f"📋 Description courte: {'✅' if scraped_data['short_description'] else '❌'}")
        print(f"📂 Catégories: {scraped_data['categories']}")
        print(f"📁 Sous-catégories: {scraped_data['subcategories']}")
        print(f"🖼️  Image: {'✅' if scraped_data['image'] else '❌'}")
        print(f"🏷️  Marque: {scraped_data['brand'] if scraped_data['brand'] else '❌'}")
        print(f"🌐 Source: {scraped_data.get('source', 'inconnu')}")
        
        # Mettre à jour la base de données
        print(f"\n💾 TENTATIVE DE MISE À JOUR EN BASE DE DONNÉES...")
        if update_product_in_database(product_id, scraped_data):
            print(f"🎉 PRODUIT {reference} MIS À JOUR AVEC SUCCÈS!")
            return True
        else:
            print(f"❌ ÉCHEC DE LA MISE À JOUR POUR {reference}")
            return False
    else:
        print(f"❌ Échec du scraping pour {reference}")
        return False

def main():
    """Fonction principale pour traiter tous les produits"""
    print("🚀 DÉBUT DU SCRAPING MULTI-SOURCES (CRENOVA + DUGA + LINKSOLUTIONS + TABTEL)")
    print("=" * 60)
    
    # Récupérer tous les produits avec données manquantes
    products = get_all_products_with_missing_data()
    
    if not products:
        print("✅ Aucun produit avec données manquantes trouvé")
        return
    
    print(f"📊 {len(products)} produits à traiter")
    print("=" * 60)
    
    success_count = 0
    error_count = 0
    
    for i, product in enumerate(products, 1):
        product_id, reference, title = product
        print(f"\n🎯 PRODUIT {i}/{len(products)}")
        print(f"📦 Référence: {reference}")
        print(f"🏷️  Titre: {title}")
        print(f"🆔 ID: {product_id}")
        print("-" * 50)
        
        # Scraper les données intelligemment
        scraped_data = smart_scraper(reference)
        
        if scraped_data:
            # Mettre à jour la base de données
            if update_product_in_database(product_id, scraped_data):
                success_count += 1
            else:
                error_count += 1
        else:
            error_count += 1
        
        # Pause pour éviter de surcharger les serveurs
        if i < len(products):
            print("⏳ Pause de 3 secondes...")
            time.sleep(3)
    
    print(f"\n🎉 SCRAPING TERMINÉ!")
    print(f"✅ Produits mis à jour avec succès: {success_count}")
    print(f"❌ Échecs: {error_count}")

if __name__ == "__main__":
    # Pour tester un seul produit spécifique
    references = [
        "21M7000HFE"
    ]

    for ref in references:
        test_and_update_single_product(ref)
    
    # Pour traiter tous les produits
    # main()