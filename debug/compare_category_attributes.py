import mysql.connector
from database import connect_wp_ozar0


def check_category_attributes():
    conn = connect_wp_ozar0()
    cursor = conn.cursor(dictionary=True)
    
    # Prefix for tables
    PREFIX = "9Ew5q6v_"
    
    categories = ['pc-portable', 'serveur']
    
    # Summary statistics for PC Portable
    print("\n=== STATISTICS: PC Portable ===")
    
    # Get all products in category
    cursor.execute(f"""
        SELECT COUNT(p.ID) as total
        FROM {PREFIX}posts p
        JOIN {PREFIX}term_relationships tr ON p.ID = tr.object_id
        JOIN {PREFIX}term_taxonomy tt ON tr.term_taxonomy_id = tt.term_taxonomy_id
        JOIN {PREFIX}terms t ON tt.term_id = t.term_id
        WHERE t.slug = 'pc-portable' AND p.post_type = 'product' AND p.post_status = 'publish'
    """)
    total_products = cursor.fetchone()['total']
    print(f"Total Products: {total_products}")

    # Get products with RAM
    cursor.execute(f"""
        SELECT COUNT(DISTINCT p.ID) as with_ram
        FROM {PREFIX}posts p
        JOIN {PREFIX}term_relationships tr_cat ON p.ID = tr_cat.object_id
        JOIN {PREFIX}term_taxonomy tt_cat ON tr_cat.term_taxonomy_id = tt_cat.term_taxonomy_id
        JOIN {PREFIX}terms t_cat ON tt_cat.term_id = t_cat.term_id
        
        JOIN {PREFIX}term_relationships tr_attr ON p.ID = tr_attr.object_id
        JOIN {PREFIX}term_taxonomy tt_attr ON tr_attr.term_taxonomy_id = tt_attr.term_taxonomy_id
        
        WHERE t_cat.slug = 'pc-portable' 
        AND p.post_type = 'product' 
        AND p.post_status = 'publish'
        AND (tt_attr.taxonomy = 'pa_ram' OR tt_attr.taxonomy = 'pa_memoire')
    """)
    with_ram = cursor.fetchone()['with_ram']
    print(f"Products with RAM attribute: {with_ram}")
    print(f"Coverage: {with_ram/total_products*100:.1f}%" if total_products else "Coverage: 0%")
    
    if with_ram < total_products:
        print("\n[INFO] Some products are missing RAM attributes. This explains why filters might behave oddly if the count is low.")

    cursor.close()
    conn.close()

if __name__ == "__main__":
    check_category_attributes()
