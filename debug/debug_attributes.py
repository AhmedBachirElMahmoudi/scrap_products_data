import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import connect_wp_ozar0

WP_PREFIX = "9Ew5q6v_"

def check_attributes_visibility():
    conn = connect_wp_ozar0()
    cursor = conn.cursor(dictionary=True)
    
    print("Checking 'pc-portable' category attributes... SKIPPED")
            
    print("\n--- Deep Dive Product 21472 Meta ---")
    pid = 21472
    cursor.execute(f"""
        SELECT meta_value FROM {WP_PREFIX}postmeta
        WHERE post_id = %s AND meta_key = '_product_attributes'
    """, (pid,))
    row = cursor.fetchone()
    print("\n--- Meta Check for 21472 ---")
    pid = 21472
    cursor.execute(f"SELECT meta_value FROM {WP_PREFIX}postmeta WHERE post_id = %s AND meta_key = '_product_attributes'", (pid,))
    row = cursor.fetchone()
    if row:
        print(f"Meta found! Length: {len(row['meta_value'])}")
        print(row['meta_value']) 
    else:
        print("Meta NOT found for _product_attributes")

    # print("\n--- Term Counts Check ---")
    # # Check general totals for pa_processeur
    # cursor.execute(f"""
    #     SELECT t.name, tt.count, tt.taxonomy
    #     FROM {WP_PREFIX}term_taxonomy tt
    #     JOIN {WP_PREFIX}terms t ON tt.term_id = t.term_id
    #     WHERE tt.taxonomy = 'pa_processeur'
    #     ORDER BY tt.count DESC
    #     LIMIT 5
    # """)
    # top_procs = cursor.fetchall()
    # print("Top 5 Processors by count:")
    # for tp in top_procs:
    #     print(f" - {tp['name']}: {tp['count']}")

    conn.close()

if __name__ == "__main__":
    check_attributes_visibility()
