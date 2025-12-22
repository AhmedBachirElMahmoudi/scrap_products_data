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
    """Trouve ou cr'ee un terme de taxonomie et retourne son term_taxonomy_id."""
    slug = name.lower().replace(" ", "-").replace("'", "-")
    slug = re.sub(r'[^a-z0-9-]', '', slug)
    
    # 1. Chercher si le terme existe
    cursor.execute(f"""
        SELECT tt.term_taxonomy_id 
        FROM {WP_PREFIX}terms t
        JOIN {WP_PREFIX}term_taxonomy tt ON t.term_id = tt.term_id
        WHERE t.name = %s AND tt.taxonomy = %s
    """, (name, taxonomy))
    
    result = cursor.fetchone()
    if result:
        return result[0]
    
    # 2. Cr'eer le terme s'il n'existe pas
    print(f"   [NEW TERM] Creating {name} in {taxonomy}...")
    cursor.execute(f"INSERT INTO {WP_PREFIX}terms (name, slug, term_group) VALUES (%s, %s, 0)", (name, slug))
    term_id = cursor.lastrowid
    
    cursor.execute(f"INSERT INTO {WP_PREFIX}term_taxonomy (term_id, taxonomy, description, parent, count) VALUES (%s, %s, '', 0, 0)", (term_id, taxonomy))
    return cursor.lastrowid

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
            
            # A. G'erer la MARQUE (pa_marque)
            if brand_id:
                # Retrouver le nom de la marque (brand_id dans source = external_id dans mapping)
                cursor_source.execute("SELECT brand_name FROM ps_brands_mapping WHERE external_id = %s OR id = %s", (brand_id, brand_id))
                brand_res = cursor_source.fetchone()
                if brand_res:
                    brand_name = brand_res['brand_name']
                    tti = get_or_create_term(cursor_wp, brand_name, 'pa_marque')

                    
                    # Lier au produit
                    cursor_wp.execute(f"REPLACE INTO {WP_PREFIX}term_relationships (object_id, term_taxonomy_id) VALUES (%s, %s)", (post_id, tti))
                    attributes_to_register['pa_marque'] = brand_name
                    print(f"   [BRAND] Linked to pa_marque: {brand_name}")

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
                        
                        tti = get_or_create_term(cursor_wp, attr_val, taxonomy)
                        
                        # Lier au produit
                        cursor_wp.execute(f"REPLACE INTO {WP_PREFIX}term_relationships (object_id, term_taxonomy_id) VALUES (%s, %s)", (post_id, tti))
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
