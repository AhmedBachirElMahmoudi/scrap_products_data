import json
import re
from database import connect_scraper
from utils import clean_site_names_from_title, clean_text

def get_best_title(candidates, reference=None):
    """
    Sélectionne le meilleur titre parmi une liste de candidats.
    Format candidat: {'source': 'duga', 'value': 'Titre...'}
    
    Args:
        candidates: Liste de dictionnaires avec 'source' et 'value'
        reference: Référence du produit (optionnel mais recommandé)
    """
    if not candidates:
        return None
        
    best_title = None
    best_score = -1
    
    for cand in candidates:
        val = cand['value']
        if not val:
            continue
            
        score = 0
        val_clean = clean_site_names_from_title(val)
        
        # CRITÈRE PRIORITAIRE: Contient la référence (TRÈS IMPORTANT)
        if reference:
            # Vérifier si la référence est présente dans le titre (case-insensitive)
            ref_upper = reference.upper()
            val_upper = val_clean.upper()
            
            if ref_upper in val_upper:
                score += 100  # BONUS ÉNORME si la référence est présente
                print(f"[OK] Titre contient la référence '{reference}': {val_clean[:60]}...")
            else:
                # Pénalité si la référence n'est PAS dans le titre
                score -= 50
                print(f"[WARN] Titre SANS référence '{reference}': {val_clean[:60]}...")
        
        # Critère 1: Longueur (viser entre 20 et 150 chars)
        if 20 <= len(val_clean) <= 150:
            score += 50
        elif len(val_clean) > 150: # Trop long
            score += 20
        else: # Trop court
            score += 10
            
        # Critère 2: Pas de ALL CAPS (on préfère "Hp Laptop" à "HP LAPTOP")
        # Si moins de 70% de majuscules
        upper_ratio = sum(1 for c in val_clean if c.isupper()) / len(val_clean) if val_clean else 0
        if upper_ratio < 0.7:
            score += 30
            
        # Critère 3: Mots clés pertinents (optionnel, mais bon signe)
        if any(x in val_clean.lower() for x in ['pc', 'portable', 'ecran', 'imprimante', 'clavier', 'souris']):
            score += 10
            
        if score > best_score:
            best_score = score
            best_title = val_clean
            
    return best_title


def get_best_description(candidates):
    """
    Sélectionne la meilleure description (la plus riche/structurée).
    Format candidat: {'source': 'duga', 'value': '...html...'}
    """
    if not candidates:
        return None, None
        
    best_desc = None
    best_source = None
    best_score = -1
    
    for cand in candidates:
        val = cand['value']
        source = cand['source']
        if not val:
            continue
            
        score = 0
        
        # Critère 1: Longueur
        score += len(val) / 100  # 1 pt par 100 chars
        
        # Critère 2: Structure HTML (Tableaux, Listes) = Qualité Technique
        if '<table' in val:
            score += 100
        if '<ul' in val or '<li' in val:
            score += 50
        if '<h' in val: # h1, h2...
            score += 20
            
        # Critère 3: Source fiable (Bonus arbitraire si on sait qu'un site est bon)
        if source in ['duga', 'crenova', 'ultrapc']: # Exemples
            score += 10
            
        if score > best_score:
            best_score = score
            best_desc = val
            best_source = source
            
    return best_desc, best_source

def get_best_image(candidates):
    """
    Sélectionne la meilleure image.
    Priorité: Existence > Source fiable
    """
    if not candidates:
        return None
        
    # Filtrer les vides et placeholders connus
    valid_candidates = []
    for cand in candidates:
        val = cand['value']
        if val and 'no-image' not in val and 'placeholder' not in val:
            valid_candidates.append(cand)
            
    if not valid_candidates:
        return None
        
    # Pour l'instant, on prend la première valide, ou on pourrait prioriser certaines extensions/domaines
    # On pourrait aussi vérifier la résolution si on avait l'info
    
    # Prioriser Duga/Crenova/Ultrapc qui ont souvent de bonnes images
    for source in ['duga', 'crenova', 'ultrapc']:
        for cand in valid_candidates:
            if cand['source'] == source:
                return cand['value']
                
    return valid_candidates[0]['value']

def merge_data():
    conn = connect_scraper()
    if not conn:
        return
        
    cursor = conn.cursor()
    
    # 1. Récupérer les données de la table V2
    print("Reading ps_products_comparison_v2...")
    
    # On liste toutes les colonnes dynamiquement ou en dur
    sites = ['crenova', 'duga', 'linksolutions', 'tabtel', 'mies', 'rightech', 'joutech', 'ultrapc']
    
    # Constuire la requête select
    cols = ['id', 'reference']
    for site in sites:
        cols.extend([
            f"{site}_title", f"{site}_description", f"{site}_short_description",
            f"{site}_image", f"{site}_brand", f"{site}_categories", f"{site}_subcategories",
            f"{site}_attributes", f"{site}_price", f"{site}_old_price"
        ])
        
    query = f"SELECT {', '.join(cols)} FROM ps_products_comparison_v2"
    cursor.execute(query)
    rows = cursor.fetchall()
    
    print(f"Stats: {len(rows)} produits à fusionner.")
    
    count_updated = 0
    
    for row in rows:
        p_id = row[0]
        ref = row[1]
        
        # Extraire les données par champ
        titles = []
        descriptions = []
        short_descriptions = []
        images = []
        brands = []
        attributes = []
        prices = []  # NOUVEAU: pour stocker les prix
        old_prices = []  # NOUVEAU: pour stocker les anciens prix
        categories_map = {} # source -> cats
        subcategories_map = {} # source -> subcats
        
        idx = 2
        for site in sites:
            # Ordre des colonnes: title, desc, short_desc, image, brand, cats, subcats, attr, price, old_price
            t = row[idx]; idx+=1
            d = row[idx]; idx+=1
            sd = row[idx]; idx+=1
            img = row[idx]; idx+=1
            b = row[idx]; idx+=1
            c = row[idx]; idx+=1
            sc = row[idx]; idx+=1
            attr = row[idx]; idx+=1
            price = row[idx]; idx+=1  # NOUVEAU
            old_price = row[idx]; idx+=1  # NOUVEAU
            
            if t: titles.append({'source': site, 'value': t})
            if d: descriptions.append({'source': site, 'value': d})
            if sd: short_descriptions.append({'source': site, 'value': sd})
            if img: images.append({'source': site, 'value': img})
            if b: brands.append({'source': site, 'value': b})
            if attr: attributes.append({'source': site, 'value': attr})
            if price and price > 0: prices.append({'source': site, 'value': float(price)})  # NOUVEAU
            if old_price and old_price > 0: old_prices.append({'source': site, 'value': float(old_price)})  # NOUVEAU
            
            categories_map[site] = c
            subcategories_map[site] = sc
            
        # Sélection "Best of Breed"
        final_title = get_best_title(titles, reference=ref)
        final_desc, desc_source = get_best_description(descriptions)
        final_short_desc, _ = get_best_description(short_descriptions) # Re-use logic or simpler
        final_image = get_best_image(images)
        
        # Pour la marque, on prend celle de la source description ou la première dispo
        final_brand = next((x['value'] for x in brands if x['source'] == desc_source), None)
        if not final_brand and brands:
            final_brand = brands[0]['value']
            
        # Pour les attributs, on prend ceux de la source description ou la première dispo
        final_attributes = next((x['value'] for x in attributes if x['source'] == desc_source), None)
        if not final_attributes and attributes:
            final_attributes = attributes[0]['value']
            
        # Pour les catégories, on prend celles de la source description ou la première dispo
        final_cats = categories_map.get(desc_source)
        final_subcats = subcategories_map.get(desc_source)
        
        # Sources disponibles
        all_sources = [x['source'] for x in titles] # Ou autre critère de présence
        
        # Si aucune info trouvée (cas rare si scraping a marché), on skip ou on met NULL
        if not final_title and not final_desc:
            continue
        
        # NOUVEAU: Gestion des prix pour Ultra PC
        # Pour Ultra PC, on utilise le prix scrapé directement sans augmentation
        final_price = None
        final_wholesale_price = None
        final_reduction = None
        final_has_stock = 0
        final_quantity = '0'
        final_marge_inf = 0
        
        # Chercher le prix Ultra PC
        ultrapc_price_data = next((x for x in prices if x['source'] == 'ultrapc'), None)
        
        if ultrapc_price_data:
            # Pour Ultra PC: le prix scrapé est le prix de vente final (wholesale_price)
            ultrapc_price = ultrapc_price_data['value']
            
            # On utilise le prix Ultra PC tel quel, sans augmentation
            final_wholesale_price = ultrapc_price
            final_price = ultrapc_price  # Prix d'achat = prix de vente (pas de marge pour Ultra PC)
            
            # Pas de réduction/marge pour Ultra PC
            final_reduction = 0.00
            final_marge_inf = 0
            
            # Pour Ultra PC, on considère qu'il y a du stock
            final_has_stock = 1
            final_quantity = '10'  # Quantité arbitraire pour Ultra PC
            
            print(f"[ULTRAPC] {ref}: Prix={final_wholesale_price} MAD (pas d'augmentation)")
            
        # Mise à jour ou Insertion dans ps_products_comparison
        # On utilise INSERT ... ON DUPLICATE KEY UPDATE pour gérer les deux cas
        
        insert_query = """
        INSERT INTO ps_products_comparison (
            reference, title, description, short_description, image, brand, attributes, 
            categories, subcategories, best_source, all_sources, sources_count, 
            updated_at, created_at, 
            price, wholesale_price, reduction, quantity, marge_inf, has_stock
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, 
            NOW(), NOW(),
            %s, %s, %s, %s, %s, %s
        )
        ON DUPLICATE KEY UPDATE
            title = VALUES(title),
            description = VALUES(description),
            short_description = VALUES(short_description),
            image = VALUES(image),
            brand = VALUES(brand),
            attributes = VALUES(attributes),
            categories = VALUES(categories),
            subcategories = VALUES(subcategories),
            best_source = VALUES(best_source),
            all_sources = VALUES(all_sources),
            sources_count = VALUES(sources_count),
            price = IF(VALUES(price) IS NOT NULL AND VALUES(price) > 0, VALUES(price), price),
            wholesale_price = IF(VALUES(wholesale_price) IS NOT NULL AND VALUES(wholesale_price) > 0, VALUES(wholesale_price), wholesale_price),
            reduction = IF(VALUES(reduction) IS NOT NULL, VALUES(reduction), reduction),
            quantity = IF(VALUES(quantity) IS NOT NULL AND VALUES(quantity) != '0', VALUES(quantity), quantity),
            marge_inf = IF(VALUES(marge_inf) IS NOT NULL, VALUES(marge_inf), marge_inf),
            has_stock = IF(VALUES(has_stock) IS NOT NULL, VALUES(has_stock), has_stock),
            updated_at = NOW()
        """
        
        try:
            cursor.execute(insert_query, (
                ref,
                final_title,
                final_desc,
                final_short_desc,
                final_image,
                final_brand,
                final_attributes,
                final_cats,
                final_subcats,
                desc_source if desc_source else (all_sources[0] if all_sources else None),
                json.dumps(all_sources),
                len(all_sources),
                final_price,
                final_wholesale_price,
                final_reduction,
                final_quantity,
                final_marge_inf,
                final_has_stock
            ))
            count_updated += 1
            
            if count_updated % 500 == 0:
                print(f"[OK] {count_updated} produits insérés/mis à jour / {len(rows)}...")
                conn.commit()
        except Exception as e:
            print(f"[ERROR] Erreur sur {ref}: {e}")

            
    conn.commit()
    print(f"Done! Fusion terminée ! {count_updated} produits mis à jour avec la meilleure qualité.")
    cursor.close()
    conn.close()

if __name__ == "__main__":
    merge_data()
