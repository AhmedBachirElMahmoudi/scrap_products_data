from database import connect_wp_ozar0
import re

WP_PREFIX = "9Ew5q6v_"

def recalculate_term_counts():
    """Recalcule les compteurs pour toutes les taxonomies d'attributs (pa_%)."""
    print("\n[COUNTS] Recalculating term counts...")
    conn = connect_wp_ozar0()
    cursor = conn.cursor()
    
    query = f"""
        UPDATE {WP_PREFIX}term_taxonomy tt
        SET count = (
            SELECT COUNT(*)
            FROM {WP_PREFIX}term_relationships tr
            WHERE tr.term_taxonomy_id = tt.term_taxonomy_id
        )
        WHERE tt.taxonomy LIKE 'pa_%'
    """
    
    try:
        cursor.execute(query)
        affected = cursor.rowcount
        print(f"   Success! Updated counts for {affected} attribute terms.")
        conn.commit()
    except Exception as e:
        print(f"   X Error updating counts: {e}")
    finally:
        cursor.close()
        conn.close()

def fix_lookup_table():
    """Reconstruit la table wc_product_attributes_lookup pour les attributs pa_%."""
    print("\n[LOOKUP] Fixing lookup table...")
    conn = connect_wp_ozar0()
    cursor = conn.cursor()
    
    try:
        # 1. Nettoyer les entrées pa_% existantes (ou tout vider si on veut être radical)
        # On va vider et reconstruire pour être sûr que tout est synchro
        print("   Clearing existing lookup data for attributes...")
        cursor.execute(f"DELETE FROM {WP_PREFIX}wc_product_attributes_lookup WHERE taxonomy LIKE 'pa_%'")
        
        # 2. Re-insérer à partir des relations actuelles
        print("   Repopulating lookup table from term relationships...")
        query = f"""
            INSERT IGNORE INTO {WP_PREFIX}wc_product_attributes_lookup 
            (product_id, product_or_parent_id, taxonomy, term_id, is_variation_attribute, in_stock)
            SELECT DISTINCT
                tr.object_id, 
                tr.object_id, 
                tt.taxonomy, 
                tt.term_id, 
                0, 
                1
            FROM {WP_PREFIX}term_relationships tr
            JOIN {WP_PREFIX}term_taxonomy tt ON tr.term_taxonomy_id = tt.term_taxonomy_id
            WHERE tt.taxonomy LIKE 'pa_%'
        """
        cursor.execute(query)
        inserted = cursor.rowcount
        print(f"   Success! Inserted {inserted} entries into lookup table.")
        
        conn.commit()
    except Exception as e:
        print(f"   X Error fixing lookup table: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    recalculate_term_counts()
    fix_lookup_table()
    print("\n=== TERMINE ===")
