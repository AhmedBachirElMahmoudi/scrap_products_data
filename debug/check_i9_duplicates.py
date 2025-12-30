"""
Vérifie les doublons d'Intel Core i9 dans la base de données
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import connect_wp_ozar0

WP_PREFIX = "9Ew5q6v_"

def check_i9_terms():
    conn = connect_wp_ozar0()
    cursor = conn.cursor(dictionary=True)
    
    print("=== RECHERCHE DES TERMES INTEL CORE i9 ===\n")
    
    # Chercher tous les termes contenant "i9" dans les taxonomies d'attributs
    query = f"""
        SELECT 
            t.term_id,
            t.name,
            t.slug,
            tt.taxonomy,
            tt.count,
            tt.term_taxonomy_id
        FROM {WP_PREFIX}terms t
        JOIN {WP_PREFIX}term_taxonomy tt ON t.term_id = tt.term_id
        WHERE tt.taxonomy LIKE 'pa_%'
        AND (t.name LIKE '%i9%' OR t.slug LIKE '%i9%')
        ORDER BY tt.taxonomy, t.name
    """
    
    cursor.execute(query)
    results = cursor.fetchall()
    
    if results:
        print(f"Trouvé {len(results)} terme(s) contenant 'i9':\n")
        for row in results:
            print(f"Term ID: {row['term_id']}")
            print(f"  Name: {row['name']}")
            print(f"  Slug: {row['slug']}")
            print(f"  Taxonomy: {row['taxonomy']}")
            print(f"  Count: {row['count']}")
            print(f"  Term Taxonomy ID: {row['term_taxonomy_id']}")
            
            # Vérifier les produits liés
            cursor.execute(f"""
                SELECT COUNT(*) as product_count
                FROM {WP_PREFIX}term_relationships
                WHERE term_taxonomy_id = %s
            """, (row['term_taxonomy_id'],))
            rel_count = cursor.fetchone()
            print(f"  Products linked (relationships): {rel_count['product_count']}")
            
            # Vérifier dans la table de lookup
            cursor.execute(f"""
                SELECT COUNT(*) as lookup_count
                FROM {WP_PREFIX}wc_product_attributes_lookup
                WHERE term_id = %s
            """, (row['term_id'],))
            lookup_count = cursor.fetchone()
            print(f"  Lookup entries: {lookup_count['lookup_count']}")
            print()
    else:
        print("Aucun terme trouvé contenant 'i9'")
    
    # Chercher aussi "Core" pour voir tous les processeurs Intel Core
    print("\n=== TOUS LES TERMES INTEL CORE ===\n")
    query = f"""
        SELECT 
            t.term_id,
            t.name,
            t.slug,
            tt.taxonomy,
            tt.count
        FROM {WP_PREFIX}terms t
        JOIN {WP_PREFIX}term_taxonomy tt ON t.term_id = tt.term_id
        WHERE tt.taxonomy LIKE 'pa_%'
        AND t.name LIKE '%Intel Core%'
        ORDER BY t.name
    """
    
    cursor.execute(query)
    core_results = cursor.fetchall()
    
    for row in core_results:
        print(f"{row['name']} ({row['count']}) - {row['taxonomy']}")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    check_i9_terms()
