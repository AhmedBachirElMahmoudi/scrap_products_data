import sys
import os

# Add parent directory to path to import database
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import connect_wp_ozar0

WP_PREFIX = "9Ew5q6v_"

def check_filter_data():
    conn = connect_wp_ozar0()
    cursor = conn.cursor(dictionary=True)
    
    print("\n=== 1. ATTRIBUTE TAXONOMIES (pa_*) ===")
    cursor.execute(f"""
        SELECT taxonomy, COUNT(*) as term_count, SUM(count) as total_products
        FROM {WP_PREFIX}term_taxonomy
        WHERE taxonomy LIKE 'pa_%%'
        GROUP BY taxonomy
    """)
    taxonomies = cursor.fetchall()
    for tax in taxonomies:
        print(f"Taxonomy: {tax['taxonomy']} | Terms: {tax['term_count']} | Sum of counts: {tax['total_products']}")

    print("\n=== 2. LOOKUP TABLE STATUS ===")
    cursor.execute(f"SELECT COUNT(*) as count FROM {WP_PREFIX}wc_product_attributes_lookup")
    lookup_count = cursor.fetchone()['count']
    print(f"Total entries in wc_product_attributes_lookup: {lookup_count}")

    if lookup_count > 0:
        cursor.execute(f"SELECT taxonomy, COUNT(*) as count FROM {WP_PREFIX}wc_product_attributes_lookup GROUP BY taxonomy")
        lookup_tax = cursor.fetchall()
        for lt in lookup_tax:
            print(f"Lookup Taxonomy: {lt['taxonomy']} | Entries: {lt['count']}")

    print("\n=== 3. PRODUCT ATTRIBUTE METADATA (Sample) ===")
    # Check if products have the _product_attributes meta key and if it contains the taxonomies
    cursor.execute(f"""
        SELECT post_id, meta_value 
        FROM {WP_PREFIX}postmeta 
        WHERE meta_key = '_product_attributes' 
        LIMIT 5
    """)
    meta_samples = cursor.fetchall()
    for sample in meta_samples:
        print(f"Product ID: {sample['post_id']} | Meta Value snippet: {str(sample['meta_value'])[:100]}...")

    print("\n=== 4. CHECKING FOR MISSING RELATIONSHIPS IN LOOKUP ===")
    # Find how many term relationships exist that ARE NOT in lookup table
    cursor.execute(f"""
        SELECT COUNT(*) as missing
        FROM {WP_PREFIX}term_relationships tr
        JOIN {WP_PREFIX}term_taxonomy tt ON tr.term_taxonomy_id = tt.term_taxonomy_id
        LEFT JOIN {WP_PREFIX}wc_product_attributes_lookup cl ON tr.object_id = cl.product_id AND tt.term_id = cl.term_id
        WHERE tt.taxonomy LIKE 'pa_%%' AND cl.product_id IS NULL
    """)
    missing = cursor.fetchone()['missing']
    print(f"Term relationships (pa_*) missing from lookup: {missing}")

    cursor.close()
    conn.close()

if __name__ == "__main__":
    check_filter_data()
