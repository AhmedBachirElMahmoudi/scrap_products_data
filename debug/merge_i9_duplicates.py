"""
Fusionne manuellement les doublons Intel Core i9
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import connect_wp_ozar0

WP_PREFIX = "9Ew5q6v_"

def merge_i9_duplicates():
    conn = connect_wp_ozar0()
    cursor = conn.cursor(dictionary=True)
    
    print("=== FUSION DES DOUBLONS INTEL CORE i9 ===\n")
    
    # Les IDs identifiés
    KEEP_TERM_ID = 6278  # Intel Core i9 (propre)
    DELETE_TERM_ID = 5772  # Intel® Core™ i9 (avec symboles)
    
    try:
        # 1. Récupérer les term_taxonomy_id
        cursor.execute(f"""
            SELECT term_taxonomy_id 
            FROM {WP_PREFIX}term_taxonomy 
            WHERE term_id = %s
        """, (KEEP_TERM_ID,))
        keep_tt = cursor.fetchone()
        
        cursor.execute(f"""
            SELECT term_taxonomy_id 
            FROM {WP_PREFIX}term_taxonomy 
            WHERE term_id = %s
        """, (DELETE_TERM_ID,))
        delete_tt = cursor.fetchone()
        
        if not keep_tt or not delete_tt:
            print("Erreur: Impossible de trouver les term_taxonomy_id")
            return
        
        keep_tt_id = keep_tt['term_taxonomy_id']
        delete_tt_id = delete_tt['term_taxonomy_id']
        
        print(f"Terme à conserver: ID {KEEP_TERM_ID} (TT_ID: {keep_tt_id})")
        print(f"Terme à supprimer: ID {DELETE_TERM_ID} (TT_ID: {delete_tt_id})")
        
        # 2. Supprimer les relations en doublon (où le produit a déjà le bon terme)
        print("\n1. Suppression des relations en doublon...")
        cursor.execute(f"""
            DELETE tr1 FROM {WP_PREFIX}term_relationships tr1
            INNER JOIN {WP_PREFIX}term_relationships tr2
            ON tr1.object_id = tr2.object_id
            WHERE tr1.term_taxonomy_id = %s
            AND tr2.term_taxonomy_id = %s
        """, (delete_tt_id, keep_tt_id))
        print(f"   Supprimé {cursor.rowcount} relations en doublon")
        
        # 3. Migrer les relations restantes vers le bon terme
        print("\n2. Migration des relations restantes...")
        cursor.execute(f"""
            UPDATE {WP_PREFIX}term_relationships
            SET term_taxonomy_id = %s
            WHERE term_taxonomy_id = %s
        """, (keep_tt_id, delete_tt_id))
        print(f"   Migré {cursor.rowcount} relations")
        
        # 4. Supprimer les entrées de lookup pour l'ancien terme
        print("\n3. Nettoyage de la table de lookup...")
        cursor.execute(f"""
            DELETE FROM {WP_PREFIX}wc_product_attributes_lookup
            WHERE term_id = %s
        """, (DELETE_TERM_ID,))
        print(f"   Supprimé {cursor.rowcount} entrées de lookup")
        
        # 5. Supprimer l'ancienne taxonomie
        print("\n4. Suppression de l'ancienne taxonomie...")
        cursor.execute(f"""
            DELETE FROM {WP_PREFIX}term_taxonomy
            WHERE term_id = %s
        """, (DELETE_TERM_ID,))
        print(f"   Supprimé {cursor.rowcount} taxonomie(s)")
        
        # 6. Supprimer l'ancien terme
        print("\n5. Suppression de l'ancien terme...")
        cursor.execute(f"""
            DELETE FROM {WP_PREFIX}terms
            WHERE term_id = %s
        """, (DELETE_TERM_ID,))
        print(f"   Supprimé {cursor.rowcount} terme(s)")
        
        # 7. Recalculer le compteur pour le terme conservé
        print("\n6. Recalcul du compteur...")
        cursor.execute(f"""
            UPDATE {WP_PREFIX}term_taxonomy
            SET count = (
                SELECT COUNT(*)
                FROM {WP_PREFIX}term_relationships
                WHERE term_taxonomy_id = %s
            )
            WHERE term_taxonomy_id = %s
        """, (keep_tt_id, keep_tt_id))
        print(f"   Compteur mis à jour")
        
        # 8. Reconstruire les entrées de lookup pour le terme conservé
        print("\n7. Reconstruction des entrées de lookup...")
        # D'abord supprimer les entrées existantes pour ce terme
        cursor.execute(f"""
            DELETE FROM {WP_PREFIX}wc_product_attributes_lookup
            WHERE term_id = %s AND taxonomy = 'pa_processeur'
        """, (KEEP_TERM_ID,))
        print(f"   Supprimé {cursor.rowcount} anciennes entrées de lookup")
        
        # Puis recréer
        cursor.execute(f"""
            INSERT INTO {WP_PREFIX}wc_product_attributes_lookup 
            (product_id, product_or_parent_id, taxonomy, term_id, is_variation_attribute, in_stock)
            SELECT 
                tr.object_id,
                tr.object_id,
                'pa_processeur',
                %s,
                0,
                1
            FROM {WP_PREFIX}term_relationships tr
            WHERE tr.term_taxonomy_id = %s
            AND tr.object_id IN (
                SELECT ID FROM {WP_PREFIX}posts WHERE post_type = 'product'
            )
        """, (KEEP_TERM_ID, keep_tt_id))
        print(f"   Créé {cursor.rowcount} nouvelles entrées de lookup")

        
        # Commit
        conn.commit()
        
        print("\n=== FUSION TERMINÉE ===")
        print("Vérifiez maintenant votre site - il ne devrait y avoir qu'un seul 'Intel Core i9'")
        
    except Exception as e:
        print(f"\nERREUR: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    merge_i9_duplicates()
