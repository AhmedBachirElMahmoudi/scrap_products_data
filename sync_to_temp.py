#!/usr/bin/env python3
"""
sync_to_temp.py

Synchronise la table ps_products_comparison de la base locale (dix_scraper)
vers la base distante (dix_temp).

Processus:
1. Vide la table distante
2. Copie toutes les données de la table locale vers la distante
"""

import sys
import io

# Force UTF-8 stdout
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

from database import connect_scraper, connect_temp
from datetime import datetime

def sync_products_to_temp():
    """Synchronise ps_products_comparison local -> distant (dix_temp)"""
    
    print("="*60)
    print("🔄 SYNCHRONISATION ps_products_comparison -> dix_temp")
    print("="*60)
    
    # 1. Connexion aux deux bases
    print("\n📡 Connexion aux bases de données...")
    conn_local = connect_scraper()
    conn_remote = connect_temp()
    
    if not conn_local:
        print("❌ Impossible de se connecter à la base locale (dix_scraper)")
        return False
        
    if not conn_remote:
        print("❌ Impossible de se connecter à la base distante (dix_temp)")
        if conn_local:
            conn_local.close()
        return False
    
    print("✅ Connexions établies")
    
    try:
        cursor_local = conn_local.cursor()
        cursor_remote = conn_remote.cursor()
        
        # 2. Compter les produits locaux
        print("\n📊 Comptage des produits locaux...")
        cursor_local.execute("SELECT COUNT(*) FROM ps_products_comparison")
        count_local = cursor_local.fetchone()[0]
        print(f"📦 {count_local} produits dans la base locale")
        
        if count_local == 0:
            print("⚠️  Aucun produit à synchroniser")
            return True
        
        # 3. Vider la table distante
        print("\n🗑️  Vidage de la table distante...")
        cursor_remote.execute("TRUNCATE TABLE ps_products_comparison")
        conn_remote.commit()
        print("✅ Table distante vidée")
        
        # 4. Récupérer toutes les données locales
        print("\n📥 Récupération des données locales...")
        cursor_local.execute("SELECT * FROM ps_products_comparison")
        rows = cursor_local.fetchall()
        
        # Récupérer les noms de colonnes
        columns = [desc[0] for desc in cursor_local.description]
        print(f"✅ {len(rows)} lignes récupérées avec {len(columns)} colonnes")
        
        # 5. Insérer dans la table distante
        print("\n📤 Insertion dans la table distante...")
        
        # Construire la requête INSERT
        placeholders = ', '.join(['%s'] * len(columns))
        column_names = ', '.join(columns)
        insert_query = f"INSERT INTO ps_products_comparison ({column_names}) VALUES ({placeholders})"
        
        # Insérer par lots de 100 pour optimiser
        batch_size = 100
        total_inserted = 0
        
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i+batch_size]
            cursor_remote.executemany(insert_query, batch)
            conn_remote.commit()
            total_inserted += len(batch)
            
            if total_inserted % 500 == 0 or total_inserted == len(rows):
                print(f"  ✅ {total_inserted}/{len(rows)} produits insérés...")
        
        print(f"\n✅ Synchronisation terminée : {total_inserted} produits copiés")
        
        # 6. Vérification
        print("\n🔍 Vérification...")
        cursor_remote.execute("SELECT COUNT(*) FROM ps_products_comparison")
        count_remote = cursor_remote.fetchone()[0]
        print(f"📊 Base distante contient maintenant : {count_remote} produits")
        
        if count_remote == count_local:
            print("✅ Synchronisation réussie !")
            return True
        else:
            print(f"⚠️  Attention : {count_local} locaux vs {count_remote} distants")
            return False
            
    except Exception as e:
        print(f"\n❌ Erreur lors de la synchronisation : {e}")
        return False
        
    finally:
        if cursor_local:
            cursor_local.close()
        if cursor_remote:
            cursor_remote.close()
        if conn_local:
            conn_local.close()
        if conn_remote:
            conn_remote.close()
        print("\n🔌 Connexions fermées")

if __name__ == "__main__":
    print(f"\n🕐 Démarrage : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    success = sync_products_to_temp()
    print(f"🕐 Fin : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if success:
        print("\n🎉 Synchronisation terminée avec succès !")
    else:
        print("\n❌ La synchronisation a échoué")
        sys.exit(1)
