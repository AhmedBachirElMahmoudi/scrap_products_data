"""
Diagnostic simple: Pourquoi l'attribut OS n'apparait pas sur PC Portable
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

def main():
    conn = connect_wp_ozar0()
    cursor = conn.cursor(dictionary=True)
    
    print("="*80)
    print("DIAGNOSTIC: Attribut OS - PC Portable vs PC Bureau")
    print("="*80)
    
    # Trouver les taxonomies OS
    cursor.execute(f"""
        SELECT DISTINCT taxonomy
        FROM {WP_PREFIX}term_taxonomy
        WHERE taxonomy IN ('pa_systeme-dexploitation', 'pa_os')
    """)
    
    os_taxonomies = [row['taxonomy'] for row in cursor.fetchall()]
    print(f"\nTaxonomies OS trouvees: {os_taxonomies}")
    
    if not os_taxonomies:
        print("\n[!] PROBLEME: Aucune taxonomie OS trouvee!")
        print("    Solution: Executer populate_attributes.py puis sync_attributes.py")
        cursor.close()
        conn.close()
        return
    
    # Pour chaque catégorie
    categories = [
        (193, 'PC Portable', 'pc-portable'),
        (194, 'PC Bureau', 'pc-bureau')
    ]
    
    for cat_id, cat_name, cat_slug in categories:
        print(f"\n{'='*80}")
        print(f"CATEGORIE: {cat_name}")
        print("="*80)
        
        # Compter les produits dans la catégorie
        cursor.execute(f"""
            SELECT COUNT(*) as total
            FROM {WP_PREFIX}posts p
            JOIN {WP_PREFIX}term_relationships tr ON p.ID = tr.object_id
            JOIN {WP_PREFIX}term_taxonomy tt ON tr.term_taxonomy_id = tt.term_taxonomy_id
            WHERE tt.term_id = %s
            AND tt.taxonomy = 'product_cat'
            AND p.post_type = 'product'
            AND p.post_status = 'publish'
        """, (cat_id,))
        
        total_products = cursor.fetchone()['total']
        print(f"Total produits: {total_products}")
        
        # Pour chaque taxonomie OS
        for os_tax in os_taxonomies:
            print(f"\n  Taxonomie: {os_tax}")
            print(f"  {'-'*76}")
            
            # Compter les produits avec cet attribut OS dans cette catégorie
            cursor.execute(f"""
                SELECT COUNT(DISTINCT p.ID) as count_with_os
                FROM {WP_PREFIX}posts p
                JOIN {WP_PREFIX}term_relationships tr_cat ON p.ID = tr_cat.object_id
                JOIN {WP_PREFIX}term_taxonomy tt_cat ON tr_cat.term_taxonomy_id = tt_cat.term_taxonomy_id
                JOIN {WP_PREFIX}term_relationships tr_os ON p.ID = tr_os.object_id
                JOIN {WP_PREFIX}term_taxonomy tt_os ON tr_os.term_taxonomy_id = tt_os.term_taxonomy_id
                WHERE tt_cat.term_id = %s
                AND tt_cat.taxonomy = 'product_cat'
                AND tt_os.taxonomy = %s
                AND p.post_type = 'product'
                AND p.post_status = 'publish'
            """, (cat_id, os_tax))
            
            count_with_os = cursor.fetchone()['count_with_os']
            print(f"  Produits avec attribut OS: {count_with_os}/{total_products}")
            
            # Lister les termes OS et leurs compteurs
            cursor.execute(f"""
                SELECT t.name, tt.count
                FROM {WP_PREFIX}terms t
                JOIN {WP_PREFIX}term_taxonomy tt ON t.term_id = tt.term_id
                WHERE tt.taxonomy = %s
                ORDER BY tt.count DESC
            """, (os_tax,))
            
            terms = cursor.fetchall()
            print(f"  Termes OS disponibles: {len(terms)}")
            
            terms_with_count = [t for t in terms if t['count'] > 0]
            print(f"  Termes avec count > 0: {len(terms_with_count)}")
            
            if terms_with_count:
                print(f"\n  Top 5 termes OS:")
                for term in terms_with_count[:5]:
                    print(f"    - {term['name']}: {term['count']} produits")
            else:
                print(f"\n  [!] PROBLEME: Aucun terme avec count > 0")
                print(f"      C'est pourquoi le filtre n'apparait pas!")
            
            # Vérifier la table lookup
            cursor.execute(f"""
                SELECT COUNT(DISTINCT l.product_id) as lookup_count
                FROM {WP_PREFIX}wc_product_attributes_lookup l
                JOIN {WP_PREFIX}term_taxonomy tt ON l.term_id = tt.term_id
                WHERE tt.taxonomy = %s
            """, (os_tax,))
            
            lookup_count = cursor.fetchone()['lookup_count']
            print(f"  Produits dans lookup table: {lookup_count}")
            
            if lookup_count == 0:
                print(f"  [!] PROBLEME: Table lookup vide pour {os_tax}")
    
    print(f"\n{'='*80}")
    print("RECOMMANDATIONS")
    print("="*80)
    
    # Vérifier si le problème vient des compteurs
    cursor.execute(f"""
        SELECT COUNT(*) as total_zero_count
        FROM {WP_PREFIX}term_taxonomy tt
        WHERE tt.taxonomy IN ('pa_systeme-dexploitation', 'pa_os')
        AND tt.count = 0
    """)
    
    zero_count = cursor.fetchone()['total_zero_count']
    
    if zero_count > 0:
        print(f"\n[!] {zero_count} termes OS ont un count = 0")
        print("\nSOLUTION:")
        print("  1. Executer: python sync_attributes.py")
        print("     (Cela va recalculer les compteurs et reconstruire la table lookup)")
    
    # Vérifier si les produits ont l'attribut dans _product_attributes
    cursor.execute(f"""
        SELECT COUNT(*) as count_with_attr
        FROM {WP_PREFIX}postmeta pm
        JOIN {WP_PREFIX}posts p ON pm.post_id = p.ID
        WHERE pm.meta_key = '_product_attributes'
        AND (pm.meta_value LIKE '%pa_systeme-dexploitation%' OR pm.meta_value LIKE '%pa_os%')
        AND p.post_type = 'product'
        AND p.post_status = 'publish'
    """)
    
    count_with_attr = cursor.fetchone()['count_with_attr']
    
    cursor.execute(f"""
        SELECT COUNT(*) as total_products
        FROM {WP_PREFIX}posts
        WHERE post_type = 'product'
        AND post_status = 'publish'
    """)
    
    total_products = cursor.fetchone()['total_products']
    
    print(f"\nProduits avec attribut OS dans _product_attributes: {count_with_attr}/{total_products}")
    
    if count_with_attr < total_products * 0.5:  # Moins de 50%
        print("\n[!] Beaucoup de produits n'ont pas l'attribut OS")
        print("\nSOLUTION:")
        print("  1. Executer: python populate_attributes.py")
        print("     (Cela va extraire les OS depuis les descriptions)")
        print("  2. Puis: python sync_attributes.py")
        print("     (Cela va synchroniser vers WooCommerce)")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    main()
