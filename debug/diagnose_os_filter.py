"""
Diagnostic approfondi: Pourquoi le filtre OS n'apparait pas sur PC Portable
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import connect_wp_ozar0

# Forcer l'encodage UTF-8 pour Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

WP_PREFIX = "9Ew5q6v_"

def check_woocommerce_settings(cursor):
    """Vérifie les paramètres WooCommerce liés aux filtres"""
    print("\n" + "="*80)
    print("VERIFICATION DES PARAMETRES WOOCOMMERCE")
    print("="*80)
    
    # Vérifier les options WooCommerce
    options_to_check = [
        'woocommerce_attribute_lookup_enabled',
        'woocommerce_hide_out_of_stock_items',
        'woocommerce_layered_nav_count',
    ]
    
    for option in options_to_check:
        cursor.execute(f"""
            SELECT option_value
            FROM {WP_PREFIX}options
            WHERE option_name = %s
        """, (option,))
        
        result = cursor.fetchone()
        if result:
            print(f"  {option}: {result['option_value']}")
        else:
            print(f"  {option}: (non defini)")

def check_category_settings(cursor, category_id):
    """Vérifie les paramètres de la catégorie"""
    print(f"\n" + "="*80)
    print(f"VERIFICATION DE LA CATEGORIE PC PORTABLE (ID: {category_id})")
    print("="*80)
    
    # Vérifier les termmeta de la catégorie
    cursor.execute(f"""
        SELECT meta_key, meta_value
        FROM {WP_PREFIX}termmeta
        WHERE term_id = %s
    """, (category_id,))
    
    metas = cursor.fetchall()
    
    if metas:
        print("\n  Metadonnees de la categorie:")
        for meta in metas:
            print(f"    {meta['meta_key']}: {meta['meta_value'][:100] if meta['meta_value'] else 'NULL'}")
    else:
        print("\n  Aucune metadonnee trouvee")

def check_attribute_visibility(cursor):
    """Vérifie la visibilité de l'attribut OS"""
    print("\n" + "="*80)
    print("VERIFICATION DE LA VISIBILITE DE L'ATTRIBUT OS")
    print("="*80)
    
    cursor.execute(f"""
        SELECT 
            attribute_id,
            attribute_name,
            attribute_label,
            attribute_type,
            attribute_orderby,
            attribute_public
        FROM {WP_PREFIX}woocommerce_attribute_taxonomies
        WHERE attribute_name = 'systeme-dexploitation'
    """)
    
    attr = cursor.fetchone()
    
    if attr:
        print("\n  Attribut WooCommerce:")
        for key, value in attr.items():
            print(f"    {key}: {value}")
        
        if attr['attribute_public'] != 1:
            print("\n  [!] PROBLEME: L'attribut n'est pas public!")
            return False
    else:
        print("\n  [!] PROBLEME: Attribut non trouve dans woocommerce_attribute_taxonomies")
        return False
    
    return True

def check_products_with_os_in_category(cursor, category_id):
    """Vérifie les produits avec OS dans la catégorie"""
    print("\n" + "="*80)
    print("VERIFICATION DES PRODUITS AVEC OS DANS PC PORTABLE")
    print("="*80)
    
    # Produits avec OS dans term_relationships
    cursor.execute(f"""
        SELECT COUNT(DISTINCT p.ID) as count_in_relationships
        FROM {WP_PREFIX}posts p
        JOIN {WP_PREFIX}term_relationships tr_cat ON p.ID = tr_cat.object_id
        JOIN {WP_PREFIX}term_taxonomy tt_cat ON tr_cat.term_taxonomy_id = tt_cat.term_taxonomy_id
        JOIN {WP_PREFIX}term_relationships tr_os ON p.ID = tr_os.object_id
        JOIN {WP_PREFIX}term_taxonomy tt_os ON tr_os.term_taxonomy_id = tt_os.term_taxonomy_id
        WHERE tt_cat.term_id = %s
        AND tt_cat.taxonomy = 'product_cat'
        AND tt_os.taxonomy = 'pa_systeme-dexploitation'
        AND p.post_type = 'product'
        AND p.post_status = 'publish'
    """, (category_id,))
    
    count_rel = cursor.fetchone()['count_in_relationships']
    print(f"\n  Produits avec OS (term_relationships): {count_rel}")
    
    # Produits avec OS dans lookup table
    cursor.execute(f"""
        SELECT COUNT(DISTINCT l.product_id) as count_in_lookup
        FROM {WP_PREFIX}wc_product_attributes_lookup l
        JOIN {WP_PREFIX}term_taxonomy tt ON l.term_id = tt.term_id
        JOIN {WP_PREFIX}term_relationships tr_cat ON l.product_id = tr_cat.object_id
        JOIN {WP_PREFIX}term_taxonomy tt_cat ON tr_cat.term_taxonomy_id = tt_cat.term_taxonomy_id
        WHERE tt.taxonomy = 'pa_systeme-dexploitation'
        AND tt_cat.term_id = %s
        AND tt_cat.taxonomy = 'product_cat'
    """, (category_id,))
    
    count_lookup = cursor.fetchone()['count_in_lookup']
    print(f"  Produits avec OS (lookup table): {count_lookup}")
    
    if count_rel != count_lookup:
        print(f"\n  [!] PROBLEME: Difference entre term_relationships ({count_rel}) et lookup ({count_lookup})")
        return False
    
    return True

def check_terms_count(cursor):
    """Vérifie les compteurs des termes OS"""
    print("\n" + "="*80)
    print("VERIFICATION DES COMPTEURS DE TERMES OS")
    print("="*80)
    
    cursor.execute(f"""
        SELECT 
            t.term_id,
            t.name,
            tt.count as taxonomy_count,
            (SELECT COUNT(*) 
             FROM {WP_PREFIX}term_relationships tr 
             JOIN {WP_PREFIX}posts p ON tr.object_id = p.ID
             WHERE tr.term_taxonomy_id = tt.term_taxonomy_id
             AND p.post_type = 'product'
             AND p.post_status = 'publish') as real_count,
            (SELECT COUNT(*)
             FROM {WP_PREFIX}wc_product_attributes_lookup l
             WHERE l.term_id = t.term_id) as lookup_count
        FROM {WP_PREFIX}terms t
        JOIN {WP_PREFIX}term_taxonomy tt ON t.term_id = tt.term_id
        WHERE tt.taxonomy = 'pa_systeme-dexploitation'
        ORDER BY real_count DESC
        LIMIT 10
    """)
    
    terms = cursor.fetchall()
    
    print("\n  Top 10 termes OS:")
    print(f"  {'Terme':<30} {'Count':<8} {'Real':<8} {'Lookup':<8}")
    print(f"  {'-'*60}")
    
    has_issues = False
    for term in terms:
        status = ""
        if term['taxonomy_count'] != term['real_count']:
            status = " [!] Count incorrect"
            has_issues = True
        if term['lookup_count'] != term['real_count']:
            status += " [!] Lookup incorrect"
            has_issues = True
        
        print(f"  {term['name']:<30} {term['taxonomy_count']:<8} {term['real_count']:<8} {term['lookup_count']:<8}{status}")
    
    return not has_issues

def check_widget_settings(cursor):
    """Vérifie les widgets de filtres"""
    print("\n" + "="*80)
    print("VERIFICATION DES WIDGETS/BLOCS DE FILTRES")
    print("="*80)
    
    # Chercher les widgets actifs
    cursor.execute(f"""
        SELECT option_name, option_value
        FROM {WP_PREFIX}options
        WHERE option_name LIKE 'widget_%'
        AND option_value LIKE '%layered_nav%'
        LIMIT 5
    """)
    
    widgets = cursor.fetchall()
    
    if widgets:
        print(f"\n  {len(widgets)} widget(s) de navigation trouve(s)")
    else:
        print("\n  [!] Aucun widget de navigation trouve")
        print("      Vous devez peut-etre ajouter le widget 'Filtre par attribut' dans la sidebar")

def main():
    conn = connect_wp_ozar0()
    cursor = conn.cursor(dictionary=True)
    
    print("="*80)
    print("DIAGNOSTIC APPROFONDI: Filtre OS sur PC Portable")
    print("="*80)
    
    category_id = 193  # PC Portable
    
    # Série de vérifications
    issues = []
    
    # 1. Vérifier les paramètres WooCommerce
    check_woocommerce_settings(cursor)
    
    # 2. Vérifier la catégorie
    check_category_settings(cursor, category_id)
    
    # 3. Vérifier la visibilité de l'attribut
    if not check_attribute_visibility(cursor):
        issues.append("Attribut OS pas visible/public")
    
    # 4. Vérifier les produits
    if not check_products_with_os_in_category(cursor, category_id):
        issues.append("Difference entre term_relationships et lookup table")
    
    # 5. Vérifier les compteurs
    if not check_terms_count(cursor):
        issues.append("Compteurs de termes incorrects")
    
    # 6. Vérifier les widgets
    check_widget_settings(cursor)
    
    # Résumé
    print("\n" + "="*80)
    print("RESUME DU DIAGNOSTIC")
    print("="*80)
    
    if issues:
        print("\n[!] PROBLEMES DETECTES:")
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. {issue}")
    else:
        print("\n[OK] Toutes les verifications techniques sont OK")
        print("\nSi le filtre n'apparait toujours pas, le probleme vient probablement de:")
        print("  1. Le theme WordPress n'affiche pas les filtres d'attributs")
        print("  2. Un plugin de cache bloque l'affichage")
        print("  3. Les widgets de filtre ne sont pas configures")
        print("  4. WooCommerce n'est pas configure pour afficher les filtres")
    
    print("\n" + "="*80)
    print("ACTIONS RECOMMANDEES")
    print("="*80)
    print("""
1. Dans l'admin WordPress, aller dans:
   WooCommerce > Reglages > Produits > Affichage
   
2. Verifier que 'Afficher les filtres d'attributs' est active

3. Aller dans Apparence > Widgets
   Ajouter le widget 'Filtre par attribut (WooCommerce)'
   Selectionner 'Systeme d'exploitation'
   
4. Ou si vous utilisez Gutenberg/blocs:
   Ajouter le bloc 'Filtre par attribut'
   Selectionner 'Systeme d'exploitation'
   
5. Vider TOUS les caches:
   - Cache WordPress
   - Cache WooCommerce
   - Cache navigateur
   - Cache serveur (si applicable)
   
6. Verifier sur une page en navigation privee
    """)
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    main()
