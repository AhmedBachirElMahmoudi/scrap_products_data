import re
from database import connect_wp_ozar0
from normalize_attributes import normalize_processor, normalize_ram, normalize_storage, normalize_screen

WP_PREFIX = "9Ew5q6v_"

def extract_attributes_from_title(title):
    attrs = {}
    
    # Processor
    if re.search(r'i[3579]-?\d{4,}', title, re.IGNORECASE):
        proc = normalize_processor(title)
        if proc and proc != title:
            attrs['pa_processeur'] = proc
    elif re.search(r'Ryzen\s*\d', title, re.IGNORECASE):
        proc = normalize_processor(title)
        if proc and proc != title:
            attrs['pa_processeur'] = proc
    elif re.search(r'Core\s*Ultra', title, re.IGNORECASE):
        proc = normalize_processor(title)
        if proc and proc != title:
            attrs['pa_processeur'] = proc
    elif re.search(r'Xeon', title, re.IGNORECASE):
        attrs['pa_processeur'] = "Intel Xeon"
            
    # RAM
    match_ram = re.search(r'(\d+\s*(?:Go|GB|G))', title, re.IGNORECASE)
    if match_ram:
        raw_ram = match_ram.group(1) 
        norm_ram = normalize_ram(raw_ram)
        if norm_ram and not norm_ram.startswith("DELETE_ME"):
            attrs['pa_ram'] = norm_ram

    # Storage
    match_storage = re.search(r'(\d+\s*(?:Go|GB|To|TB)\s*(?:SSD|HDD)?)', title, re.IGNORECASE)
    if match_storage:
        norm_storage = normalize_storage(match_storage.group(1))
        if norm_storage:
            attrs['pa_stockage'] = norm_storage
            
    # Screen
    match_screen = re.search(r'(\d+(?:[,\.]\d+)?)\s*(?:"|pouces|inch|cm)', title, re.IGNORECASE)
    if match_screen:
         raw_screen = match_screen.group(0)
         norm_screen = normalize_screen(raw_screen)
         if norm_screen:
             attrs['pa_taille-decran'] = norm_screen
             
    # Operating System (OS)
    if re.search(r'(?:Windows|Win)\s*11\s*(?:Pro|Professional|P)\b', title, re.IGNORECASE):
        attrs['pa_systeme-dexploitation'] = "Windows 11 Pro"
    elif re.search(r'(?:Windows|Win)\s*11\s*(?:Home|Famille|H)\b', title, re.IGNORECASE):
        attrs['pa_systeme-dexploitation'] = "Windows 11 Home"
    elif re.search(r'(?:Windows|Win)\s*11', title, re.IGNORECASE):
         attrs['pa_systeme-dexploitation'] = "Windows 11"
    elif re.search(r'(?:Windows|Win)\s*10\s*(?:Pro|Professional|P)\b', title, re.IGNORECASE):
        attrs['pa_systeme-dexploitation'] = "Windows 10 Pro"
    elif re.search(r'(?:Windows|Win)\s*10\s*(?:Home|Famille|H)\b', title, re.IGNORECASE):
        attrs['pa_systeme-dexploitation'] = "Windows 10 Home"
    elif re.search(r'(?:Windows|Win)\s*10', title, re.IGNORECASE):
        attrs['pa_systeme-dexploitation'] = "Windows 10"
    elif re.search(r'FreeDOS', title, re.IGNORECASE):
         attrs['pa_systeme-dexploitation'] = "FreeDOS"
    elif re.search(r'Android', title, re.IGNORECASE):
        attrs['pa_systeme-dexploitation'] = "Android"
    elif re.search(r'MacOS', title, re.IGNORECASE):
        attrs['pa_systeme-dexploitation'] = "macOS"
    elif re.search(r'Ubuntu|Linux', title, re.IGNORECASE):
        attrs['pa_systeme-dexploitation'] = "Linux"

    return attrs

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

def populate_missing_attributes(dry_run=False):
    conn = connect_wp_ozar0()
    cursor = conn.cursor(dictionary=True)
    
    print("Fetching published products...")
    # No LIMIT, get all products
    cursor.execute(f"SELECT ID, post_title FROM {WP_PREFIX}posts WHERE post_type='product' AND post_status='publish'")
    products = cursor.fetchall()
    print(f"Checking {len(products)} products attribute coverage...")
    
    updates = 0
    
    for p in products:
        pid = p['ID']
        title = p['post_title']
        
        # Check existing attributes
        cursor.execute(f"""
            SELECT tt.taxonomy
            FROM {WP_PREFIX}term_relationships tr
            JOIN {WP_PREFIX}term_taxonomy tt ON tr.term_taxonomy_id = tt.term_taxonomy_id
            WHERE tr.object_id = %s AND tt.taxonomy LIKE 'pa_%%'
        """, (pid,))
        existing_tax = {r['taxonomy'] for r in cursor.fetchall()}
        
        needed = []
        if 'pa_processeur' not in existing_tax: needed.append('pa_processeur')
        if 'pa_ram' not in existing_tax: needed.append('pa_ram')
        if 'pa_stockage' not in existing_tax: needed.append('pa_stockage')
        if 'pa_taille-decran' not in existing_tax: needed.append('pa_taille-decran')
        if 'pa_systeme-dexploitation' not in existing_tax: needed.append('pa_systeme-dexploitation')
        if 'pa_taille-decran' not in existing_tax: needed.append('pa_taille-decran')
        
        if not needed:
            continue
            
        # Extract from title
        extracted = extract_attributes_from_title(title)
        
        to_add = {}
        for tax in needed:
            if tax in extracted:
                to_add[tax] = extracted[tax]
                
        if to_add:
            print(f"\nProduct {pid}: {title}")
            print(f"  Missing: {needed}")
            print(f"  Found: {to_add}")
            
            if not dry_run:
                for tax, val in to_add.items():
                    # Check if term exists
                    slug = val.lower().replace(' ', '-')
                    slug = re.sub(r'[^a-z0-9-]', '', slug)
                    
                    # Find term_id
                    cursor.execute(f"""
                        SELECT t.term_id, tt.term_taxonomy_id
                        FROM {WP_PREFIX}terms t
                        JOIN {WP_PREFIX}term_taxonomy tt ON t.term_id = tt.term_id
                        WHERE tt.taxonomy = %s AND t.name = %s
                        LIMIT 1
                    """, (tax, val))
                    term = cursor.fetchone()
                    
                    term_id = None
                    tt_id = None
                    
                    if not term:
                        # Create term if it doesn't exist
                        print(f"    Creating new term '{val}' in {tax}...")
                        cursor.execute(f"INSERT INTO {WP_PREFIX}terms (name, slug) VALUES (%s, %s)", (val, slug))
                        term_id = cursor.lastrowid
                        cursor.execute(f"INSERT INTO {WP_PREFIX}term_taxonomy (term_id, taxonomy, description, parent, count) VALUES (%s, %s, '', 0, 0)", (term_id, tax))
                        tt_id = cursor.lastrowid
                    else:
                        term_id = term['term_id']
                        tt_id = term['term_taxonomy_id']
                        
                    # Assign relationship
                    if tt_id:
                        cursor.execute(f"""
                            INSERT IGNORE INTO {WP_PREFIX}term_relationships
                            (object_id, term_taxonomy_id, term_order)
                            VALUES (%s, %s, 0)
                        """, (pid, tt_id))
                        
                        # Update lookup table for filtering
                        cursor.execute(f"""
                            REPLACE INTO {WP_PREFIX}wc_product_attributes_lookup 
                            (product_id, product_or_parent_id, taxonomy, term_id, is_variation_attribute, in_stock)
                            VALUES (%s, %s, %s, %s, 0, 1)
                        """, (pid, pid, tax, term_id))
                        print(f"    Updated lookup table for {tax}")

                # After adding new attributes, we must update the _product_attributes meta
                # Fetch ALL attributes for this product (old + new)
                cursor.execute(f"""
                    SELECT DISTINCT tt.taxonomy
                    FROM {WP_PREFIX}term_relationships tr
                    JOIN {WP_PREFIX}term_taxonomy tt ON tr.term_taxonomy_id = tt.term_taxonomy_id
                    WHERE tr.object_id = %s AND tt.taxonomy LIKE 'pa_%%'
                """, (pid,))
                all_taxonomies = [r['taxonomy'] for r in cursor.fetchall()]
                
                # Build dict for serialization (values don't matter for taxonomy attributes, just keys)
                attr_dict = {tax: "" for tax in all_taxonomies}
                
                serialized_data = phpserialize_attributes(attr_dict)
                
                # Update or Insert meta
                cursor.execute(f"SELECT meta_id FROM {WP_PREFIX}postmeta WHERE post_id=%s AND meta_key='_product_attributes'", (pid,))
                if cursor.fetchone():
                    cursor.execute(f"UPDATE {WP_PREFIX}postmeta SET meta_value=%s WHERE post_id=%s AND meta_key='_product_attributes'", (serialized_data, pid))
                else:
                    cursor.execute(f"INSERT INTO {WP_PREFIX}postmeta (post_id, meta_key, meta_value) VALUES (%s, '_product_attributes', %s)", (pid, serialized_data))
                print(f"    Updated _product_attributes meta")

            updates += 1
            
            if updates % 50 == 0:
                conn.commit()
                print(f"Committed {updates} updates...")

    conn.commit()
    print(f"\nResult: Processed products. Found {updates} products that needed updates.")
    
    # Recalculate counts at the end
    print("Recalculating term counts...")
    cursor.execute(f"""
        UPDATE {WP_PREFIX}term_taxonomy tt
        SET count = (
            SELECT COUNT(*)
            FROM {WP_PREFIX}term_relationships tr
            WHERE tr.term_taxonomy_id = tt.term_taxonomy_id
        )
        WHERE tt.taxonomy LIKE 'pa_%%'
    """)
    conn.commit()
    print("Counts recalculated.")
    
    conn.close()

if __name__ == "__main__":
    populate_missing_attributes(dry_run=False)
