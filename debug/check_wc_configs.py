import sys
import os

# Add parent directory to path to import database
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import connect_wp_ozar0

WP_PREFIX = "9Ew5q6v_"

def check_wc_taxonomies():
    conn = connect_wp_ozar0()
    cursor = conn.cursor(dictionary=True)
    
    print("\n=== WOOCOMMERCE ATTRIBUTE TAXONOMIES TABLE ===")
    cursor.execute(f"SELECT * FROM {WP_PREFIX}woocommerce_attribute_taxonomies")
    attrs = cursor.fetchall()
    
    if not attrs:
        print("No entries in woocommerce_attribute_taxonomies!")
    else:
        for attr in attrs:
            print(f"ID: {attr['attribute_id']} | Name: {attr['attribute_name']} | Label: {attr['attribute_label']} | Type: {attr['attribute_type']}")

    print("\n=== SAMPLE _PRODUCT_ATTRIBUTES FOR PRODUCT ID 14273 ===")
    cursor.execute(f"SELECT meta_value FROM {WP_PREFIX}postmeta WHERE post_id = 14273 AND meta_key = '_product_attributes'")
    res = cursor.fetchone()
    if res:
        print(f"Raw meta_value (snippet): {res['meta_value'][:200]}...")
    
    # Check specifically for pa_processeur and pa_ram in attribute configuration
    print("\n=== SPECIFIC ATTRIBUTE CHECK ===")
    cursor.execute(f"SELECT * FROM {WP_PREFIX}woocommerce_attribute_taxonomies WHERE attribute_name IN ('processeur', 'ram', 'stockage', 'os')")
    specific_attrs = cursor.fetchall()
    for attr in specific_attrs:
        print(f"Found config for: {attr['attribute_name']} (type: {attr['attribute_type']})")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    check_wc_taxonomies()
