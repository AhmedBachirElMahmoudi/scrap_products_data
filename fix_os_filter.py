"""
Force la visibilite du filtre OS sur la categorie PC Portable
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import connect_wp_ozar0

# Forcer l'encodage UTF-8 pour Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

WP_PREFIX = "9Ew5q6v_"

def fix_os_filter():
    conn = connect_wp_ozar0()
    cursor = conn.cursor(dictionary=True)
    
    print("="*80)
    print("CORRECTION: Filtre OS sur PC Portable")
    print("="*80)
    
    # Étape 1: Recalculer les compteurs pour pa_systeme-dexploitation
    print("\n[1/3] Recalcul des compteurs de termes...")
    
    cursor.execute(f"""
        SELECT tt.term_taxonomy_id, COUNT(tr.object_id) as real_count
        FROM {WP_PREFIX}term_taxonomy tt
        LEFT JOIN {WP_PREFIX}term_relationships tr ON tt.term_taxonomy_id = tr.term_taxonomy_id
        LEFT JOIN {WP_PREFIX}posts p ON tr.object_id = p.ID
        WHERE tt.taxonomy = 'pa_systeme-dexploitation'
        AND (p.post_type = 'product' OR p.ID IS NULL)
        AND (p.post_status = 'publish' OR p.ID IS NULL)
        GROUP BY tt.term_taxonomy_id
    """)
    
    terms_to_update = cursor.fetchall()
    updated_count = 0
    
    for term in terms_to_update:
        cursor.execute(f"""
            UPDATE {WP_PREFIX}term_taxonomy
            SET count = %s
            WHERE term_taxonomy_id = %s
        """, (term['real_count'], term['term_taxonomy_id']))
        updated_count += 1
    
    conn.commit()
    print(f"   -> {updated_count} termes mis a jour")
    
    # Étape 2: Reconstruire la table lookup pour OS
    print("\n[2/3] Reconstruction de la table lookup...")
    
    # Supprimer les anciennes entrées OS
    cursor.execute(f"""
        DELETE l FROM {WP_PREFIX}wc_product_attributes_lookup l
        JOIN {WP_PREFIX}term_taxonomy tt ON l.term_id = tt.term_id
        WHERE tt.taxonomy = 'pa_systeme-dexploitation'
    """)
    
    deleted = cursor.rowcount
    print(f"   -> {deleted} anciennes entrees supprimees")
    
    # Réinsérer les entrées correctes
    cursor.execute(f"""
        INSERT INTO {WP_PREFIX}wc_product_attributes_lookup 
        (product_id, product_or_parent_id, taxonomy, term_id, is_variation_attribute, in_stock)
        SELECT DISTINCT
            p.ID as product_id,
            p.ID as product_or_parent_id,
            tt.taxonomy,
            tt.term_id,
            0 as is_variation_attribute,
            CASE 
                WHEN pm_stock.meta_value IS NULL OR pm_stock.meta_value = '' THEN 1
                WHEN CAST(pm_stock.meta_value AS SIGNED) > 0 THEN 1
                ELSE 0
            END as in_stock
        FROM {WP_PREFIX}posts p
        JOIN {WP_PREFIX}term_relationships tr ON p.ID = tr.object_id
        JOIN {WP_PREFIX}term_taxonomy tt ON tr.term_taxonomy_id = tt.term_taxonomy_id
        LEFT JOIN {WP_PREFIX}postmeta pm_stock ON p.ID = pm_stock.post_id AND pm_stock.meta_key = '_stock'
        WHERE p.post_type = 'product'
        AND p.post_status = 'publish'
        AND tt.taxonomy = 'pa_systeme-dexploitation'
    """)
    
    inserted = cursor.rowcount
    conn.commit()
    print(f"   -> {inserted} nouvelles entrees inserees")
    
    # Étape 3: Vérifier que l'attribut est marqué comme filtrable
    print("\n[3/3] Verification de l'attribut WooCommerce...")
    
    cursor.execute(f"""
        SELECT * FROM {WP_PREFIX}woocommerce_attribute_taxonomies
        WHERE attribute_name = 'systeme-dexploitation'
    """)
    
    attr = cursor.fetchone()
    
    if attr:
        print(f"   -> Attribut trouve: {attr['attribute_label']}")
        print(f"      Public: {attr['attribute_public']}")
        
        # S'assurer qu'il est public
        if attr['attribute_public'] == 0:
            cursor.execute(f"""
                UPDATE {WP_PREFIX}woocommerce_attribute_taxonomies
                SET attribute_public = 1
                WHERE attribute_name = 'systeme-dexploitation'
            """)
            conn.commit()
            print(f"      -> Attribut marque comme public")
    else:
        print(f"   [!] Attribut non trouve dans woocommerce_attribute_taxonomies")
        print(f"       Creation de l'attribut...")
        
        cursor.execute(f"""
            INSERT INTO {WP_PREFIX}woocommerce_attribute_taxonomies
            (attribute_name, attribute_label, attribute_type, attribute_orderby, attribute_public)
            VALUES ('systeme-dexploitation', 'Système d''exploitation', 'select', 'menu_order', 1)
        """)
        conn.commit()
        print(f"       -> Attribut cree")
    
    # Vérification finale
    print("\n" + "="*80)
    print("VERIFICATION FINALE")
    print("="*80)
    
    # Compter les produits PC Portable avec OS
    cursor.execute(f"""
        SELECT COUNT(DISTINCT p.ID) as count_with_os
        FROM {WP_PREFIX}posts p
        JOIN {WP_PREFIX}term_relationships tr_cat ON p.ID = tr_cat.object_id
        JOIN {WP_PREFIX}term_taxonomy tt_cat ON tr_cat.term_taxonomy_id = tt_cat.term_taxonomy_id
        JOIN {WP_PREFIX}term_relationships tr_os ON p.ID = tr_os.object_id
        JOIN {WP_PREFIX}term_taxonomy tt_os ON tr_os.term_taxonomy_id = tt_os.term_taxonomy_id
        WHERE tt_cat.term_id = 193
        AND tt_cat.taxonomy = 'product_cat'
        AND tt_os.taxonomy = 'pa_systeme-dexploitation'
        AND p.post_type = 'product'
        AND p.post_status = 'publish'
    """)
    
    count_with_os = cursor.fetchone()['count_with_os']
    print(f"\nProduits PC Portable avec OS: {count_with_os}")
    
    # Compter les termes avec count > 0
    cursor.execute(f"""
        SELECT COUNT(*) as terms_with_count
        FROM {WP_PREFIX}term_taxonomy
        WHERE taxonomy = 'pa_systeme-dexploitation'
        AND count > 0
    """)
    
    terms_with_count = cursor.fetchone()['terms_with_count']
    print(f"Termes OS avec count > 0: {terms_with_count}")
    
    # Compter les entrées dans lookup
    cursor.execute(f"""
        SELECT COUNT(DISTINCT product_id) as lookup_products
        FROM {WP_PREFIX}wc_product_attributes_lookup l
        JOIN {WP_PREFIX}term_taxonomy tt ON l.term_id = tt.term_id
        WHERE tt.taxonomy = 'pa_systeme-dexploitation'
    """)
    
    lookup_products = cursor.fetchone()['lookup_products']
    print(f"Produits dans lookup table: {lookup_products}")
    
    print("\n" + "="*80)
    print("TERMINÉ!")
    print("="*80)
    print("\nLe filtre 'Système d'exploitation' devrait maintenant apparaitre sur:")
    print("  https://dix.ma/ordinateur/pc-portable/")
    print("\nSi le filtre n'apparait toujours pas:")
    print("  1. Vider le cache WordPress/WooCommerce")
    print("  2. Regenerer les permaliens (Reglages > Permaliens > Enregistrer)")
    print("  3. Verifier les parametres de filtres WooCommerce")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    fix_os_filter()
