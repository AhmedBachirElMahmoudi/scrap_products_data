import sys
import time
from datetime import datetime
from database import connect_scraper, connect_wp_ozar0
from test import (
    get_existing_products_references, 
    get_all_products_from_temp, 
    get_product_id_by_sku, 
    assign_product_category,
    get_product_by_reference,
    safe_int
)

def clear_product_categories(cnx_dix, product_id):
    """Supprime toutes les catégories (product_cat) d'un produit."""
    cursor = cnx_dix.cursor()
    try:
        # On supprime seulement les relations de type 'product_cat'
        cursor.execute("""
            DELETE tr FROM 9Ew5q6v_term_relationships tr
            JOIN 9Ew5q6v_term_taxonomy tt ON tr.term_taxonomy_id = tt.term_taxonomy_id
            WHERE tr.object_id = %s AND tt.taxonomy = 'product_cat'
        """, (product_id,))
        cnx_dix.commit()
        return True
    except Exception as e:
        print(f"   ⚠️ Erreur lors du nettoyage des catégories pour le produit {product_id}: {e}")
        return False
    finally:
        cursor.close()

def process_single_product(product, conn_dix, i, total):
    # (id, reference, title, description, short_description, attributes, categories, subcategories, id_category_default, ...)
    reference = product[1]
    category_id = product[8] # id_category_default
    
    if not category_id:
        print(f"⏩ [{i}/{total}] {reference}: Pas de catégorie définie dans TEMP, ignoré.")
        return False

    print(f"🔄 [{i}/{total}] Traitement de {reference}...")
    
    product_id = get_product_id_by_sku(conn_dix, reference)
    
    if product_id:
        # Étape 1: Nettoyer les anciennes catégories
        if clear_product_categories(conn_dix, product_id):
            # Étape 2: Assigner la nouvelle catégorie
            if assign_product_category(conn_dix, product_id, category_id):
                conn_dix.commit()
                print(f"   ✅ Catégorie mise à jour: {category_id}")
                return True
            else:
                print(f"   ❌ Erreur assignation catégorie")
        else:
            print(f"   ❌ Erreur nettoyage catégories")
    else:
        print(f"   ⚠️ SKU {reference} non trouvé dans WordPress")
    return False

def main():
    # Vérifier si une référence est passée en argument
    target_sku = sys.argv[1] if len(sys.argv) > 1 else None

    if target_sku:
        print(f"� MISE À JOUR DE LA CATÉGORIE POUR LE PRODUIT: {target_sku}")
    else:
        print("🚀 MISE À JOUR DES CATÉGORIES (TOUS LES PRODUITS EXISTANTS)")
    print("=" * 60)
    
    # 1. Connexions
    conn_temp = connect_scraper()
    conn_dix = connect_wp_ozar0()
    
    if not conn_temp or not conn_dix:
        print("❌ Erreur de connexion aux bases de données")
        return

    try:
        if target_sku:
            # Mode produit unique
            product = get_product_by_reference(target_sku)
            if not product:
                print(f"❌ Produit {target_sku} non trouvé dans la base temporaire")
                return

            process_single_product(product, conn_dix, 1, 1)
        else:
            # Mode global
            print("🔄 Récupération des références WordPress...")
            existing_references = get_existing_products_references(conn_dix)
            
            print("🔄 Récupération des produits depuis la base temporaire...")
            all_temp_products = get_all_products_from_temp()
            
            to_update = [p for p in all_temp_products if p[1] in existing_references]
            print(f"🎯 {len(to_update)} produits à traiter\n")

            updated_count = 0
            for i, product in enumerate(to_update, 1):
                if process_single_product(product, conn_dix, i, len(to_update)):
                    updated_count += 1
                
                # Pause tous les 100 produits
                if i % 100 == 0:
                    print(f"⏳ Petite pause...")
                    time.sleep(1)
            
            print(f"\n✅ Total produits mis à jour: {updated_count}")

    finally:
        conn_temp.close()
        conn_dix.close()
        print("=" * 50)

if __name__ == "__main__":
    main()
