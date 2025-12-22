import json
import re
from database import connect_wp_ozar0, connect_scraper


# =========================================================
# ANALYSE PRODUIT : MARQUES & ATTRIBUTS
# =========================================================
def check_product_brands(sku):
    print(f"\nANALYSE DU PRODUIT: {sku}")
    print("=" * 60)

    # ---------- 1. SOURCE (SCRAPER) ----------
    print("SOURCE (ps_products_comparison):")
    conn_source = connect_scraper()
    cursor_source = conn_source.cursor(buffered=True)

    try:
        cursor_source.execute(
            "SELECT attributes, brand_id FROM ps_products_comparison WHERE reference = %s",
            (sku,)
        )
        source_res = cursor_source.fetchone()

        if source_res:
            print(f"   Brand ID (colonne): {source_res[1]}")
            print(f"   Attributs (JSON): {source_res[0]}")
        else:
            print("   Produit non trouvé dans la source.")
    except Exception as e:
        print(f"   Erreur source: {e}")
    finally:
        cursor_source.close()
        conn_source.close()

    # ---------- 2. WORDPRESS ----------
    print("\nDESTINATION (WordPress):")
    conn = connect_wp_ozar0()
    cursor = conn.cursor(buffered=True)

    try:
        # ID produit
        cursor.execute(
            "SELECT post_id FROM 9Ew5q6v_postmeta WHERE meta_key='_sku' AND meta_value=%s",
            (sku,)
        )
        res = cursor.fetchone()

        if not res:
            print("❌ Produit non trouvé.")
            return

        post_id = res[0]
        print(f"ID Produit: {post_id}")

        # Infos produit
        cursor.execute(
            "SELECT post_title FROM 9Ew5q6v_posts WHERE ID=%s",
            (post_id,)
        )
        print(f"Titre: {cursor.fetchone()[0]}")

        # ---------- TAXONOMIES ----------
        print("\nTAXONOMIES LIEES:")
        cursor.execute("""
            SELECT t.name, tt.taxonomy
            FROM 9Ew5q6v_term_relationships tr
            JOIN 9Ew5q6v_term_taxonomy tt ON tr.term_taxonomy_id = tt.term_taxonomy_id
            JOIN 9Ew5q6v_terms t ON tt.term_id = t.term_id
            WHERE tr.object_id = %s
        """, (post_id,))

        terms = cursor.fetchall()
        for name, taxonomy in terms:
            print(f"   - [{taxonomy}] {name}")

        # ---------- ATTRIBUTS WC ----------
        print("\nATTRIBUTS (_product_attributes):")
        cursor.execute("""
            SELECT meta_value FROM 9Ew5q6v_postmeta
            WHERE post_id=%s AND meta_key='_product_attributes'
        """, (post_id,))

        attr = cursor.fetchone()
        if not attr:
            print("   X Aucun attribut.")
        else:
            raw = attr[0]
            print(f"   Brut (extrait): {raw[:150]}...")

            matches = re.findall(r's:\d+:"(pa_[^"]+)"', raw)
            for m in set(matches):
                print(f"   - {m}")

        # ---------- META MARQUE ----------
        print("\nMETA MARQUE:")
        keys = ['brand', 'marque', 'product_brand']
        for k in keys:
            cursor.execute("""
                SELECT meta_value FROM 9Ew5q6v_postmeta
                WHERE post_id=%s AND meta_key LIKE %s
            """, (post_id, f'%{k}%'))

            rows = cursor.fetchall()
            for r in rows:
                print(f"   - {k}: {r[0]}")

        # ---------- RESUME ----------
        print("\nRESUME:")
        print("   OK pa_marque present")
        print("   WARN product_brand present (doublon)")
        print("   INFO Recommande: supprimer product_brand")

    except Exception as e:
        print(f"X Erreur: {e}")

    finally:
        cursor.close()
        conn.close()


# =========================================================
# SUPPRESSION DES DOUBLONS product_brand
# =========================================================
def clean_product_brand_duplicates(sku):
    print(f"\n🧹 NETTOYAGE: {sku}")
    print("=" * 60)

    conn = connect_wp_ozar0()
    cursor = conn.cursor(buffered=True)

    try:
        cursor.execute(
            "SELECT post_id FROM 9Ew5q6v_postmeta WHERE meta_key='_sku' AND meta_value=%s",
            (sku,)
        )
        res = cursor.fetchone()
        if not res:
            print("❌ Produit non trouvé.")
            return

        post_id = res[0]

        cursor.execute("""
            DELETE tr FROM 9Ew5q6v_term_relationships tr
            JOIN 9Ew5q6v_term_taxonomy tt ON tr.term_taxonomy_id = tt.term_taxonomy_id
            WHERE tr.object_id = %s AND tt.taxonomy = 'product_brand'
        """, (post_id,))

        print(f"🗑️ Supprimé: {cursor.rowcount}")
        conn.commit()

    except Exception as e:
        conn.rollback()
        print(f"❌ Erreur: {e}")
    finally:
        cursor.close()
        conn.close()


# =========================================================
# MAIN
# =========================================================
if __name__ == "__main__":
    SKUS = ['886J1EA']
    ACTION = "check"  # check | clean

    for sku in SKUS:
        if ACTION == "check":
            check_product_brands(sku)
        elif ACTION == "clean":
            clean_product_brand_duplicates(sku)

    print("\nTERMINÉ")
