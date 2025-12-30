"""
Vérifie l'état de l'attribut Système d'exploitation
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import connect_wp_ozar0

WP_PREFIX = "9Ew5q6v_"

def check_os_attribute():
    conn = connect_wp_ozar0()
    cursor = conn.cursor(dictionary=True)
    
    print("=== VÉRIFICATION DE L'ATTRIBUT SYSTÈME D'EXPLOITATION ===\n")
    
    # 1. Chercher toutes les taxonomies liées au système d'exploitation
    query = f"""
        SELECT DISTINCT tt.taxonomy, COUNT(*) as term_count
        FROM {WP_PREFIX}term_taxonomy tt
        WHERE tt.taxonomy LIKE '%os%' 
           OR tt.taxonomy LIKE '%systeme%'
           OR tt.taxonomy LIKE '%exploitation%'
        GROUP BY tt.taxonomy
    """
    
    cursor.execute(query)
    taxonomies = cursor.fetchall()
    
    if taxonomies:
        print("Taxonomies trouvées liées à l'OS :")
        for tax in taxonomies:
            print(f"  - {tax['taxonomy']} ({tax['term_count']} termes)")
    else:
        print("❌ Aucune taxonomie trouvée pour le système d'exploitation")
    
    print("\n" + "="*60 + "\n")
    
    # 2. Pour chaque taxonomie, afficher les termes et leurs compteurs
    for tax in taxonomies:
        taxonomy_name = tax['taxonomy']
        print(f"Détails pour: {taxonomy_name}")
        print("-" * 60)
        
        cursor.execute(f"""
            SELECT 
                t.term_id,
                t.name,
                t.slug,
                tt.count,
                tt.term_taxonomy_id
            FROM {WP_PREFIX}terms t
            JOIN {WP_PREFIX}term_taxonomy tt ON t.term_id = tt.term_id
            WHERE tt.taxonomy = %s
            ORDER BY t.name
        """, (taxonomy_name,))
        
        terms = cursor.fetchall()
        
        for term in terms:
            print(f"\n  Terme: {term['name']}")
            print(f"    Term ID: {term['term_id']}")
            print(f"    Slug: {term['slug']}")
            print(f"    Count (taxonomy): {term['count']}")
            
            # Vérifier les relations réelles
            cursor.execute(f"""
                SELECT COUNT(*) as real_count
                FROM {WP_PREFIX}term_relationships
                WHERE term_taxonomy_id = %s
            """, (term['term_taxonomy_id'],))
            real = cursor.fetchone()
            print(f"    Count (relationships): {real['real_count']}")
            
            # Vérifier la table de lookup
            cursor.execute(f"""
                SELECT COUNT(*) as lookup_count
                FROM {WP_PREFIX}wc_product_attributes_lookup
                WHERE term_id = %s
            """, (term['term_id'],))
            lookup = cursor.fetchone()
            print(f"    Count (lookup): {lookup['lookup_count']}")
            
            # Si le count est 0 mais qu'il y a des relations, c'est un problème
            if term['count'] == 0 and real['real_count'] > 0:
                print(f"    ⚠️  PROBLÈME: Count=0 mais {real['real_count']} produits liés!")
    
    print("\n" + "="*60 + "\n")
    
    # 3. Vérifier si l'attribut est enregistré dans woocommerce_attribute_taxonomies
    cursor.execute(f"""
        SELECT *
        FROM {WP_PREFIX}woocommerce_attribute_taxonomies
        WHERE attribute_name LIKE '%os%'
           OR attribute_name LIKE '%systeme%'
           OR attribute_name LIKE '%exploitation%'
    """)
    
    wc_attrs = cursor.fetchall()
    
    if wc_attrs:
        print("Attributs WooCommerce trouvés :")
        for attr in wc_attrs:
            print(f"\n  Attribute ID: {attr['attribute_id']}")
            print(f"    Name: {attr['attribute_name']}")
            print(f"    Label: {attr['attribute_label']}")
            print(f"    Type: {attr['attribute_type']}")
            print(f"    Order by: {attr['attribute_orderby']}")
            print(f"    Public: {attr['attribute_public']}")
    else:
        print("❌ Aucun attribut WooCommerce trouvé pour l'OS")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    check_os_attribute()
