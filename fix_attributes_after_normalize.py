"""
Script pour recalculer les compteurs et reconstruire la table de lookup
après la normalisation des attributs.
"""
from database import connect_wp_ozar0
from sync_attributes import recalculate_term_counts, fix_lookup_table, WP_PREFIX

def main():
    print("=== RECALCUL DES COMPTEURS ET RECONSTRUCTION DE LA TABLE DE LOOKUP ===\n")
    
    conn = connect_wp_ozar0()
    cursor = conn.cursor(buffered=True)
    
    try:
        # 1. Recalculer les compteurs de termes
        recalculate_term_counts(cursor, conn)
        
        # 2. Reconstruire la table de lookup
        fix_lookup_table(cursor, conn)
        
        print("\n=== TERMINE ===")
        print("Les filtres devraient maintenant fonctionner correctement!")
        print("Vérifiez votre site pour confirmer que 'Intel Core i9' n'apparaît qu'une seule fois.")
        
    except Exception as e:
        print(f"\nErreur: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    main()
