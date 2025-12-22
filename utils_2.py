import html
import time
import re
from bs4 import BeautifulSoup

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