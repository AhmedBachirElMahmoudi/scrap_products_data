#!/usr/bin/env python3
"""
set_out_of_stock_orphans.py

Ce script met à jour le stock à 0 (Rupture de stock) pour les produits
qui existent sur WordPress (dix.ma) mais PAS dans la base de données locale (scraper).

EXCEPTION : Les produits de la catégorie "Point de Vente" (ID 252) sont IGNORÉS.
"""

import sys
import io
import argparse
from typing import Set, Dict, List
from database import connect_scraper, connect_wp_ozar0

# Force UTF-8 stdout
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

EXCLUDED_CATEGORY_ID = 252  # Point de Vente

def get_local_skus():
    """Récupère tous les SKU de la base locale"""
    conn = connect_scraper()
    if not conn:
        print("❌ Connecteur Scraper HS")
        return set()
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT reference FROM ps_products_comparison WHERE reference IS NOT NULL AND reference != ''")
        skus = {row[0] for row in cursor.fetchall()}
        print(f"📊 Base locale: {len(skus)} produits trouvés")
        return skus
    except Exception as e:
        print(f"❌ Erreur base locale: {e}")
        return set()
    finally:
        conn.close()

def get_wp_products():
    """Récupère ID et SKU de tous les produits publiés sur WordPress"""
    conn = connect_wp_ozar0()
    if not conn:
        print("❌ Connecteur WordPress HS")
        return {}
    
    try:
        cursor = conn.cursor()
        # Récupérer ID et SKU
        query = """
        SELECT p.ID, pm.meta_value as sku 
        FROM 9Ew5q6v_posts p
        JOIN 9Ew5q6v_postmeta pm ON p.ID = pm.post_id
        WHERE p.post_type = 'product' 
        AND p.post_status = 'publish' 
        AND pm.meta_key = '_sku' 
        AND pm.meta_value IS NOT NULL 
        AND pm.meta_value != ''
        """
        cursor.execute(query)
        # Dict: SKU -> ID (Attention aux doublons SKU, on prend le dernier ou on gère une liste)
        # Pour simplifier, on assume mapping SKU -> ID unique pour la désactivation
        products = {}
        for row in cursor.fetchall():
            products[row[1]] = row[0]
            
        print(f"📊 WordPress: {len(products)} produits publiés trouvés")
        return products
    except Exception as e:
        print(f"❌ Erreur base WordPress (récup produits): {e}")
        return {}
    finally:
        conn.close()

def get_products_in_category(category_id):
    """Récupère les IDs des produits dans une catégorie spécifique"""
    conn = connect_wp_ozar0()
    if not conn:
        return set()
    
    try:
        cursor = conn.cursor()
        # Trouver les produits liés à la catégorie via term_taxonomy
        query = """
        SELECT tr.object_id 
        FROM 9Ew5q6v_term_relationships tr
        JOIN 9Ew5q6v_term_taxonomy tt ON tr.term_taxonomy_id = tt.term_taxonomy_id
        WHERE tt.term_id = %s
        """
        cursor.execute(query, (category_id,))
        ids = {row[0] for row in cursor.fetchall()}
        print(f"🔒 Catégorie {category_id} (Exclue): {len(ids)} produits protégés")
        return ids
    except Exception as e:
        print(f"❌ Erreur récupération catégorie {category_id}: {e}")
        return set()
    finally:
        conn.close()

def set_product_out_of_stock(conn, product_id):
    """Met le stock à 0 et statut outofstock"""
    try:
        cursor = conn.cursor()
        
        # 1. Update _stock
        cursor.execute("""
            UPDATE 9Ew5q6v_postmeta 
            SET meta_value = '0' 
            WHERE post_id = %s AND meta_key = '_stock'
        """, (product_id,))
        
        # 2. Update _stock_status
        cursor.execute("""
            UPDATE 9Ew5q6v_postmeta 
            SET meta_value = 'outofstock' 
            WHERE post_id = %s AND meta_key = '_stock_status'
        """, (product_id,))
        
        # 3. Toucher le post pour la date de modif
        cursor.execute("""
            UPDATE 9Ew5q6v_posts 
            SET post_modified = NOW()
            WHERE ID = %s
        """, (product_id,))
        
        return True
    except Exception as e:
        print(f"❌ Erreur lors de la mise à jour ID {product_id}: {e}")
        return False

def main(dry_run=True):
    print("="*60)
    print("🧹 NETTOYAGE DES PRODUITS ORPHELINS (Mise hors stock)")
    print("="*60)
    if dry_run:
        print("⚠️  MODE SIMULATION (DRY-RUN) - Aucune modification ne sera faite")
    else:
        print("🚨 MODE RÉEL - Les modifications seront appliquées !")
    print("-" * 60)

    # 1. Récupérer les SKUs locaux
    local_skus = get_local_skus()
    if not local_skus:
        print("Arrêt : Base locale vide ou inaccessible.")
        return

    # 2. Récupérer les produits WP
    wp_products_map = get_wp_products() # SKU -> ID
    if not wp_products_map:
        print("Arrêt : Base WP vide ou inaccessible.")
        return

    # 3. Récupérer les produits protégés (Catégorie 252)
    protected_ids = get_products_in_category(EXCLUDED_CATEGORY_ID)

    # 4. Identifier les orphelins
    orphans = []
    for sku, pid in wp_products_map.items():
        if sku not in local_skus:
            # C'est un orphelin
            if pid not in protected_ids:
                orphans.append((sku, pid))
            else:
                # Orphelin mais protégé
                pass # On pourrait le logger si besoin

    print(f"🔍 Résultat : {len(orphans)} produits à mettre hors stock (sur {len(wp_products_map)} produits WP total)")
    print("-" * 60)

    if not orphans:
        print("✅ Aucun produit orphelin à traiter.")
        return

    # 5. Traiter les orphelins
    conn = None
    if not dry_run:
        conn = connect_wp_ozar0()
        if not conn:
            print("❌ Impossible de se connecter pour appliquer les modifications.")
            return

    count_updated = 0
    try:
        for i, (sku, pid) in enumerate(orphans, 1):
            if i <= 10 or i % 100 == 0:
                print(f"[{i}/{len(orphans)}] Traitement orphelin: {sku} (ID: {pid})")
            
            if not dry_run:
                if set_product_out_of_stock(conn, pid):
                    count_updated += 1
                    if i % 100 == 0:
                        conn.commit() # Commit par lots
            else:
                # En simulation, on compte juste
                count_updated += 1
        
        if not dry_run:
            conn.commit() # Commit final
            print(f"\n✅ Terminé : {count_updated} produits mis hors stock.")
        else:
            print(f"\n✅ Simulation terminée : {count_updated} produits auraient été mis hors stock.")
            print("💡 Pour appliquer les changements, lancez avec : python set_out_of_stock_orphans.py --apply")

    except Exception as e:
        print(f"\n❌ Erreur globale pendant le traitement: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mettre hors stock les produits orphelins")
    parser.add_argument("--apply", action="store_true", help="Appliquer les modifications (sinon simulation)")
    args = parser.parse_args()
    
    main(dry_run=not args.apply)
