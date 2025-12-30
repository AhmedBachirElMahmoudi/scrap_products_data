"""
Normalise les valeurs d'attributs pour regrouper les produits similaires
et reduire le nombre de termes dans les filtres.
"""
import re
from database import connect_wp_ozar0

WP_PREFIX = "9Ew5q6v_"

def normalize_processor(value):
    """
    Simplifie le processeur a sa categorie principale uniquement.
    Ex: "Intel Core i5-13420H..." -> "Intel Core i5"
    """
    if not value:
        return value
        
    lv = value.lower()
    # Remove trademark symbols/artifacts that interfere with regex
    lv = re.sub(r'[®™]', '', lv)
    lv = re.sub(r'\s+', ' ', lv).strip()
    
    # 1. Intel Core iX
    if re.search(r'i3', lv): return "Intel Core i3"
    if re.search(r'i5', lv): return "Intel Core i5"
    if re.search(r'i7', lv): return "Intel Core i7"
    if re.search(r'i9', lv): return "Intel Core i9"
    
    # 2. Intel Core Ultra
    if re.search(r'ultra\s*5|core\s*5', lv): return "Intel Core Ultra 5"
    if re.search(r'ultra\s*7|core\s*7', lv): return "Intel Core Ultra 7"
    if re.search(r'ultra\s*9|core\s*9', lv): return "Intel Core Ultra 9"
    
    # 3. AMD Ryzen
    if re.search(r'ryzen\s*3', lv): return "AMD Ryzen 3"
    if re.search(r'ryzen\s*5', lv): return "AMD Ryzen 5"
    if re.search(r'ryzen\s*7', lv): return "AMD Ryzen 7"
    if re.search(r'ryzen\s*9', lv): return "AMD Ryzen 9"
    
    # 4. Autres categories communes
    if 'celeron' in lv: return "Intel Celeron"
    if 'xeon' in lv: return "Intel Xeon"
    if 'pentium' in lv: return "Intel Pentium"
    if 'snapdragon x plus' in lv: return "Snapdragon X Plus"
    if 'snapdragon x elite' in lv: return "Snapdragon X Elite"
    if 'snapdragon' in lv: return "Snapdragon"
    if 'apple m1' in lv: return "Apple M1"
    if 'apple m2' in lv: return "Apple M2"
    if 'apple m3' in lv: return "Apple M3"
    if 'apple m4' in lv: return "Apple M4"

    # Si rien n'est trouve, on nettoie juste un peu mais on garde l'original
    value = re.sub(r'®|™', '', value)
    value = re.sub(r'\s+', ' ', value).strip()
    return value

def normalize_ram(value):
    """
    Normalise la RAM pour garder uniquement la capacite principale.
    Accepte uniquement les tailles standards (2-128 Go).
    """
    if not value:
        return value

    # Si c'est en To/TB, ce n'est PAS de la RAM (pour ce contexte PC)
    if re.search(r'To|TB|teraoctets?', value, re.IGNORECASE):
        # On retourne une marque speciale pour suppression
        return "DELETE_ME_NOT_RAM"

    # Extraire la capacite en Go
    # Cas "1 x 16 Go"
    match = re.search(r'(\d+)\s*x\s*(\d+)\s*G[oB]?', value, re.IGNORECASE)
    total = 0
    if match:
        total = int(match.group(1)) * int(match.group(2))
    else:
        # Cas "16 Go", "16 GB", "16 G"
        match = re.search(r'(\d+)\s*G[oB]?', value, re.IGNORECASE)
        if match:
            total = int(match.group(1))
    
    if total > 0:
        # Whitelist des tailles valides pour éviter "256 Go" (SSD) ou "115 Go" (bug)
        if total in [1, 2, 3, 4, 6, 8, 10, 12, 16, 20, 24, 32, 48, 64, 96, 128]:
            return f"{total} Go"
        else:
            return "DELETE_ME_INVALID_SIZE"
    
    return "DELETE_ME_NO_MATCH"

def normalize_storage(value):
    """
    Normalise le stockage.
    
    Exemples:
    - "SSD 512 Go" -> "512 Go SSD"
    - "1TB SSD NVMe" -> "1 To SSD"
    """
    # Extraire la capacite
    match = re.search(r'(\d+)\s*(Go|GB|To|TB)', value, re.IGNORECASE)
    if not match:
        return value
    
    capacity = match.group(1)
    raw_unit = match.group(2).upper()
    
    # Normaliser l'unite
    if raw_unit in ['GB', 'GO']:
        unit = 'Go'
    elif raw_unit in ['TB', 'TO']:
        unit = 'To'
    else:
        unit = raw_unit.capitalize() # Fallback, though regex restricts to explicit list
    
    return f"{capacity} {unit}"

def normalize_screen(value):
    """
    Normalise la taille d'ecran.
    
    Exemples:
    - "16,0 pouces non-tactile FHD+" -> "16 pouces"
    - "15.6 inch Full HD" -> "15.6 pouces"
    - "14\" HD" -> "14 pouces"
    - "15,6" -> "15.6 pouces"
    """
    if not value:
        return value
        
    # Exclure les affichages de lignes (ex: imprimantes "LCD 2 lignes")
    if re.search(r'\b(lignes?|lines?)\b', value, re.IGNORECASE):
        return value

    # Nettoyer les caracteres bizarres
    value = value.replace('?', '').strip()
    
    # Extraire la taille (nombre decimal ou entier)
    # Cherche un nombre qui est soit suivi d'une unite, soit seul
    match = re.search(r'(\d+[,\.]\d+|\d+)', value)
    if not match:
        return value
    
    size = match.group(1).replace(',', '.')
    
    # Enlever le .0 inutile (ex: 14.0 -> 14)
    if size.endswith('.0'):
        size = size[:-2]
    
    # On pourrait ajouter Full HD/4K ici si on veut, mais garder simple semble mieux pour les filtres
    return f"{size} pouces"

def normalize_os(value):
    """
    Normalise le systeme d'exploitation.
    """
    if not value:
        return value
        
    lv = value.lower()
    
    if 'freedos' in lv: 
        return "FreeDOS"
    if 'ubuntu' in lv: 
        return "Ubuntu"
    
    # Windows 11
    if '11' in lv:
        if 'pro' in lv or 'professionnel' in lv:
            return "Windows 11 Pro"
        if 'home' in lv or 'famille' in lv or 'familiale' in lv:
            return "Windows 11 Home"
        return "Windows 11"
        
    # Windows 10
    if '10' in lv:
        if 'pro' in lv or 'professionnel' in lv:
            return "Windows 10 Pro"
        if 'home' in lv or 'famille' in lv or 'familiale' in lv:
            return "Windows 10 Home"
        return "Windows 10"
        
    if 'windows' in lv:
        return "Windows"
        
    return value

def delete_erroneous_terms(conn, cursor):
    """Supprime les termes qui sont en fait des entetes de colonnes d'import."""
    terms_to_delete = [
        "Modèle CPU", "Mémoire système", "Description du produit", 
        "Type de produit", "Format", "Contrôleur de stockage", 
        "Baies de disque dur", "Réseaux", "Alimentation",
        "Spécifications techniques", "Modèle de télécommande",
        "Garantie du fabricant", "Services inclus", "Poids", "Dimensions (LxPxH)"
    ]
    
    print("\n=== NETTOYAGE DES TERMES ERRONES ===")
    
    total_deleted = 0
    for term_name in terms_to_delete:
        # Trouver les IDs de ces termes dans les taxonomies d'attributs (pa_*)
        cursor.execute(f"""
            SELECT t.term_id, tt.term_taxonomy_id, tt.taxonomy
            FROM {WP_PREFIX}terms t
            JOIN {WP_PREFIX}term_taxonomy tt ON t.term_id = tt.term_id
            WHERE t.name = %s AND tt.taxonomy LIKE 'pa_%%'
        """, (term_name,))
        
        to_del = cursor.fetchall()
        for item in to_del:
            term_id = item['term_id']
            tt_id = item['term_taxonomy_id']
            tax = item['taxonomy']
            
            print(f"  Suppression de '{term_name}' dans {tax}...")
            
            # 1. Supprimer les relations
            cursor.execute(f"DELETE FROM {WP_PREFIX}term_relationships WHERE term_taxonomy_id = %s", (tt_id,))
            # 2. Supprimer la taxonomie
            cursor.execute(f"DELETE FROM {WP_PREFIX}term_taxonomy WHERE term_taxonomy_id = %s", (tt_id,))
            # 3. Supprimer le terme
            cursor.execute(f"DELETE FROM {WP_PREFIX}terms WHERE term_id = %s", (term_id,))
            
            total_deleted += 1
            
    conn.commit()
    print(f"Termes errones supprimes: {total_deleted}\n")

def normalize_attribute_value(taxonomy, value):
    """Applique la normalisation appropriee selon le type d'attribut."""
    taxonomy_lower = taxonomy.lower()
    
    if 'processeur' in taxonomy_lower or 'cpu' in taxonomy_lower:
        return normalize_processor(value)
    elif 'ram' in taxonomy_lower or 'memoire' in taxonomy_lower:
        return normalize_ram(value)
    elif 'stockage' in taxonomy_lower or 'disque' in taxonomy_lower or 'ssd' in taxonomy_lower or 'hdd' in taxonomy_lower:
        return normalize_storage(value)
    elif 'ecran' in taxonomy_lower or 'taille-decran' in taxonomy_lower:
        return normalize_screen(value)
    elif 'os' in taxonomy_lower or 'systeme' in taxonomy_lower or 'exploitation' in taxonomy_lower:
        return normalize_os(value)
    
    return value

def normalize_all_attributes():
    """Normalise tous les attributs dans la base de donnees."""
    conn = connect_wp_ozar0()
    cursor = conn.cursor(dictionary=True, buffered=True)
    cursor_inner = conn.cursor(dictionary=True, buffered=True)  # Separate cursor for inner queries
    
    try:
        # 1. Nettoyer les termes errones d'abord
        delete_erroneous_terms(conn, cursor)
        
        print("=== NORMALISATION DES ATTRIBUTS ===\n")
        
        # Trouver tous les termes d'attributs
        cursor.execute(f"""
            SELECT t.term_id, t.name, t.slug, tt.taxonomy
            FROM {WP_PREFIX}terms t
            JOIN {WP_PREFIX}term_taxonomy tt ON t.term_id = tt.term_id
            WHERE tt.taxonomy LIKE 'pa_%'
            ORDER BY tt.taxonomy, t.name
        """)
        
        terms = cursor.fetchall()
        print(f"Total termes a analyser: {len(terms)}\n")
        
        normalized_count = 0
        merge_map = {}  # Ancien term_id -> nouveau term_id
        
        for term in terms:
            original_name = term['name']
            taxonomy = term['taxonomy']
            
            # Normaliser la valeur
            normalized_name = normalize_attribute_value(taxonomy, original_name)
            
            if normalized_name != original_name:
                print(f"[{taxonomy}]")
                print(f"  Ancien: {original_name}")
                print(f"  Nouveau: {normalized_name}")
                
                if normalized_name.startswith("DELETE_ME"):
                     print(f"  -> SUPPRESSION IMMEDIATE (Terme invalide detecte)")
                     # We delete the current term
                     tt_id = None
                     # Need to fetch TT_ID if not present in 'term' dict? 'term' dict has term_id, name, slug, taxonomy.
                     # The select query was: SELECT t.term_id, t.name, t.slug, tt.taxonomy FROM ...
                     # Wait, I need tt.term_taxonomy_id for deletion. The SELECT query didn't fetch it!
                     # I must fetch it now.
                     cursor_inner.execute(f"SELECT term_taxonomy_id FROM {WP_PREFIX}term_taxonomy WHERE term_id = %s", (term['term_id'],))
                     tt_res = cursor_inner.fetchone()
                     if tt_res:
                         tt_id = tt_res['term_taxonomy_id']
                         # 1. Relations
                         cursor_inner.execute(f"DELETE FROM {WP_PREFIX}term_relationships WHERE term_taxonomy_id = %s", (tt_id,))
                         # 2. Lookup
                         cursor_inner.execute(f"DELETE FROM {WP_PREFIX}wc_product_attributes_lookup WHERE term_id = %s", (term['term_id'],))
                         # 3. Taxonomy
                         cursor_inner.execute(f"DELETE FROM {WP_PREFIX}term_taxonomy WHERE term_taxonomy_id = %s", (tt_id,))
                         # 4. Term
                         cursor_inner.execute(f"DELETE FROM {WP_PREFIX}terms WHERE term_id = %s", (term['term_id'],))
                     continue

                # Chercher si le terme normalise existe deja
                normalized_slug = normalized_name.lower().replace(' ', '-')
                normalized_slug = re.sub(r'[^a-z0-9-]', '', normalized_slug)
                
                cursor_inner.execute(f"""
                    SELECT t.term_id, tt.term_taxonomy_id
                    FROM {WP_PREFIX}terms t
                    JOIN {WP_PREFIX}term_taxonomy tt ON t.term_id = tt.term_id
                    WHERE tt.taxonomy = %s AND (t.name = %s OR t.slug = %s)
                """, (taxonomy, normalized_name, normalized_slug))
                
                existing = cursor_inner.fetchone()
                
                if existing and existing['term_id'] != term['term_id']:
                    # Le terme normalise existe deja, on va fusionner
                    print(f"  -> Fusion avec term_id={existing['term_id']}\n")
                    merge_map[term['term_id']] = existing
                elif not existing:
                    # Mettre a jour le terme existant uniquement s'il est différent
                    print(f"  -> Mise a jour du terme\n")
                    cursor_inner.execute(f"""
                        UPDATE {WP_PREFIX}terms
                        SET name = %s, slug = %s
                        WHERE term_id = %s
                    """, (normalized_name, normalized_slug, term['term_id']))
                
                normalized_count += 1
        
        # Effectuer les fusions
        if merge_map:
            print(f"\n=== FUSION DE {len(merge_map)} TERMES ===\n")
            
            for old_term_id, new_term_info in merge_map.items():
                new_term_id = new_term_info['term_id']
                new_tt_id = new_term_info['term_taxonomy_id']
                
                # Get old term_taxonomy_id
                cursor_inner.execute(f"""
                    SELECT term_taxonomy_id FROM {WP_PREFIX}term_taxonomy
                    WHERE term_id = %s
                """, (old_term_id,))
                old_tt_result = cursor_inner.fetchone()
                
                if old_tt_result:
                    old_tt_id = old_tt_result['term_taxonomy_id']
                    
                    # First, delete relationships where the object already has the new term
                    # (to avoid duplicate PRIMARY key conflicts)
                    # Use DELETE with JOIN to avoid MySQL subquery limitations
                    cursor_inner.execute(f"""
                        DELETE tr1 FROM {WP_PREFIX}term_relationships tr1
                        INNER JOIN {WP_PREFIX}term_relationships tr2
                        ON tr1.object_id = tr2.object_id
                        WHERE tr1.term_taxonomy_id = %s
                        AND tr2.term_taxonomy_id = %s
                    """, (old_tt_id, new_tt_id))
                    
                    # Now update the remaining relationships from old to new term
                    cursor_inner.execute(f"""
                        UPDATE {WP_PREFIX}term_relationships
                        SET term_taxonomy_id = %s
                        WHERE term_taxonomy_id = %s
                    """, (new_tt_id, old_tt_id))
                
                print(f"  Fusionne term_id {old_term_id} -> {new_term_id}")
                
                # Supprimer l'ancien terme
                cursor_inner.execute(f"DELETE FROM {WP_PREFIX}term_taxonomy WHERE term_id = %s", (old_term_id,))
                cursor_inner.execute(f"DELETE FROM {WP_PREFIX}terms WHERE term_id = %s", (old_term_id,))
        
        conn.commit()
        
        print(f"\n=== TERMINE ===")
        print(f"Termes normalises: {normalized_count}")
        print(f"Termes fusionnes: {len(merge_map)}")
        print("\nPROCHAINE ETAPE: Executer recalculate_term_counts() et fix_lookup_table()")
        
    except Exception as e:
        print(f"Erreur: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
    finally:
        cursor.close()
        cursor_inner.close()
        conn.close()

if __name__ == "__main__":
    normalize_all_attributes()
