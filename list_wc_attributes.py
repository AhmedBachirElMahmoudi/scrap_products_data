from database import connect_wp_ozar0

def list_woocommerce_attributes():
    """Liste tous les attributs enregistrés dans le dictionnaire WooCommerce."""
    
    conn = connect_wp_ozar0()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Récupérer tous les attributs enregistrés
        cursor.execute("""
            SELECT 
                attribute_id,
                attribute_name,
                attribute_label,
                attribute_type,
                attribute_orderby,
                attribute_public
            FROM 9Ew5q6v_woocommerce_attribute_taxonomies
            ORDER BY attribute_name
        """)
        
        attributes = cursor.fetchall()
        
        print("=" * 100)
        print("ATTRIBUTS ENREGISTRÉS DANS WOOCOMMERCE")
        print("=" * 100)
        print(f"\nTotal: {len(attributes)} attributs\n")
        
        # Afficher sous forme de tableau
        print(f"{'ID':<5} {'Nom (Taxonomy)':<30} {'Label':<35} {'Type':<10} {'Public':<6}")
        print("-" * 100)
        
        for attr in attributes:
            attr_id = attr['attribute_id']
            attr_name = f"pa_{attr['attribute_name']}"
            attr_label = attr['attribute_label'] or '(vide)'
            attr_type = attr['attribute_type']
            attr_public = 'Oui' if attr['attribute_public'] else 'Non'
            
            # Tronquer si trop long
            if len(attr_label) > 35:
                attr_label = attr_label[:32] + '...'
            
            print(f"{attr_id:<5} {attr_name:<30} {attr_label:<35} {attr_type:<10} {attr_public:<6}")
        
        print("\n" + "=" * 100)
        
        # Statistiques par type
        print("\nSTATISTIQUES PAR TYPE:")
        cursor.execute("""
            SELECT attribute_type, COUNT(*) as count
            FROM 9Ew5q6v_woocommerce_attribute_taxonomies
            GROUP BY attribute_type
        """)
        
        types = cursor.fetchall()
        for t in types:
            print(f"  {t['attribute_type']}: {t['count']} attributs")
        
        # Attributs publics vs privés
        print("\nVISIBILITÉ:")
        cursor.execute("""
            SELECT 
                SUM(CASE WHEN attribute_public = 1 THEN 1 ELSE 0 END) as public_count,
                SUM(CASE WHEN attribute_public = 0 THEN 1 ELSE 0 END) as private_count
            FROM 9Ew5q6v_woocommerce_attribute_taxonomies
        """)
        
        visibility = cursor.fetchone()
        print(f"  Publics: {visibility['public_count']}")
        print(f"  Privés: {visibility['private_count']}")
        
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    list_woocommerce_attributes()
