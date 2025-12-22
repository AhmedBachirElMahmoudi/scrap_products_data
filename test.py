import json
from datetime import datetime
import re
import time
import unicodedata
from database import connect_scraper, connect_wp_ozar0

def get_dix_connection():
    return connect_wp_ozar0()

def get_temp_connection():
    return connect_scraper()

def create_product_slug(cnx_dix, title, reference, max_length=100):
    """Crée un slug optimisé à partir du titre avec gestion des doublons"""
    cursor = cnx_dix.cursor()
    base_slug = sanitize_filename(title)
    
    if len(base_slug) > max_length:
        base_slug = base_slug[:max_length].rstrip('-')
    
    slug = base_slug
    i = 1
    
    while True:
        cursor.execute("SELECT COUNT(*) FROM 9Ew5q6v_posts WHERE post_name = %s AND post_type = 'product'", (slug,))
        if cursor.fetchone()[0] == 0:
            break
        
        if i == 1:
            new_slug = f"{base_slug}-{reference.lower()}"
        else:
            new_slug = f"{base_slug}-{reference.lower()}-{i}"
        
        if len(new_slug) > max_length:
            available_length = max_length - len(reference) - 10
            base_part = base_slug[:available_length].rstrip('-')
            new_slug = f"{base_part}-{reference.lower()}-{i}"
        
        slug = new_slug
        i += 1
        
        if i > 100:
            slug = reference.lower()
            break
    
    cursor.close()
    return slug

def sanitize_filename(filename):
    """Nettoie le nom de fichier pour en faire un slug valide"""
    if not filename:
        return ""
    
    filename = unicodedata.normalize('NFKD', str(filename))
    filename = filename.encode('ASCII', 'ignore').decode('ASCII')
    filename = filename.lower()
    
    replacements = {
        '+': 'plus', '&': 'and', '@': 'at', '#': 'sharp', 
        '%': 'percent', '°': 'degre'
    }
    
    for char, replacement in replacements.items():
        filename = filename.replace(char, f'-{replacement}-')
    
    filename = re.sub(r'[^\w\s-]', '', filename)
    filename = re.sub(r'[-\s]+', '-', filename)
    filename = filename.strip('-')
    
    return filename or "product"

def safe_float(value, default=0.0):
    """Convertit en float de manière sécurisée"""
    try:
        if value is None or value == '':
            return default
        return float(str(value).replace(',', '.').strip())
    except:
        return default

def safe_int(value, default=0):
    """Convertit en int de manière sécurisée"""
    try:
        if value is None or value == '':
            return default
        # Convertir en string, nettoyer et convertir en int
        return int(float(str(value).replace(',', '.').strip()))
    except:
        return default

def get_category_info(cnx_dix, category_id):
    """Récupère les informations d'une catégorie depuis WordPress"""
    cursor = cnx_dix.cursor()
    try:
        cursor.execute("""
            SELECT t.term_id, t.name, t.slug, tt.term_taxonomy_id
            FROM 9Ew5q6v_terms t
            JOIN 9Ew5q6v_term_taxonomy tt ON t.term_id = tt.term_id
            WHERE t.term_id = %s AND tt.taxonomy = 'product_cat'
        """, (category_id,))
        
        result = cursor.fetchone()
        if result:
            return {
                'term_id': result[0],
                'name': result[1],
                'slug': result[2],
                'term_taxonomy_id': result[3]
            }
        return None
    except Exception as e:
        print(f"   ⚠️ Erreur récupération catégorie {category_id}: {e}")
        return None
    finally:
        cursor.close()

def assign_product_category(cnx_dix, product_id, category_id):
    """Assigner une catégorie spécifique au produit (INSERTION SEULEMENT)"""
    cursor = cnx_dix.cursor()
    try:
        # Vérifier si la catégorie est déjà assignée
        cursor.execute("""
            SELECT COUNT(*) FROM 9Ew5q6v_term_relationships tr
            JOIN 9Ew5q6v_term_taxonomy tt ON tr.term_taxonomy_id = tt.term_taxonomy_id
            WHERE tr.object_id = %s AND tt.term_id = %s AND tt.taxonomy = 'product_cat'
        """, (product_id, category_id))
        
        if cursor.fetchone()[0] > 0:
            print(f"   ℹ️  Catégorie déjà assignée: {category_id}")
            return True
        
        category_info = get_category_info(cnx_dix, category_id)
        
        if category_info:
            cursor.execute("""
                INSERT INTO 9Ew5q6v_term_relationships (object_id, term_taxonomy_id)
                VALUES (%s, %s)
            """, (product_id, category_info['term_taxonomy_id']))
            print(f"   ✅ Catégorie assignée: {category_info['name']} (ID: {category_id})")
            return True
        else:
            print(f"   ⚠️ Catégorie ID {category_id} non trouvée dans WordPress")
            return False
    except Exception as e:
        print(f"   ⚠️ Erreur assignation catégorie {category_id}: {e}")
        return False
    finally:
        cursor.close()

def assign_default_category(cnx_dix, product_id):
    """Assigner une catégorie par défaut (INSERTION SEULEMENT)"""
    cursor = cnx_dix.cursor()
    try:
        cursor.execute("""
            SELECT term_id FROM 9Ew5q6v_terms 
            WHERE name IN ('Non classé', 'Uncategorized', 'Default', 'Général') 
            LIMIT 1
        """)
        result = cursor.fetchone()
        
        if result:
            category_id = result[0]
            cursor.execute("""
                SELECT term_taxonomy_id FROM 9Ew5q6v_term_taxonomy 
                WHERE term_id = %s AND taxonomy = 'product_cat'
            """, (category_id,))
            taxonomy_result = cursor.fetchone()
            
            if taxonomy_result:
                # Vérifier si la catégorie par défaut est déjà assignée
                cursor.execute("""
                    SELECT COUNT(*) FROM 9Ew5q6v_term_relationships 
                    WHERE object_id = %s AND term_taxonomy_id = %s
                """, (product_id, taxonomy_result[0]))
                
                if cursor.fetchone()[0] == 0:
                    cursor.execute("""
                        INSERT INTO 9Ew5q6v_term_relationships (object_id, term_taxonomy_id)
                        VALUES (%s, %s)
                    """, (product_id, taxonomy_result[0]))
                    print(f"   ✅ Catégorie par défaut assignée")
                else:
                    print(f"   ℹ️  Catégorie par défaut déjà assignée")
    except Exception as e:
        print(f"   ⚠️ Erreur assignation catégorie par défaut: {e}")
    finally:
        cursor.close()

def get_brand_external_id(cnx_temp, brand_id):
    """Récupère l'external_id d'une marque depuis ps_brands_mapping"""
    try:
        cursor = cnx_temp.cursor()
        cursor.execute("""
            SELECT external_id FROM ps_brands_mapping 
            WHERE external_id= %s
        """, (brand_id,))
        result = cursor.fetchone()
        return result[0] if result else None
    except Exception as e:
        print(f"   ⚠️ Erreur récupération external_id marque {brand_id}: {e}")
        return None
    finally:
        cursor.close()

def get_brand_term_id_by_external_id(cnx_dix, external_id):
    """Trouve le term_id WordPress correspondant à l'external_id de la marque"""
    try:
        cursor = cnx_dix.cursor()
        
        # Chercher la marque par son external_id stocké dans la meta
        cursor.execute("""
            SELECT t.term_id 
            FROM 9Ew5q6v_terms t
            JOIN 9Ew5q6v_termmeta tm ON t.term_id = tm.term_id
            WHERE tm.meta_key = 'external_id' AND tm.meta_value = %s
            AND t.term_id IN (
                SELECT term_id FROM 9Ew5q6v_term_taxonomy 
                WHERE taxonomy = 'pwb-brand'
            )
        """, (external_id,))
        
        result = cursor.fetchone()
        if result:
            return result[0]
        
        # Si pas trouvé par external_id, chercher par le nom de la marque
        conn_temp = get_temp_connection()
        if conn_temp:
            cursor_temp = conn_temp.cursor()
            cursor_temp.execute("""
                SELECT brand_name FROM ps_brands_mapping 
                WHERE external_id = %s
            """, (external_id,))
            brand_result = cursor_temp.fetchone()
            cursor_temp.close()
            conn_temp.close()
            
            if brand_result:
                brand_name = brand_result[0]
                # Chercher par nom de marque
                cursor.execute("""
                    SELECT t.term_id 
                    FROM 9Ew5q6v_terms t
                    JOIN 9Ew5q6v_term_taxonomy tt ON t.term_id = tt.term_id
                    WHERE t.name = %s AND tt.taxonomy = 'pwb-brand'
                """, (brand_name,))
                
                result = cursor.fetchone()
                if result:
                    return result[0]
        
        return None
        
    except Exception as e:
        print(f"   ⚠️ Erreur recherche marque external_id {external_id}: {e}")
        return None
    finally:
        cursor.close()

def create_brand_in_wordpress(cnx_dix, brand_id):
    """Crée une marque dans WordPress si elle n'existe pas"""
    try:
        # Récupérer les infos de la marque depuis ps_brands_mapping
        conn_temp = get_temp_connection()
        if not conn_temp:
            return None
            
        cursor_temp = conn_temp.cursor()
        cursor_temp.execute("""
            SELECT brand_name, brand_slug, external_id 
            FROM ps_brands_mapping 
            WHERE id = %s
        """, (brand_id,))
        
        brand_result = cursor_temp.fetchone()
        cursor_temp.close()
        conn_temp.close()
        
        if not brand_result:
            return None
            
        brand_name, brand_slug, external_id = brand_result
        
        cursor = cnx_dix.cursor()
        
        # Créer le terme
        cursor.execute("""
            INSERT INTO 9Ew5q6v_terms (name, slug, term_group)
            VALUES (%s, %s, 0)
        """, (brand_name, brand_slug))
        
        term_id = cursor.lastrowid
        
        # Créer la taxonomie
        cursor.execute("""
            INSERT INTO 9Ew5q6v_term_taxonomy (term_id, taxonomy, description, parent, count)
            VALUES (%s, 'pwb-brand', '', 0, 0)
        """, (term_id,))
        
        term_taxonomy_id = cursor.lastrowid
        
        # Stocker l'external_id dans termmeta
        cursor.execute("""
            INSERT INTO 9Ew5q6v_termmeta (term_id, meta_key, meta_value)
            VALUES (%s, 'external_id', %s)
        """, (term_id, external_id))
        
        cnx_dix.commit()
        print(f"   ✅ Nouvelle marque créée: {brand_name} (ID: {term_id})")
        
        return term_id
        
    except Exception as e:
        print(f"   ❌ Erreur création marque {brand_id}: {e}")
        cnx_dix.rollback()
        return None
    finally:
        cursor.close()

def assign_product_brand(cnx_dix, product_id, brand_id):
    """Assigner une marque au produit dans WordPress"""
    if not brand_id:
        return False
    
    cursor = None
    try:
        cursor = cnx_dix.cursor()
        
        # Vérifier si la marque existe déjà dans WordPress
        # La marque Canon existe avec term_id = 699
        term_id = brand_id  # Dans votre cas, le brand_id = term_id WordPress
        
        # Vérifier si cette marque existe vraiment
        cursor.execute("""
            SELECT COUNT(*) FROM 9Ew5q6v_terms t
            JOIN 9Ew5q6v_term_taxonomy tt ON t.term_id = tt.term_id
            WHERE t.term_id = %s AND tt.taxonomy = 'product_brand'
        """, (term_id,))
        
        if cursor.fetchone()[0] == 0:
            print(f"   ⚠️ Marque ID {term_id} non trouvée dans WordPress")
            return False
        
        # Vérifier si la marque est déjà assignée au produit
        cursor.execute("""
            SELECT COUNT(*) FROM 9Ew5q6v_term_relationships tr
            JOIN 9Ew5q6v_term_taxonomy tt ON tr.term_taxonomy_id = tt.term_taxonomy_id
            WHERE tr.object_id = %s AND tt.term_id = %s AND tt.taxonomy = 'product_brand'
        """, (product_id, term_id))
        
        if cursor.fetchone()[0] > 0:
            print(f"   ℹ️  Marque déjà assignée: ID {term_id}")
            return True
        
        # Récupérer le term_taxonomy_id
        cursor.execute("""
            SELECT term_taxonomy_id FROM 9Ew5q6v_term_taxonomy 
            WHERE term_id = %s AND taxonomy = 'product_brand'
        """, (term_id,))
        
        result = cursor.fetchone()
        if result:
            term_taxonomy_id = result[0]
            cursor.execute("""
                INSERT INTO 9Ew5q6v_term_relationships (object_id, term_taxonomy_id)
                VALUES (%s, %s)
            """, (product_id, term_taxonomy_id))
            
            # Récupérer le nom de la marque pour l'affichage
            cursor.execute("SELECT name FROM 9Ew5q6v_terms WHERE term_id = %s", (term_id,))
            brand_name = cursor.fetchone()
            brand_display = brand_name[0] if brand_name else f"ID {term_id}"
            
            print(f"   ✅ Marque assignée: {brand_display} (ID: {term_id})")
            return True
        else:
            print(f"   ⚠️ Terme marque ID {term_id} non trouvé dans WordPress")
            return False
            
    except Exception as e:
        print(f"   ⚠️ Erreur assignation marque {brand_id}: {e}")
        return False
    finally:
        if cursor:
            cursor.close()
              
def get_existing_products_references(cnx_dix):
    """Récupère toutes les références existantes dans WordPress en une seule requête"""
    cursor = cnx_dix.cursor()
    try:
        cursor.execute("""
            SELECT meta_value FROM 9Ew5q6v_postmeta 
            WHERE meta_key = '_sku' AND meta_value IS NOT NULL AND meta_value != ''
        """)
        references = {row[0] for row in cursor.fetchall()}
        return references
    except Exception as e:
        print(f"❌ Erreur récupération références existantes: {e}")
        return set()
    finally:
        cursor.close()

def get_product_id_by_sku(cnx_dix, reference):
    """Récupère l'ID d'un produit par son SKU"""
    cursor = cnx_dix.cursor()
    try:
        cursor.execute("""
            SELECT post_id FROM 9Ew5q6v_postmeta 
            WHERE meta_key = '_sku' AND meta_value = %s
        """, (reference,))
        result = cursor.fetchone()
        return result[0] if result else None
    except Exception as e:
        print(f"   ❌ Erreur récupération ID produit {reference}: {e}")
        return None
    finally:
        cursor.close()

def get_all_products_from_temp():
    """Récupère tous les produits COMPLETS de la base temporaire"""
    try:
        conn_temp = get_temp_connection()
        if not conn_temp:
            print("❌ Impossible de se connecter à la base temporaire")
            return []
        
        cursor_temp = conn_temp.cursor()
        
        # Vérifier si la table existe
        cursor_temp.execute("SHOW TABLES LIKE 'ps_products_comparison'")
        if not cursor_temp.fetchone():
            print("❌ Table 'ps_products_comparison' non trouvée dans la base temporaire")
            cursor_temp.close()
            conn_temp.close()
            return []
        
        cursor_temp.execute("SHOW COLUMNS FROM ps_products_comparison")
        columns = [column[0] for column in cursor_temp.fetchall()]
        
        select_fields = [
            'id', 'reference', 'title', 'description', 'short_description',
            'attributes', 'categories', 'subcategories'
        ]
        
        if 'id_category_default' in columns:
            select_fields.append('id_category_default')
        else:
            select_fields.append('NULL as id_category_default')
            
        if 'quantity' in columns:
            select_fields.append('quantity')
        else:
            select_fields.append('NULL as quantity')
            
        if 'wholesale_price' in columns:
            select_fields.append('wholesale_price')
        else:
            select_fields.append('NULL as wholesale_price')
            
        if 'price' in columns:
            select_fields.append('price')
        else:
            select_fields.append('NULL as price')
            
        # AJOUT: Inclure brand_id si la colonne existe
        if 'brand_id' in columns:
            select_fields.append('brand_id')
        else:
            select_fields.append('NULL as brand_id')
        
        # FILTRE IMPORTANT: Récupérer uniquement les produits COMPLETS
        query = f"""
        SELECT {', '.join(select_fields)}
        FROM ps_products_comparison 
        WHERE reference IS NOT NULL AND reference != ''
        AND title IS NOT NULL AND title != ''
        AND description IS NOT NULL AND description != ''
        """
        
        cursor_temp.execute(query)
        products = cursor_temp.fetchall()
        cursor_temp.close()
        conn_temp.close()
        
        print(f"📊 {len(products)} produits COMPLETS trouvés dans la base temporaire")
        return products
        
    except Exception as e:
        print(f"❌ Erreur lors de la récupération des produits: {e}")
        return []

def get_product_by_reference(reference):
    """Récupère un produit spécifique par sa référence"""
    try:
        conn_temp = get_temp_connection()
        if not conn_temp:
            return None
        
        cursor_temp = conn_temp.cursor()
        cursor_temp.execute("SHOW COLUMNS FROM ps_products_comparison")
        columns = [column[0] for column in cursor_temp.fetchall()]
        
        select_fields = [
            'id', 'reference', 'title', 'description', 'short_description',
            'attributes', 'categories', 'subcategories'
        ]
        
        if 'id_category_default' in columns:
            select_fields.append('id_category_default')
        else:
            select_fields.append('NULL as id_category_default')
            
        if 'quantity' in columns:
            select_fields.append('quantity')
        else:
            select_fields.append('NULL as quantity')
            
        if 'wholesale_price' in columns:
            select_fields.append('wholesale_price')
        else:
            select_fields.append('NULL as wholesale_price')
            
        if 'price' in columns:
            select_fields.append('price')
        else:
            select_fields.append('NULL as price')
            
        # AJOUT: Inclure brand_id si la colonne existe
        if 'brand_id' in columns:
            select_fields.append('brand_id')
        else:
            select_fields.append('NULL as brand_id')
        
        query = f"""
        SELECT {', '.join(select_fields)}
        FROM ps_products_comparison 
        WHERE reference = %s
        """
        
        cursor_temp.execute(query, (reference,))
        product = cursor_temp.fetchone()
        cursor_temp.close()
        conn_temp.close()
        
        return product
        
    except Exception as e:
        print(f"❌ Erreur récupération produit {reference}: {e}")
        return None

def analyze_products_before_sync(all_products, existing_references):
    """Analyse les produits avant la synchronisation"""
    print("\n📊 ANALYSE DES PRODUITS AVANT SYNCHRONISATION")
    print("=" * 50)
    
    total_products = len(all_products)
    new_products = 0
    existing_products = 0
    new_with_stock = 0
    new_without_stock = 0
    existing_with_stock = 0
    existing_without_stock = 0
    
    for product in all_products:
        reference = product[1]
        quantity = safe_int(product[9] if len(product) >= 10 else 0)
        
        if reference in existing_references:
            existing_products += 1
            if quantity > 0:
                existing_with_stock += 1
            else:
                existing_without_stock += 1
        else:
            new_products += 1
            if quantity > 0:
                new_with_stock += 1
            else:
                new_without_stock += 1
    
    print(f"📦 TOTAL PRODUITS: {total_products}")
    print(f"🔄 PRODUITS EXISTANTS: {existing_products}")
    print(f"   ├── 📈 Avec stock (>0): {existing_with_stock}")
    print(f"   └── 📉 Sans stock (0): {existing_without_stock}")
    print(f"🆕 NOUVEAUX PRODUITS: {new_products}")
    print(f"   ├── ✅ À insérer (stock>0): {new_with_stock}")
    print(f"   └── ⏭️  À ignorer (stock=0): {new_without_stock}")
    print("=" * 50)
    
    return {
        'total': total_products,
        'existing': existing_products,
        'new': new_products,
        'new_with_stock': new_with_stock,
        'new_without_stock': new_without_stock,
        'existing_with_stock': existing_with_stock,
        'existing_without_stock': existing_without_stock
    }

def insert_product_to_wordpress(product):
    """Insère un nouveau produit dans WordPress"""
    try:
        if len(product) >= 13:  # ← Changé à 13 pour inclure brand_id
            (temp_id, reference, title, description, short_description, 
             attributes, categories, subcategories, id_category_default, quantity, wholesale_price, price, brand_id) = product
        else:
            print(f"❌ Structure inattendue: {len(product)} champs")
            return False
        
        conn_dix = get_dix_connection()
        if not conn_dix:
            print("❌ Impossible de se connecter à la base WordPress")
            return False
        
        cursor_dix = conn_dix.cursor()
        
        # VÉRIFICATION QUANTITÉ : Ne pas insérer si quantité <= 0
        qty = safe_int(quantity, 0)
        if qty <= 0:
            print(f"   ⏭️  Produit ignoré (quantité <= 0): {qty}")
            cursor_dix.close()
            conn_dix.close()
            return False
        
        stock_status = 'instock' if qty > 0 else 'outofstock'
        stock_qty = str(qty)
        
        def clean_text(text):
            if not text: return text
            replacements = {'″': '"', '′': "'", ' ': ' ', '–': '-', '—': '-',
                        '‘': "'", ' ': "'", '“': '"', '»': '"', '…': '...',
                        '«': '"', '»': '"', '×': 'x', '÷': '/', '±': '+/-'}
            for old, new in replacements.items():
                text = text.replace(old, new)
            return text
        
        clean_title = clean_text(title) if title else f"Produit {reference}"
        clean_description = clean_text(description) if description else ''
        clean_short_description = clean_text(short_description) if short_description else ''
        
        slug = create_product_slug(conn_dix, clean_title, reference)
        
        now = datetime.now()
        now_gmt = datetime.utcnow()
        
        post_query = """
        INSERT INTO 9Ew5q6v_posts 
        (post_author, post_date, post_date_gmt, post_content, post_title, 
         post_excerpt, post_status, comment_status, ping_status, post_password,
         post_name, to_ping, pinged, post_modified, post_modified_gmt,
         post_content_filtered, post_parent, guid, menu_order, post_type,
         post_mime_type, comment_count , exclude)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        guid = f"https://dix.ma/?post_type=product&p={slug}"
        
        post_data = (
            1, now, now_gmt, clean_description, clean_title, clean_short_description,
            'publish', 'open', 'open', '', slug, '', '', now, now_gmt,
            '', 0, guid, 0, 'product', '', 0, 0
        )
        
        cursor_dix.execute(post_query, post_data)
        post_id = cursor_dix.lastrowid
        
        print(f"   ✅ Post créé - ID: {post_id}")
        print(f"   🔗 Slug: {slug}")
        
        def add_meta(post_id, meta_key, meta_value):
            cursor_dix.execute(
                "INSERT INTO 9Ew5q6v_postmeta (post_id, meta_key, meta_value) VALUES (%s, %s, %s)",
                (post_id, meta_key, str(meta_value) if meta_value is not None else '')
            )
        
        add_meta(post_id, '_sku', reference)
        
        # CORRECTION : Gestion CORRECTE des prix avec promotion
        # Dans PrestaShop :
        # - wholesale_price = prix d'achat → _wholesale_price
        # - price = prix de vente PROMO → _sale_price et _price
        
        regular_price = safe_float(wholesale_price, 0)  # ← Prix normal = wholesale_price
        sale_price = safe_float(price, regular_price)   # ← Prix promo = price
        
        # Si le prix promo est différent du prix normal, on a une promotion
        has_promotion = sale_price < regular_price and sale_price > 0
        
        if has_promotion:
            # PROMOTION : prix affiché = prix promo
            display_price = sale_price
            print(f"   🏷️  PROMOTION DÉTECTÉE: {regular_price} → {sale_price} DH")
        else:
            # PAS DE PROMOTION : prix affiché = prix normal
            display_price = regular_price
        
        add_meta(post_id, '_regular_price', str(regular_price))
        add_meta(post_id, '_price', str(display_price))
        
        # CORRECTION : TOUJOURS créer _sale_price (même vide) pour éviter les problèmes de mise à jour
        if has_promotion:
            add_meta(post_id, '_sale_price', str(sale_price))
            print(f"   ➕ Métadonnée créée: _sale_price = {sale_price} (PROMO)")
        else:
            # Créer _sale_price vide pour que les mises à jour futures fonctionnent correctement
            add_meta(post_id, '_sale_price', '')
            print(f"   ➕ Métadonnée créée: _sale_price = '' (pas de promotion)")
        
        add_meta(post_id, '_manage_stock', 'yes')
        add_meta(post_id, '_stock_status', stock_status)
        add_meta(post_id, '_stock', stock_qty)
        
        # Métadonnées WooCommerce
        add_meta(post_id, '_featured', 'no')
        add_meta(post_id, '_virtual', 'no')
        add_meta(post_id, '_downloadable', 'no')
        add_meta(post_id, '_visibility', 'visible')
        add_meta(post_id, '_sold_individually', 'no')
        add_meta(post_id, '_backorders', 'no')
        add_meta(post_id, '_product_type', 'simple')
        add_meta(post_id, '_tax_status', 'taxable')
        add_meta(post_id, '_tax_class', '')
        add_meta(post_id, '_purchase_note', '')
        add_meta(post_id, '_product_version', '8.0.0')
        add_meta(post_id, '_reviews_allowed', 'yes')
        add_meta(post_id, '_average_rating', '0')
        add_meta(post_id, '_rating_count', 'a:0:{}')
        
        # Métadonnées custom optionnelles
        if wholesale_price:
            add_meta(post_id, '_wholesale_price', str(wholesale_price))  # Prix d'achat
        
        add_meta(post_id, '_temp_product_id', temp_id)
        add_meta(post_id, '_original_category_id', id_category_default or '')
        
        # Gestion des catégories - INSERTION SEULEMENT
        if id_category_default and id_category_default != '':
            assign_product_category(conn_dix, post_id, id_category_default)
        else:
            assign_default_category(conn_dix, post_id)
        
        # AJOUT: Assigner la marque si elle existe
        if brand_id and brand_id != '':
            assign_product_brand(conn_dix, post_id, brand_id)
        
        conn_dix.commit()
        cursor_dix.close()
        conn_dix.close()
        
        print(f"   ✅ Produit inséré - SKU: {reference}")
        if has_promotion:
            print(f"   💰 Prix normal: {regular_price} DH → PROMO: {sale_price} DH | Stock: {stock_qty}")
        else:
            print(f"   💰 Prix de vente: {regular_price} DH | Stock: {stock_qty}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Erreur insertion: {e}")
        return False

def update_product_quantity_only(cnx_dix, product_id, quantity):
    """Met à jour seulement la quantité d'un produit"""
    try:
        cursor = cnx_dix.cursor()
        
        qty_int = safe_int(quantity, 0)
        stock_status = 'instock' if qty_int > 0 else 'outofstock'
        stock_qty = str(qty_int)
        
        # VÉRIFIER d'abord si les métadonnées existent
        cursor.execute("SELECT meta_id FROM 9Ew5q6v_postmeta WHERE post_id = %s AND meta_key = '_stock'", (product_id,))
        stock_exists = cursor.fetchone() is not None
        
        cursor.execute("SELECT meta_id FROM 9Ew5q6v_postmeta WHERE post_id = %s AND meta_key = '_stock_status'", (product_id,))
        status_exists = cursor.fetchone() is not None
        
        if stock_exists:
            cursor.execute("UPDATE 9Ew5q6v_postmeta SET meta_value = %s WHERE post_id = %s AND meta_key = '_stock'", (stock_qty, product_id))
        else:
            cursor.execute("INSERT INTO 9Ew5q6v_postmeta (post_id, meta_key, meta_value) VALUES (%s, '_stock', %s)", (product_id, stock_qty))
        
        if status_exists:
            cursor.execute("UPDATE 9Ew5q6v_postmeta SET meta_value = %s WHERE post_id = %s AND meta_key = '_stock_status'", (stock_status, product_id))
        else:
            cursor.execute("INSERT INTO 9Ew5q6v_postmeta (post_id, meta_key, meta_value) VALUES (%s, '_stock_status', %s)", (product_id, stock_status))
        
        cursor.execute("UPDATE 9Ew5q6v_posts SET post_modified = %s WHERE ID = %s", (datetime.now(), product_id))
        
        cnx_dix.commit()
        cursor.close()
        
        print(f"   ✅ Quantité mise à jour: {stock_qty} ({stock_status})")
        return True
        
    except Exception as e:
        print(f"   ❌ Erreur mise à jour quantité: {e}")
        return False

def update_product_complete(cnx_dix, product_id, product, quantity):
    """Met à jour complètement un produit (quantité > 0)"""
    try:
        if len(product) >= 13:  # ← Changé à 13 pour inclure brand_id
            (temp_id, reference, title, description, short_description, 
             attributes, categories, subcategories, id_category_default, quantity, wholesale_price, price, brand_id) = product
        else:
            print(f"❌ Structure inattendue: {len(product)} champs")
            return False
        
        cursor = cnx_dix.cursor()
        
        qty_int = safe_int(quantity, 0)
        stock_status = 'instock' if qty_int > 0 else 'outofstock'
        stock_qty = str(qty_int)
        
        def clean_text(text):
            if not text: return text
            replacements = {'″': '"', '′': "'", ' ': ' ', '–': '-', '—': '-',
                        '‘': "'", ' ': "'", '“': '"', '»': '"', '…': '...',
                        '«': '"', '»': '"', '×': 'x', '÷': '/', '±': '+/-'}
            for old, new in replacements.items():
                text = text.replace(old, new)
            return text
        
        clean_title = clean_text(title) if title else None
        clean_description = clean_text(description) if description else None
        clean_short_description = clean_text(short_description) if short_description else None
        
        update_fields = []
        update_data = []
        
        if clean_title:
            update_fields.append("post_title = %s")
            update_data.append(clean_title)
        
        if clean_description:
            update_fields.append("post_content = %s")
            update_data.append(clean_description)
        
        if clean_short_description:
            update_fields.append("post_excerpt = %s")
            update_data.append(clean_short_description)
        
        if update_fields:
            update_fields.append("post_modified = %s")
            update_data.append(datetime.now())
            
            update_query = f"UPDATE 9Ew5q6v_posts SET {', '.join(update_fields)} WHERE ID = %s"
            update_data.append(product_id)
            cursor.execute(update_query, update_data)
            print(f"   ✅ Post mis à jour")
        
        # CORRECTION : Gestion CORRECTE des prix avec promotion
        # Dans PrestaShop :
        # - wholesale_price = prix d'achat → _wholesale_price
        # - price = prix de vente PROMO → _sale_price et _price
        # - On doit calculer le prix régulier (wholesale_price) → _regular_price
        
        regular_price = safe_float(wholesale_price, 0)  # ← Prix normal = wholesale_price
        sale_price = safe_float(price, regular_price)   # ← Prix promo = price
        
        # Si le prix promo est différent du prix normal, on a une promotion
        has_promotion = sale_price < regular_price and sale_price > 0
        
        if has_promotion:
            # PROMOTION : prix affiché = prix promo
            display_price = sale_price
            print(f"   🏷️  PROMOTION DÉTECTÉE: {regular_price} → {sale_price} DH")
        else:
            # PAS DE PROMOTION : prix affiché = prix normal
            display_price = regular_price
            sale_price = ''  # Pas de prix promo
        
        # LISTE des métadonnées à mettre à jour
        meta_updates = [
            ('_regular_price', str(regular_price)),
            ('_price', str(display_price)),
            ('_stock', stock_qty),
            ('_stock_status', stock_status)
        ]
        
        # METTRE À JOUR les métadonnées existantes
        for meta_key, meta_value in meta_updates:
            # Vérifier si la métadonnée existe
            cursor.execute("SELECT meta_id FROM 9Ew5q6v_postmeta WHERE post_id = %s AND meta_key = %s", (product_id, meta_key))
            meta_exists = cursor.fetchone() is not None
            
            if meta_exists:
                # METTRE À JOUR la métadonnée existante
                cursor.execute("UPDATE 9Ew5q6v_postmeta SET meta_value = %s WHERE post_id = %s AND meta_key = %s", 
                             (meta_value, product_id, meta_key))
                print(f"   🔄 Métadonnée mise à jour: {meta_key} = {meta_value}")
            else:
                # CRÉER la métadonnée si elle n'existe pas
                cursor.execute("INSERT INTO 9Ew5q6v_postmeta (post_id, meta_key, meta_value) VALUES (%s, %s, %s)", 
                             (product_id, meta_key, meta_value))
                print(f"   ➕ Métadonnée créée: {meta_key} = {meta_value}")
        
        # Gestion spéciale pour _sale_price - AVEC PROMOTION
        if has_promotion:
            cursor.execute("SELECT meta_id FROM 9Ew5q6v_postmeta WHERE post_id = %s AND meta_key = '_sale_price'", (product_id,))
            sale_price_exists = cursor.fetchone() is not None
            
            if sale_price_exists:
                cursor.execute("UPDATE 9Ew5q6v_postmeta SET meta_value = %s WHERE post_id = %s AND meta_key = '_sale_price'", 
                             (str(sale_price), product_id))
                print(f"   🔄 Métadonnée mise à jour: _sale_price = {sale_price} (PROMO)")
            else:
                cursor.execute("INSERT INTO 9Ew5q6v_postmeta (post_id, meta_key, meta_value) VALUES (%s, '_sale_price', %s)", 
                             (product_id, str(sale_price)))
                print(f"   ➕ Métadonnée créée: _sale_price = {sale_price} (PROMO)")
        else:
            # Supprimer _sale_price s'il n'y a pas de promotion
            cursor.execute("DELETE FROM 9Ew5q6v_postmeta WHERE post_id = %s AND meta_key = '_sale_price'", (product_id,))
            print(f"   🗑️  Métadonnée supprimée: _sale_price (pas de promotion)")
        
        # Métadonnées supplémentaires pour tracking
        if wholesale_price:
            cursor.execute("SELECT meta_id FROM 9Ew5q6v_postmeta WHERE post_id = %s AND meta_key = '_wholesale_price'", (product_id,))
            wholesale_exists = cursor.fetchone() is not None
            
            if wholesale_exists:
                cursor.execute("UPDATE 9Ew5q6v_postmeta SET meta_value = %s WHERE post_id = %s AND meta_key = '_wholesale_price'", 
                             (str(wholesale_price), product_id))
            else:
                cursor.execute("INSERT INTO 9Ew5q6v_postmeta (post_id, meta_key, meta_value) VALUES (%s, '_wholesale_price', %s)", 
                             (product_id, str(wholesale_price)))
        
        # AJOUT: Mettre à jour la marque si elle existe
        if brand_id and brand_id != '':
            assign_product_brand(cnx_dix, product_id, brand_id)
        
        cnx_dix.commit()
        cursor.close()
        
        print(f"   ✅ Produit complètement mis à jour - SKU: {reference}")
        if has_promotion:
            print(f"   💰 Prix normal: {regular_price} DH → PROMO: {sale_price} DH | Stock: {stock_qty}")
        else:
            print(f"   💰 Prix de vente: {regular_price} DH | Stock: {stock_qty}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Erreur mise à jour complète: {e}")
        return False

def process_updates(all_products, existing_references, conn_dix):
    """Traite toutes les MISE À JOUR des produits existants"""
    print("\n🔄 PHASE 1: MISE À JOUR DES PRODUITS EXISTANTS")
    print("=" * 50)
    
    updated_complete_count = 0
    updated_quantity_only_count = 0
    error_count = 0
    
    # Filtrer seulement les produits existants
    existing_products = [p for p in all_products if p[1] in existing_references]
    
    print(f"📦 {len(existing_products)} produits existants à mettre à jour")
    
    for i, product in enumerate(existing_products, 1):
        reference = product[1]
        quantity = product[9] if len(product) >= 10 else 0
        qty = safe_int(quantity, 0)
        
        print(f"\n🔄 [{i}/{len(existing_products)}] Mise à jour: {reference} (Stock: {qty})")
        
        product_id = get_product_id_by_sku(conn_dix, reference)
        if product_id:
            if qty <= 0:
                # Mise à jour PARTIELLE : seulement quantité
                if update_product_quantity_only(conn_dix, product_id, qty):
                    updated_quantity_only_count += 1
                    print(f"   ✅ Mise à jour quantité seulement")
                else:
                    error_count += 1
                    print(f"   ❌ Erreur mise à jour quantité")
            else:
                # Mise à jour COMPLÈTE
                if update_product_complete(conn_dix, product_id, product, qty):
                    updated_complete_count += 1
                    print(f"   ✅ Mise à jour complète réussie")
                else:
                    error_count += 1
                    print(f"   ❌ Erreur mise à jour complète")
        else:
            error_count += 1
            print(f"   ❌ ID produit non trouvé pour {reference}")
        
        # Petite pause pour éviter la surcharge
        if i < len(existing_products) and i % 50 == 0:
            print(f"⏳ Pause après {i} mises à jour...")
            time.sleep(1)
    
    return {
        'updated_complete': updated_complete_count,
        'updated_quantity_only': updated_quantity_only_count,
        'errors': error_count
    }

def process_insertions(all_products, existing_references):
    """Traite toutes les INSERTIONS des nouveaux produits"""
    print("\n🆕 PHASE 2: INSERTION DES NOUVEAUX PRODUITS")
    print("=" * 50)
    
    inserted_count = 0
    skipped_count = 0
    error_count = 0
    
    # Filtrer seulement les nouveaux produits avec stock > 0
    new_products = [p for p in all_products if p[1] not in existing_references and safe_int(p[9] if len(p) >= 10 else 0) > 0]
    
    print(f"📦 {len(new_products)} nouveaux produits à insérer")
    
    for i, product in enumerate(new_products, 1):
        reference = product[1]
        quantity = product[9] if len(product) >= 10 else 0
        qty = safe_int(quantity, 0)
        
        print(f"\n🆕 [{i}/{len(new_products)}] Insertion: {reference} (Stock: {qty})")
        
        if insert_product_to_wordpress(product):
            inserted_count += 1
            print(f"   ✅ Nouveau produit inséré")
        else:
            error_count += 1
            print(f"   ❌ Erreur insertion nouveau produit")
        
        # Petite pause pour éviter la surcharge
        if i < len(new_products) and i % 20 == 0:
            print(f"⏳ Pause après {i} insertions...")
            time.sleep(2)
    
    # Compter les nouveaux produits ignorés (stock = 0)
    new_ignored = [p for p in all_products if p[1] not in existing_references and safe_int(p[9] if len(p) >= 10 else 0) <= 0]
    skipped_count = len(new_ignored)
    
    return {
        'inserted': inserted_count,
        'skipped': skipped_count,
        'errors': error_count
    }

def main():
    """🚀 SYNCHRONISATION WORDPRESS - Mises à jour puis insertions"""
    print("🚀 DÉBUT DE LA SYNCHRONISATION SÉPARÉE")
    print("=" * 60)
    
    # Récupérer tous les produits COMPLETS de la base temporaire
    all_products = get_all_products_from_temp()
    if not all_products:
        print("❌ Aucun produit complet à traiter")
        return
    
    # Connexion à WordPress pour vérifications
    conn_dix = get_dix_connection()
    if not conn_dix:
        print("❌ Impossible de se connecter à la base WordPress")
        return
    
    # Récupérer toutes les références existantes en UNE SEULE requête
    print("🔄 Récupération des références existantes...")
    existing_references = get_existing_products_references(conn_dix)
    print(f"📋 {len(existing_references)} références trouvées dans WordPress")
    
    # ANALYSE avant traitement
    stats = analyze_products_before_sync(all_products, existing_references)
    
    # PHASE 1: MISE À JOUR des produits existants
    update_results = process_updates(all_products, existing_references, conn_dix)
    
    # Fermer et rouvrir la connexion pour les insertions
    conn_dix.close()
    print("\n⏳ Fermeture de la connexion pour phase d'insertion...")
    time.sleep(2)
    
    # PHASE 2: INSERTION des nouveaux produits
    insertion_results = process_insertions(all_products, existing_references)
    
    print(f"\n🎉 SYNCHRONISATION TERMINÉE!")
    print("=" * 50)
    print(f"📊 RÉSULTATS DÉTAILLÉS:")
    print(f"\n🔄 PHASE MISE À JOUR:")
    print(f"   ✅ Produits mis à jour (complète): {update_results['updated_complete']}")
    print(f"   📦 Produits mis à jour (quantité seulement): {update_results['updated_quantity_only']}")
    print(f"   ❌ Erreurs mise à jour: {update_results['errors']}")
    
    print(f"\n🆕 PHASE INSERTION:")
    print(f"   ✅ Produits insérés (nouveaux): {insertion_results['inserted']}")
    print(f"   ⏭️  Produits ignorés (nouveaux, qte<=0): {insertion_results['skipped']}")
    print(f"   ❌ Erreurs insertion: {insertion_results['errors']}")
    
    print(f"\n📈 TOTAL GÉNÉRAL:")
    total_processed = (update_results['updated_complete'] + update_results['updated_quantity_only'] + 
                      insertion_results['inserted'] + insertion_results['skipped'])
    total_errors = update_results['errors'] + insertion_results['errors']
    print(f"   📦 Total produits traités: {total_processed}")
    print(f"   ❌ Total erreurs: {total_errors}")
    print(f"   📊 Total produits source: {len(all_products)}")

def test_single_product(reference):
    """🎯 TEST MANUEL : Teste un produit spécifique par sa référence"""
    print(f"\n🎯 TEST MANUEL DU PRODUIT: {reference}")
    print("=" * 50)
    
    # Récupérer le produit depuis la base temporaire
    product = get_product_by_reference(reference)
    if not product:
        print(f"❌ Produit {reference} non trouvé dans la base temporaire")
        return False
    
    # Afficher les informations du produit
    if len(product) >= 13:
        (temp_id, reference, title, description, short_description, 
         attributes, categories, subcategories, id_category_default, quantity, wholesale_price, price, brand_id) = product
        
        print(f"📋 INFORMATIONS DU PRODUIT:")
        print(f"   📝 Titre: {title or 'N/A'}")
        print(f"   📄 Description: {len(description or '')} caractères")
        print(f"   📋 Short Description: {len(short_description or '')} caractères")
        print(f"   🏷️  Catégorie ID: {id_category_default or 'N/A'}")
        print(f"   📦 Quantité: {quantity or 'N/A'}")
        print(f"   💰 Prix wholesale: {wholesale_price or 'N/A'}")
        print(f"   🏷️  Prix vente: {price or 'N/A'}")
        print(f"   🏭 Marque ID: {brand_id or 'N/A'}")
    
    # Vérifier si le produit existe dans WordPress
    conn_dix = get_dix_connection()
    if not conn_dix:
        print("❌ Impossible de se connecter à la base WordPress")
        return False
    
    existing_references = get_existing_products_references(conn_dix)
    exists = reference in existing_references
    conn_dix.close()
    
    if exists:
        print(f"\n📊 STATUT: Produit EXISTE dans WordPress (DIX)")
        qty = safe_int(quantity, 0)
        if qty <= 0:
            print("🔄 Type: Mise à jour PARTIELLE (quantité seulement)")
            # Récupérer l'ID du produit pour la mise à jour
            conn_dix = get_dix_connection()
            product_id = get_product_id_by_sku(conn_dix, reference)
            conn_dix.close()
            if product_id:
                conn_dix = get_dix_connection()
                result = update_product_quantity_only(conn_dix, product_id, qty)
                conn_dix.close()
                return result
            else:
                print("❌ ID produit non trouvé")
                return False
        else:
            print("🔄 Type: Mise à jour COMPLÈTE")
            return update_product_in_wordpress(product)
    else:
        print(f"\n📊 STATUT: NOUVEAU produit (n'existe pas dans WordPress)")
        qty = safe_int(quantity, 0)
        if qty <= 0:
            print("❌ INSERTION IMPOSSIBLE: Quantité <= 0")
            return False
        else:
            print("✅ INSERTION POSSIBLE: Quantité > 0")
            return insert_product_to_wordpress(product)

def update_product_in_wordpress(product):
    """Met à jour un produit existant dans WordPress"""
    try:
        if len(product) >= 13:
            (temp_id, reference, title, description, short_description, 
             attributes, categories, subcategories, id_category_default, quantity, wholesale_price, price, brand_id) = product
        else:
            print(f"❌ Structure inattendue: {len(product)} champs")
            return False
        
        conn_dix = get_dix_connection()
        if not conn_dix:
            print("❌ Impossible de se connecter à la base WordPress")
            return False
        
        product_id = get_product_id_by_sku(conn_dix, reference)
        if not product_id:
            print(f"   ❌ Produit non trouvé: {reference}")
            conn_dix.close()
            return False
        
        print(f"   🔄 Mise à jour produit ID: {product_id}")
        
        qty = safe_int(quantity, 0)
        
        if qty <= 0:
            print(f"   📦 Mise à jour partielle (quantité seulement): {qty}")
            result = update_product_quantity_only(conn_dix, product_id, qty)
        else:
            print(f"   🔄 Mise à jour complète (quantité > 0): {qty}")
            result = update_product_complete(conn_dix, product_id, product, qty)
        
        conn_dix.close()
        return result
        
    except Exception as e:
        print(f"   ❌ Erreur mise à jour: {e}")
        return False

if __name__ == "__main__":
    # Exécute la synchronisation complète
    #main()
    
    # Pour tester un produit spécifique, décommentez la ligne ci-dessous :
    test_single_product("B0CG3AS")


