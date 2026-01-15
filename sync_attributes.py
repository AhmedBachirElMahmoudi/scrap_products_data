import json
import re
from database import connect_scraper, connect_wp_ozar0

# =========================================================
# CONFIGURATION
# =========================================================
WP_PREFIX = "9Ew5q6v_"

# Mapping des noms d'attributs vers les taxonomies WooCommerce existantes
ATTRIBUTE_MAPPING = {
    # Mémoire
    "mémoire ram": "ram",
    "memoire ram": "ram",
    "ram": "ram",
    "mémoire": "ram",
    
    # Stockage
    "capacité de stockage": "capacite-de-stockage",
    "capacite de stockage": "capacite-de-stockage",
    "capacité du stockage": "capacite-du-stockage",
    "stockage": "capacite-de-stockage",
    
    # Processeur
    "processeur": "processeur",
    "cpu": "processeur",
    
    # Système d'exploitation
    "système d'exploitation": "systeme-dexploitation",
    "systeme d'exploitation": "systeme-dexploitation",
    "système dexploitation": "systeme-dexploitation",
    "systeme dexploitation": "systeme-dexploitation",
    "os": "systeme-dexploitation",
    
    # Écran
    "taille de l'écran": "taille-decran",
    "taille de lecran": "taille-decran",
    "taille d'écran": "taille-decran",
    "taille decran": "taille-decran",
    "taille écran": "taille-decran",
    "écran": "taille-decran",
    
    # Résolution
    "résolution": "resolution",
    "resolution": "resolution",
    
    # Carte graphique - créer un nouvel attribut car pas d'équivalent
    # "carte graphique": "resolution",  # SUPPRIMÉ - incorrect
    
    # Écran tactile
    "écran tactile": "ecran-tactile",  # Nouveau, pas dans WC
    "ecran tactile": "ecran-tactile",
    
    # Convertible
    "convertible tablette": "convertible-tablette",  # Nouveau, pas dans WC
    "convertible": "convertible-tablette",
    
    # Disques
    "disque hdd": "disque-hdd",
    "hdd": "hdd",
    "disque ssd": "disque-ssd",
    "ssd": "ssd",
    "type de stockage": "ssd",  # Approximation
    
    # Couleur
    "couleur": "couleur",
    
    # Connectivité
    "wifi": "wifi",
    "bluetooth": "bluetooth",
    "réseau": "reseau",
    "reseau": "reseau",
    
    # Mobile
    "dual sim": "dual-sim",
    "caméra avant": "camera-avant",
    "camera avant": "camera-avant",
    "caméra arrière": "camera-arriere",
    "camera arriere": "camera-arriere",
    "réseaux mobiles": "reseaux-mobiles",
    "reseaux mobiles": "reseaux-mobiles",
    
    # Autres
    "marque": "marque",
    "format": "format",
    "taille": "taille",
    "interface": "interface",
    "garantie": "garantie",
}

# Attributs à ignorer complètement (ne pas importer dans WooCommerce)
IGNORED_ATTRIBUTES = [
    "modèle cpu", "temp", "mémoire système", "description du produit", 
    "type de produit", "format", "contrôleur de stockage", 
    "baies de disque dur", "réseaux", "alimentation", 
    "spécifications techniques", "modèle de télécommande",
    "garantie du fabricant", "services inclus", "poids", "dimensions (lxpxh)",
    "hauteur", "largeur", "profondeur", "poids du paquet", "dimensions du paquet",
    "hauteur du colis", "largeur du colis", "profondeur du colis",
    "ean", "upc", "part number", "référence constructeur", "numéro de pièce fabricant",
    "indice de réparabilité", "indice das"
]

def map_attribute_name(attr_name):
    """
    Mappe un nom d'attribut vers une taxonomie WooCommerce existante.
    Retourne le nom normalisé ou None si pas de mapping trouvé.
    """
    # Normaliser le nom (minuscules, sans accents pour la recherche)
    normalized = attr_name.lower().strip()
    
    # Chercher dans le mapping
    if normalized in ATTRIBUTE_MAPPING:
        return ATTRIBUTE_MAPPING[normalized]
    
    # Si pas trouvé, retourner None pour créer un nouveau
    return None

def phpserialize_attributes(attributes_dict):
    """
    Simule une s'erialisation PHP simplifi'ee pour WooCommerce _product_attributes.
    Format: a:N:{s:9:"pa_marque";a:6:{s:4:"name";s:9:"pa_marque";s:5:"value";s:0:"";s:8:"position";i:0;s:10:"is_visible";i:1;s:12:"is_variation";i:0;s:11:"is_taxonomy";i:1;}}
    """
    serialized = f'a:{len(attributes_dict)}:{{'
    for i, (key, value) in enumerate(attributes_dict.items()):
        # Chaque attribut est lui-m'eme un tableau de 6 propri'et'es
        serialized += f's:{len(key)}:"{key}";a:6:{{'
        serialized += f's:4:"name";s:{len(key)}:"{key}";'
        serialized += f's:5:"value";s:0:"";' # Vide car c'est une taxonomie
        serialized += f's:8:"position";i:{i};'
        serialized += f's:10:"is_visible";i:1;'
        serialized += f's:12:"is_variation";i:0;'
        serialized += f's:11:"is_taxonomy";i:1;'
        serialized += '}'
    serialized += '}'
    return serialized

def get_or_create_term(cursor, name, taxonomy):
    """
    Trouve ou crée un terme de taxonomie et retourne (term_taxonomy_id, term_id).
    Improved version to prevent duplicates.
    """
    slug = name.lower().replace(" ", "-").replace("'", "-")
    slug = re.sub(r'[^a-z0-9-]', '', slug)
    
    # IMPROVED: First check if this exact name+taxonomy combination exists
    cursor.execute(f"""
        SELECT tt.term_taxonomy_id, tt.term_id
        FROM {WP_PREFIX}term_taxonomy tt
        JOIN {WP_PREFIX}terms t ON tt.term_id = t.term_id
        WHERE t.name = %s AND tt.taxonomy = %s
        LIMIT 1
    """, (name, taxonomy))
    
    existing = cursor.fetchone()
    if existing:
        # Found existing term with this exact name in this taxonomy
        return existing[0], existing[1]
    
    # Also check by slug in case name varies slightly
    cursor.execute(f"""
        SELECT tt.term_taxonomy_id, tt.term_id
        FROM {WP_PREFIX}term_taxonomy tt
        JOIN {WP_PREFIX}terms t ON tt.term_id = t.term_id
        WHERE t.slug = %s AND tt.taxonomy = %s
        LIMIT 1
    """, (slug, taxonomy))
    
    existing_slug = cursor.fetchone()
    if existing_slug:
        # Found existing term with same slug in this taxonomy
        return existing_slug[0], existing_slug[1]
    
    # No existing term found, create new one
    # 1. Check if term exists in wp_terms (might be used in other taxonomies)
    cursor.execute(f"SELECT term_id FROM {WP_PREFIX}terms WHERE slug = %s", (slug,))
    term_res = cursor.fetchone()
    
    if term_res:
        term_id = term_res[0]
        # print(f"   [DEBUG] Reusing existing term '{name}' (ID: {term_id})")
    else:
        # Create new term
        print(f"   [NEW TERM] Creating '{name}' in terms table...")
        cursor.execute(f"INSERT INTO {WP_PREFIX}terms (name, slug, term_group) VALUES (%s, %s, 0)", (name, slug))
        term_id = cursor.lastrowid
    
    # 2. Link term to taxonomy (we already checked this doesn't exist above)
    print(f"   [NEW TAX] Linking term {term_id} to taxonomy {taxonomy}...")
    cursor.execute(f"""
        INSERT INTO {WP_PREFIX}term_taxonomy (term_id, taxonomy, description, parent, count) 
        VALUES (%s, %s, '', 0, 0)
    """, (term_id, taxonomy))
    term_taxonomy_id = cursor.lastrowid
    
    return term_taxonomy_id, term_id

def recalculate_term_counts(cursor_wp, conn_wp):
    """
    Recalcule les compteurs pour toutes les taxonomies d'attributs (pa_%).
    Ceci est crtique pour que les filtres fonctionnent.
    """
    print("\n[COUNTS] Recalculating term counts...")
    
    # Mettre à jour les compteurs basés sur les relations réelles
    query = f"""
        UPDATE {WP_PREFIX}term_taxonomy tt
        SET count = (
            SELECT COUNT(*)
            FROM {WP_PREFIX}term_relationships tr
            WHERE tr.term_taxonomy_id = tt.term_taxonomy_id
        )
        WHERE tt.taxonomy LIKE 'pa_%'
    """
    
    try:
        cursor_wp.execute(query)
        affected = cursor_wp.rowcount
        print(f"   Success! Updated counts for {affected} attribute terms.")
        conn_wp.commit()
    except Exception as e:
        print(f"   X Error updating counts: {e}")


def fix_lookup_table(cursor_wp, conn_wp):
    """
    Reconstruit la table wc_product_attributes_lookup pour tous les attributs.
    Cette table est essentielle pour que les filtres WooCommerce fonctionnent.
    """
    print("\n[LOOKUP] Rebuilding product attributes lookup table...")
    
    try:
        # 1. Vider la table de lookup pour les attributs (pa_%)
        print("   Clearing existing lookup entries...")
        cursor_wp.execute(f"DELETE FROM {WP_PREFIX}wc_product_attributes_lookup WHERE taxonomy LIKE 'pa_%'")
        
        # 2. Reconstruire à partir des relations réelles
        print("   Rebuilding from term_relationships...")
        query = f"""
            INSERT INTO {WP_PREFIX}wc_product_attributes_lookup 
            (product_id, product_or_parent_id, taxonomy, term_id, is_variation_attribute, in_stock)
            SELECT 
                tr.object_id as product_id,
                tr.object_id as product_or_parent_id,
                tt.taxonomy,
                tt.term_id,
                0 as is_variation_attribute,
                1 as in_stock
            FROM {WP_PREFIX}term_relationships tr
            JOIN {WP_PREFIX}term_taxonomy tt ON tr.term_taxonomy_id = tt.term_taxonomy_id
            WHERE tt.taxonomy LIKE 'pa_%'
            AND tr.object_id IN (
                SELECT ID FROM {WP_PREFIX}posts WHERE post_type = 'product'
            )
        """
        cursor_wp.execute(query)
        affected = cursor_wp.rowcount
        print(f"   Success! Inserted {affected} lookup entries.")
        conn_wp.commit()
    except Exception as e:
        print(f"   X Error rebuilding lookup table: {e}")
        conn_wp.rollback()


def sync_product_attributes(sku=None):
    """Synchronise les attributs d'un produit ou de tous les produits."""
    conn_source = connect_scraper()
    conn_wp = connect_wp_ozar0()
    
    cursor_source = conn_source.cursor(dictionary=True, buffered=True)
    cursor_wp = conn_wp.cursor(buffered=True)

    
    try:
        # 1. R'ecup'erer les produits de la source
        query = "SELECT reference, title, attributes, brand_id FROM ps_products_comparison"
        if sku:
            query += " WHERE reference = %s"
            cursor_source.execute(query, (sku,))
        else:
            cursor_source.execute(query)
            
        products = cursor_source.fetchall()
        print(f"Found {len(products)} products to process.")
        
        for prod in products:
            ref = prod['reference']
            title = prod['title']
            source_attrs = prod['attributes']
            brand_id = prod['brand_id']
            
            print(f"\nProcessing: {ref} - {title}")

            
            # Trouver l'ID dans WordPress
            cursor_wp.execute(f"SELECT post_id FROM {WP_PREFIX}postmeta WHERE meta_key='_sku' AND meta_value=%s", (ref,))
            wp_res = cursor_wp.fetchone()
            if not wp_res:
                print(f"   X Not found in WordPress (SKU: {ref})")
                continue
            
            post_id = wp_res[0]
            attributes_to_register = {}

            # VÉRIFICATION: Si le produit a déjà des attributs, on passe
            cursor_wp.execute(f"SELECT meta_value FROM {WP_PREFIX}postmeta WHERE post_id=%s AND meta_key='_product_attributes'", (post_id,))
            existing_attr_row = cursor_wp.fetchone()
            
            # 'a:0:{}' est le tableau vide sérialisé en PHP
            if existing_attr_row and existing_attr_row[0] and existing_attr_row[0] != 'a:0:{}':
                print(f"   [SKIP] Le produit a déjà des attributs (SKU: {ref})")
                continue
            
            # A. G'erer la MARQUE (pa_marque)
            if brand_id:
                # Retrouver le nom de la marque (brand_id dans source = external_id dans mapping)
                cursor_source.execute("SELECT brand_name FROM ps_brands_mapping WHERE external_id = %s OR id = %s", (brand_id, brand_id))
                brand_res = cursor_source.fetchone()
                if brand_res:
                    brand_name = brand_res['brand_name']
                    tti, term_id = get_or_create_term(cursor_wp, brand_name, 'pa_marque')

                    # Lier au produit
                    cursor_wp.execute(f"REPLACE INTO {WP_PREFIX}term_relationships (object_id, term_taxonomy_id) VALUES (%s, %s)", (post_id, tti))
                    
                    # Mise à jour de la table de lookup pour le filtrage
                    sql_lookup = f"""
                        REPLACE INTO {WP_PREFIX}wc_product_attributes_lookup 
                        (product_id, product_or_parent_id, taxonomy, term_id, is_variation_attribute, in_stock)
                        VALUES (%s, %s, 'pa_marque', %s, 0, 1)
                    """
                    print(f"   [DEBUG] Lookup Insert: Prod={post_id}, TermID={term_id}")
                    cursor_wp.execute(sql_lookup, (post_id, post_id, term_id))
                    
                    attributes_to_register['pa_marque'] = brand_name
                    print(f"   [BRAND] Linked to pa_marque: {brand_name}")
                    conn_wp.commit()  # Commit immédiat

            # B. G'erer les autres ATTRIBUTS (JSON)
            if source_attrs:
                try:
                    data = json.loads(source_attrs)
                    items = []
                    
                    if isinstance(data, list):
                        # Format: [{"name": "X", "value": "Y"}]
                        for item in data:
                            name = item.get('name')
                            val = item.get('value')
                            if name and val:
                                items.append((name, val))
                    elif isinstance(data, dict):
                        # Format: {"Key": "Value"}
                        for name, val in data.items():
                            if name and val:
                                items.append((name, val))
                    
                    for attr_name, attr_val in items:
                        # Ignorer les attributs indésirables
                        if attr_name.lower().strip() in IGNORED_ATTRIBUTES:
                            # print(f"   [Ignored] {attr_name}")
                            continue

                        # Essayer de mapper vers un attribut WooCommerce existant
                        mapped_name = map_attribute_name(attr_name)
                        
                        if mapped_name:
                            # Utiliser l'attribut WooCommerce existant
                            taxonomy = f"pa_{mapped_name}"
                            print(f"   [MAPPED] '{attr_name}' -> {taxonomy}")
                        else:
                            # Créer un nouveau nom normalisé
                            taxonomy = "pa_" + attr_name.lower().replace(" ", "-").replace("'", "-")
                            taxonomy = taxonomy.replace("é", "e").replace("è", "e").replace("à", "a")
                            taxonomy = taxonomy.replace("ô", "o").replace("ù", "u").replace("ï", "i")
                            taxonomy = taxonomy.replace("ê", "e").replace("â", "a").replace("û", "u")
                            taxonomy = re.sub(r'[^a-z0-9-_]', '', taxonomy)
                            print(f"   [NEW] '{attr_name}' -> {taxonomy}")
                        
                        # Troncature pour ėviter "Data too long"
                        if len(attr_val) > 190:
                            attr_val = attr_val[:190] + "..."
                        
                        tti, term_id = get_or_create_term(cursor_wp, attr_val, taxonomy)
                        
                        # Lier au produit
                        cursor_wp.execute(f"REPLACE INTO {WP_PREFIX}term_relationships (object_id, term_taxonomy_id) VALUES (%s, %s)", (post_id, tti))
                        
                        # Mise à jour de la table de lookup pour le filtrage
                        cursor_wp.execute(f"""
                            REPLACE INTO {WP_PREFIX}wc_product_attributes_lookup 
                            (product_id, product_or_parent_id, taxonomy, term_id, is_variation_attribute, in_stock)
                            VALUES (%s, %s, %s, %s, 0, 1)
                        """, (post_id, post_id, taxonomy, term_id))
                        
                        attributes_to_register[taxonomy] = attr_val
                        print(f"   [ATTR] Linked to {taxonomy}: {attr_val}")
                except Exception as e:
                    print(f"   X Error parsing attributes: {e}")


            # C. Mettre 'a jour la m'etadonn'ee _product_attributes
            if attributes_to_register:
                serialized_data = phpserialize_attributes(attributes_to_register)
                
                # V'erifier si la m'eta existe
                cursor_wp.execute(f"SELECT meta_id FROM {WP_PREFIX}postmeta WHERE post_id=%s AND meta_key='_product_attributes'", (post_id,))
                if cursor_wp.fetchone():
                    cursor_wp.execute(f"UPDATE {WP_PREFIX}postmeta SET meta_value=%s WHERE post_id=%s AND meta_key='_product_attributes'", (serialized_data, post_id))
                else:
                    cursor_wp.execute(f"INSERT INTO {WP_PREFIX}postmeta (post_id, meta_key, meta_value) VALUES (%s, '_product_attributes', %s)", (post_id, serialized_data))
                
                print(f"   [META] Updated _product_attributes ({len(attributes_to_register)} items)")

            conn_wp.commit()

        # Recalculer les compteurs globalement une fois le lot termin'e
        recalculate_term_counts(cursor_wp, conn_wp)

    finally:
        cursor_source.close()
        cursor_wp.close()
        conn_source.close()
        conn_wp.close()

if __name__ == "__main__":
    import sys
    
    # Si un SKU est fourni en argument, traiter uniquement ce produit
    # Sinon, traiter TOUS les produits
    if len(sys.argv) > 1:
        sku = sys.argv[1]
        print(f"Processing single product: {sku}\n")
        sync_product_attributes(sku)
    else:
        print("Processing ALL products...\n")
        sync_product_attributes()  # Sans argument = tous les produits
    
    print("\n[SYNC] Completed.")
