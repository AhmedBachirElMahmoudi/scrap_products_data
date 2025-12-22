import json
import re
from database import connect_scraper, connect_wp_ozar0

# =========================================================
# CONFIGURATION
# =========================================================
WP_PREFIX = "9Ew5q6v_"

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
                    attrs_list = json.loads(source_attrs)
                    if isinstance(attrs_list, list):
                        for attr in attrs_list:
                            attr_name = attr.get('name')
                            attr_val = attr.get('value')
                            
                            if attr_name and attr_val:
                                # Nettoyer le nom pour le slug (ex: "Couleur" -> "pa_couleur")
                                taxonomy = "pa_" + attr_name.lower().replace(" ", "-").replace("'", "-")
                                taxonomy = re.sub(r'[^a-z0-9-_]', '', taxonomy)
                                
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
    # Test sur le produit sp'ecifique
    skus_to_test = ['886J1EA']

    for sku in skus_to_test:
        sync_product_attributes(sku)
    print("\n[SYNC] Completed.")
