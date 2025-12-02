# comparator.py
import mysql.connector
from datetime import datetime
import logging
from typing import Dict, List, Any, Optional
import time
import sys
import re

# Utiliser votre nouveau gestionnaire de connexions
from database import get_disty_connection, get_disway_connection, get_logicom_connection, get_temp_connection

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('product_comparison.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

class ProductComparator:
    def __init__(self):
        self.connections = {
            'disway': None,
            'disty': None, 
            'logicom': None,
            'temp': None
        }
        self.cursors = {
            'disway': None,
            'disty': None,
            'logicom': None,
            'temp': None
        }
        self.logger = logging.getLogger(__name__)
        
        # Configuration de l'augmentation
        self.price_increase_percentage = 9  # 9% d'augmentation sur le prix seulement
        
        self.stats = {
            'connection_status': {
                'disway': False,
                'disty': False,
                'logicom': False,
                'temp': False
            },
            'database_operations': {
                'inserted': 0,
                'updated': 0,
                'errors': 0
            },
            'price_adjustments': {
                'total_adjusted': 0,
                'total_original_price': 0,
                'total_new_price': 0
            }
        }
        
        self.logger.info("ProductComparator initialisé avec augmentation de 9% sur prix seulement")
    
    def apply_price_increase(self, price):
        """Applique une augmentation de 9% sur le prix"""
        if price and float(price) > 0:
            original_price = float(price)
            increased_price = original_price * (1 + self.price_increase_percentage / 100)
            return round(increased_price, 2)
        return price
    
    def calculate_reduction(self, wholesale_price, price):
        """Calcule la réduction comme wholesale_price - price"""
        try:
            if (wholesale_price and float(wholesale_price) > 0 and 
                price and float(price) > 0):
                wholesale = float(wholesale_price)
                selling_price = float(price)
                
                # Réduction = Prix de gros - Prix de vente
                reduction = wholesale - selling_price
                
                # Si la réduction est négative, mettre à 0
                if reduction < 0:
                    return 0.0
                
                return round(reduction, 2)
            return 0.0
        except (ValueError, TypeError):
            return 0.0
    
    def connect_to_all_sources(self) -> bool:
        """Établit les connexions à toutes les bases de données"""
        successful_connections = 0
        
        try:
            self.logger.info("Tentative de connexion à Disway...")
            self.connections['disway'] = get_disway_connection()
            if self.connections['disway'] and self.connections['disway'].is_connected():
                self.cursors['disway'] = self.connections['disway'].cursor(dictionary=True)
                self.stats['connection_status']['disway'] = True
                successful_connections += 1
                self.logger.info("✅ Connexion Disway réussie")
            else:
                self.logger.error("❌ Connexion Disway échouée")
        except Exception as e:
            self.logger.error(f"❌ Erreur connexion Disway: {e}")
        
        try:
            self.logger.info("Tentative de connexion à Disty...")
            self.connections['disty'] = get_disty_connection()
            if self.connections['disty'] and self.connections['disty'].is_connected():
                self.cursors['disty'] = self.connections['disty'].cursor(dictionary=True)
                self.stats['connection_status']['disty'] = True
                successful_connections += 1
                self.logger.info("✅ Connexion Disty réussie")
            else:
                self.logger.error("❌ Connexion Disty échouée")
        except Exception as e:
            self.logger.error(f"❌ Erreur connexion Disty: {e}")
        
        try:
            self.logger.info("Tentative de connexion à Logicom...")
            self.connections['logicom'] = get_logicom_connection()
            if self.connections['logicom'] and self.connections['logicom'].is_connected():
                self.cursors['logicom'] = self.connections['logicom'].cursor(dictionary=True)
                self.stats['connection_status']['logicom'] = True
                successful_connections += 1
                self.logger.info("✅ Connexion Logicom réussie")
            else:
                self.logger.error("❌ Connexion Logicom échouée")
        except Exception as e:
            self.logger.error(f"❌ Erreur connexion Logicom: {e}")
        
        try:
            self.logger.info("Tentative de connexion à la base Temp...")
            self.connections['temp'] = get_temp_connection()
            if self.connections['temp'] and self.connections['temp'].is_connected():
                self.cursors['temp'] = self.connections['temp'].cursor(dictionary=True)
                self.stats['connection_status']['temp'] = True
                successful_connections += 1
                self.logger.info("✅ Connexion Temp réussie")
            else:
                self.logger.error("❌ Connexion Temp échouée")
        except Exception as e:
            self.logger.error(f"❌ Erreur connexion Temp: {e}")
        
        self.logger.info(f"📊 Connexions réussies: {successful_connections}/4")
        return successful_connections >= 2  # Au moins 2 connexions nécessaires
    
    def ensure_comparison_table(self):
        """Crée la table de comparaison si elle n'existe pas"""
        try:
            create_table_query = """
            CREATE TABLE IF NOT EXISTS ps_products_comparison (
                id INT AUTO_INCREMENT PRIMARY KEY,
                reference VARCHAR(100) UNIQUE NOT NULL,
                best_source VARCHAR(20) NOT NULL,
                id_product INT,
                id_category_default INT,
                price DECIMAL(10,2),
                wholesale_price DECIMAL(10,2),
                reduction DECIMAL(10,2),
                quantity INT,
                marge_inf BOOLEAN DEFAULT FALSE,
                has_stock BOOLEAN DEFAULT FALSE,
                all_sources TEXT,
                sources_count INT DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_reference (reference),
                INDEX idx_best_source (best_source),
                INDEX idx_price (price),
                INDEX idx_has_stock (has_stock)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
            
            self.cursors['temp'].execute(create_table_query)
            self.connections['temp'].commit()
            self.logger.info("✅ Table de comparaison vérifiée/créée")
            
        except Exception as e:
            self.logger.error(f"❌ Erreur création table: {e}")
            raise
    
    def get_all_products(self):
        """Récupère tous les produits des différentes sources"""
        if not any(self.stats['connection_status'].values()):
            self.logger.error("❌ Aucune connexion active")
            return None
        
        try:
            self.logger.info("📥 Récupération des produits...")
            
            all_products = {}
            sources_count = {}
            
            # Récupération Disway
            if self.stats['connection_status']['disway']:
                self.logger.info("Récupération des produits Disway...")
                self.cursors['disway'].execute("""
                    SELECT id_product, reference, id_category_default, price, 
                           wholesale_price, reduction, quantity, marge_inf 
                    FROM ps_product 
                    WHERE reference IS NOT NULL AND reference != ''
                """)
                disway_products = self.cursors['disway'].fetchall()
                sources_count['disway'] = len(disway_products)
                
                for product in disway_products:
                    ref = product['reference'].strip()
                    if ref:
                        if ref not in all_products:
                            all_products[ref] = {}
                        
                        # Appliquer l'augmentation de 9% sur le prix seulement
                        original_price = product['price']
                        original_wholesale = product['wholesale_price']
                        
                        # Augmenter le prix de 9%
                        increased_price = self.apply_price_increase(original_price)
                        product['price'] = increased_price
                        
                        # Recalculer la réduction: wholesale_price - price
                        product['reduction'] = self.calculate_reduction(original_wholesale, increased_price)
                        
                        # Log pour debug
                        if ref in ['TEST001', 'TEST002']:  # Exemple pour quelques produits
                            self.logger.debug(f"🔄 Disway {ref}: Prix {original_price} → {increased_price} | Réduction recalculée")
                        
                        all_products[ref]['disway'] = product
            
            # Récupération Disty
            if self.stats['connection_status']['disty']:
                self.logger.info("Récupération des produits Disty...")
                self.cursors['disty'].execute("""
                    SELECT id_product, reference, id_category_default, price, 
                           wholesale_price, reduction, quantity, marge_inf 
                    FROM ps_product 
                    WHERE reference IS NOT NULL AND reference != ''
                """)
                disty_products = self.cursors['disty'].fetchall()
                sources_count['disty'] = len(disty_products)
                
                for product in disty_products:
                    ref = product['reference'].strip()
                    if ref:
                        if ref not in all_products:
                            all_products[ref] = {}
                        
                        # Appliquer l'augmentation de 9% sur le prix seulement
                        original_price = product['price']
                        original_wholesale = product['wholesale_price']
                        
                        # Augmenter le prix de 9%
                        increased_price = self.apply_price_increase(original_price)
                        product['price'] = increased_price
                        
                        # Recalculer la réduction: wholesale_price - price
                        product['reduction'] = self.calculate_reduction(original_wholesale, increased_price)
                        
                        all_products[ref]['disty'] = product
            
            # Récupération Logicom
            if self.stats['connection_status']['logicom']:
                self.logger.info("Récupération des produits Logicom...")
                self.cursors['logicom'].execute("""
                    SELECT id_product, reference, id_category_default, price, 
                           wholesale_price, reduction, quantity, marge_inf 
                    FROM ps_product 
                    WHERE reference IS NOT NULL AND reference != ''
                """)
                logicom_products = self.cursors['logicom'].fetchall()
                sources_count['logicom'] = len(logicom_products)
                
                for product in logicom_products:
                    ref = product['reference'].strip()
                    if ref:
                        if ref not in all_products:
                            all_products[ref] = {}
                        
                        # Appliquer l'augmentation de 9% sur le prix seulement
                        original_price = product['price']
                        original_wholesale = product['wholesale_price']
                        
                        # Augmenter le prix de 9%
                        increased_price = self.apply_price_increase(original_price)
                        product['price'] = increased_price
                        
                        # Recalculer la réduction: wholesale_price - price
                        product['reduction'] = self.calculate_reduction(original_wholesale, increased_price)
                        
                        all_products[ref]['logicom'] = product
            
            # Log des statistiques
            self.logger.info("📊 Statistiques de récupération:")
            for source, count in sources_count.items():
                self.logger.info(f"  {source.upper()}: {count} produits")
            self.logger.info(f"  TOTAL: {len(all_products)} références uniques")
            
            # Afficher quelques exemples d'augmentation
            self.logger.info(f"\n📈 EXEMPLES D'AUGMENTATION +9%:")
            sample_count = 0
            for ref, sources in list(all_products.items())[:3]:  # Prendre 3 exemples
                for source, product in sources.items():
                    if sample_count < 3:
                        original_price_approx = product['price'] / 1.09  # Calcul inverse pour l'exemple
                        self.logger.info(f"  {ref} ({source}): {original_price_approx:.2f} DH → {product['price']:.2f} DH | Réduction: {product['reduction']:.2f} DH")
                        sample_count += 1
            
            return all_products
            
        except Exception as e:
            self.logger.error(f"❌ Erreur récupération produits: {e}")
            return None
    
    def find_best_prices(self, all_products):
        """Trouve le meilleur produit (STOCK PRIORITAIRE sur prix)"""
        if not all_products:
            self.logger.error("❌ Aucune donnée à analyser")
            return None
        
        try:
            self.logger.info("🔍 Analyse des meilleurs produits (STOCK PRIORITAIRE)...")
            
            best_prices_results = []
            stats = {
                'total': 0, 
                'with_stock_and_price': 0,
                'without_stock_but_price': 0,
                'no_price': 0
            }
            
            for ref, sources in all_products.items():
                stats['total'] += 1
                
                # Étape 1: Filtrer les sources avec prix valide
                sources_with_price = {}
                for source, data in sources.items():
                    if data.get('price') and float(data['price']) > 0:
                        sources_with_price[source] = data
                
                if not sources_with_price:
                    stats['no_price'] += 1
                    continue
                
                # Étape 2: SÉPARER les sources AVEC stock et SANS stock
                sources_with_stock = {}
                sources_without_stock = {}
                
                for source, data in sources_with_price.items():
                    quantity = data.get('quantity', 0)
                    # Convertir en int et vérifier si > 0
                    try:
                        qty_int = int(quantity) if quantity is not None else 0
                        if qty_int > 0:
                            sources_with_stock[source] = data
                        else:
                            sources_without_stock[source] = data
                    except (ValueError, TypeError):
                        sources_without_stock[source] = data
                
                # Étape 3: LOGIQUE INTELLIGENTE - PRIORITÉ AU STOCK
                best_source = None
                best_data = None
                has_any_stock = len(sources_with_stock) > 0
                
                if sources_with_stock:
                    stats['with_stock_and_price'] += 1
                    # Parmi les sources AVEC stock, prendre le MEILLEUR PRIX (plus bas)
                    best_source = min(sources_with_stock.keys(), 
                                    key=lambda x: float(sources_with_stock[x]['price']))
                    best_data = sources_with_stock[best_source]
                    self.logger.debug(f"  ✅ {ref}: Choix AVEC stock - {best_source} (prix: {best_data['price']})")
                    
                elif sources_without_stock:
                    stats['without_stock_but_price'] += 1
                    # Si AUCUN stock, prendre le MEILLEUR PRIX parmi ceux sans stock
                    best_source = min(sources_without_stock.keys(), 
                                    key=lambda x: float(sources_without_stock[x]['price']))
                    best_data = sources_without_stock[best_source]
                    self.logger.debug(f"  ⚠️  {ref}: Choix SANS stock - {best_source} (prix: {best_data['price']})")
                else:
                    continue
                
                result = {
                    'reference': ref,
                    'best_source': best_source,
                    'id_product': best_data.get('id_product'),
                    'id_category_default': best_data.get('id_category_default'),
                    'price': float(best_data['price']) if best_data.get('price') else 0.0,
                    'wholesale_price': float(best_data['wholesale_price']) if best_data.get('wholesale_price') else 0.0,
                    'reduction': float(best_data['reduction']) if best_data.get('reduction') else 0.0,
                    'quantity': int(best_data['quantity']) if best_data.get('quantity') else 0,
                    'marge_inf': bool(best_data.get('marge_inf', False)),
                    'has_stock': has_any_stock,  # TRUE si au moins une source a du stock
                    'all_sources': list(sources.keys()),
                    'sources_with_price': list(sources_with_price.keys()),
                    'sources_with_stock': list(sources_with_stock.keys())  # NOUVEAU: sources qui ont du stock
                }
                
                best_prices_results.append(result)
            
            self.logger.info(f"📈 Analyse AVEC STOCK terminée:")
            self.logger.info(f"  ✅ Produits AVEC stock et prix: {stats['with_stock_and_price']}")
            self.logger.info(f"  ⚠️  Produits SANS stock mais avec prix: {stats['without_stock_but_price']}")
            self.logger.info(f"  ❌ Produits sans prix valide: {stats['no_price']}")
            self.logger.info(f"  📦 Total analysé: {stats['total']}")
            
            # Afficher quelques exemples de décisions
            if best_prices_results:
                self.logger.info(f"\n🎯 Exemples de décisions (après +9%):")
                for i, product in enumerate(best_prices_results[:5]):
                    stock_status = "🟢 AVEC STOCK" if product['has_stock'] else "🔴 SANS STOCK"
                    self.logger.info(f"  {i+1}. {product['reference']} → {product['best_source']} ({stock_status}) - Prix: {product['price']} DH | Réduction: {product['reduction']} DH")
            
            return best_prices_results
            
        except Exception as e:
            self.logger.error(f"❌ Erreur analyse prix: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return None
    
    def save_comparison_results(self, best_prices_results):
        """Sauvegarde les résultats de comparaison"""
        if not best_prices_results:
            self.logger.error("❌ Aucun résultat à sauvegarder")
            return False
        
        try:
            self.logger.info("💾 Sauvegarde des résultats...")
            
            # S'assurer que la table existe
            self.ensure_comparison_table()
            
            inserted = 0
            updated = 0
            errors = 0
            
            for i, product in enumerate(best_prices_results, 1):
                try:
                    # Afficher la progression
                    if i % 100 == 0 or i <= 5 or i == len(best_prices_results):
                        progress_percent = (i / len(best_prices_results)) * 100
                        stock_status = "🟢" if product['has_stock'] else "🔴"
                        self.logger.info(f"⏳ {stock_status} Progression: {i}/{len(best_prices_results)} ({progress_percent:.1f}%) - {product['reference']}")
                    
                    # Convertir les listes en chaînes
                    all_sources_str = ",".join(product['all_sources'])
                    sources_count = len(product['sources_with_price'])
                    
                    # Requête UPSERT
                    upsert_query = """
                    INSERT INTO ps_products_comparison 
                    (reference, best_source, id_product, id_category_default, price, 
                     wholesale_price, reduction, quantity, marge_inf, has_stock, 
                     all_sources, sources_count)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    best_source = VALUES(best_source),
                    id_product = VALUES(id_product),
                    id_category_default = VALUES(id_category_default),
                    price = VALUES(price),
                    wholesale_price = VALUES(wholesale_price),
                    reduction = VALUES(reduction),
                    quantity = VALUES(quantity),
                    marge_inf = VALUES(marge_inf),
                    has_stock = VALUES(has_stock),
                    all_sources = VALUES(all_sources),
                    sources_count = VALUES(sources_count),
                    updated_at = CURRENT_TIMESTAMP
                    """
                    
                    values = (
                        product['reference'],
                        product['best_source'],
                        product['id_product'],
                        product['id_category_default'],
                        product['price'],
                        product['wholesale_price'],
                        product['reduction'],
                        product['quantity'],
                        product['marge_inf'],
                        product['has_stock'],
                        all_sources_str,
                        sources_count
                    )
                    
                    self.cursors['temp'].execute(upsert_query, values)
                    
                    # Déterminer si c'est un INSERT ou UPDATE
                    rowcount = self.cursors['temp'].rowcount
                    if rowcount == 1:
                        inserted += 1
                        if i <= 3:  # Afficher les 3 premiers INSERT pour debug
                            self.logger.info(f"    ✅ NOUVEAU: {product['reference']} → {product['best_source']} (Prix: {product['price']} DH | Réduction: {product['reduction']} DH)")
                    elif rowcount == 2:
                        updated += 1
                        if i <= 3:  # Afficher les 3 premiers UPDATE pour debug
                            self.logger.info(f"    🔄 MISE À JOUR: {product['reference']} → {product['best_source']} (Prix: {product['price']} DH | Réduction: {product['reduction']} DH)")
                    else:
                        self.logger.warning(f"    ⚠️  Rowcount inattendu {rowcount} pour {product['reference']}")
                        
                except Exception as e:
                    errors += 1
                    self.logger.error(f"❌ Erreur produit {product['reference']}: {e}")
                    continue
            
            # Commit final
            self.connections['temp'].commit()
            
            # Mettre à jour les statistiques
            self.stats['database_operations']['inserted'] = inserted
            self.stats['database_operations']['updated'] = updated
            self.stats['database_operations']['errors'] = errors
            
            self.logger.info(f"✅ Sauvegarde terminée:")
            self.logger.info(f"  ✅ Nouveaux produits: {inserted}")
            self.logger.info(f"  🔄 Produits mis à jour: {updated}")
            self.logger.info(f"  ❌ Erreurs: {errors}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erreur sauvegarde générale: {e}")
            return False
    
    def verify_results(self):
        """Vérifie les résultats sauvegardés"""
        try:
            self.logger.info("🔍 Vérification des résultats...")
            
            # Compter le total
            self.cursors['temp'].execute("SELECT COUNT(*) as total FROM ps_products_comparison")
            total = self.cursors['temp'].fetchone()['total']
            
            # Statistiques par source
            self.cursors['temp'].execute("""
                SELECT best_source, COUNT(*) as count, 
                       AVG(price) as avg_price,
                       AVG(reduction) as avg_reduction,
                       SUM(has_stock) as with_stock
                FROM ps_products_comparison 
                GROUP BY best_source
            """)
            source_stats = self.cursors['temp'].fetchall()
            
            # Produits avec plusieurs sources
            self.cursors['temp'].execute("SELECT COUNT(*) as multi_source FROM ps_products_comparison WHERE sources_count > 1")
            multi_source = self.cursors['temp'].fetchone()['multi_source']
            
            # Statistiques stock globales
            self.cursors['temp'].execute("SELECT COUNT(*) as total_with_stock FROM ps_products_comparison WHERE has_stock = TRUE")
            total_with_stock = self.cursors['temp'].fetchone()['total_with_stock']
            
            self.logger.info(f"📊 VÉRIFICATION TERMINÉE:")
            self.logger.info(f"  Produits totaux: {total}")
            self.logger.info(f"  Produits AVEC stock: {total_with_stock} ({(total_with_stock/total*100):.1f}%)")
            self.logger.info(f"  Produits multi-sources: {multi_source} ({(multi_source/total*100):.1f}%)")
            
            self.logger.info(f"\n📋 RÉPARTITION PAR SOURCE:")
            for stat in source_stats:
                stock_percentage = (stat['with_stock'] / stat['count']) * 100 if stat['count'] > 0 else 0
                self.logger.info(f"  {stat['best_source'].upper():<8}: {stat['count']:>4} produits")
                self.logger.info(f"           Prix moyen: {stat['avg_price']:.2f} DH")
                self.logger.info(f"           Réduction moyenne: {stat['avg_reduction']:.2f} DH")
                self.logger.info(f"           En stock: {stat['with_stock']} ({stock_percentage:.1f}%)")
            
            # Afficher quelques exemples récents
            self.cursors['temp'].execute("""
                SELECT reference, best_source, price, reduction, quantity, has_stock, updated_at 
                FROM ps_products_comparison 
                ORDER BY updated_at DESC 
                LIMIT 5
            """)
            recent_products = self.cursors['temp'].fetchall()
            
            if recent_products:
                self.logger.info(f"\n🆕 PRODUITS RÉCEMMENTS MIS À JOUR:")
                for product in recent_products:
                    stock_icon = "🟢" if product['has_stock'] else "🔴"
                    self.logger.info(f"  {stock_icon} {product['reference']:15} → {product['best_source']:8} | Prix: {product['price']:6.2f} DH | Réduction: {product['reduction']:6.2f} DH | Stock: {product['quantity']}")
            
            return total
            
        except Exception as e:
            self.logger.error(f"❌ Erreur vérification: {e}")
            return 0
    
    def disconnect_all(self):
        """Ferme toutes les connexions"""
        for source, cursor in self.cursors.items():
            if cursor:
                cursor.close()
                self.logger.info(f"🔌 Curseur {source} fermé")
        
        # Note: Avec DatabaseManager, les connexions sont gérées automatiquement
        self.logger.info("🔌 Toutes les connexions fermées")

def main():
    """Fonction principale"""
    print("\n" + "="*70)
    print("🔄 COMPARATEUR DE PRODUITS INTELLIGENT")
    print("🎯 STRATÉGIE: STOCK PRIORITAIRE sur prix")
    print(f"📈 CONFIGURATION: AUGMENTATION DE 9% sur prix + réduction = wholesale_price - price")
    print("="*70)
    
    start_time = time.time()
    
    comparator = ProductComparator()
    
    try:
        # Établir les connexions
        if not comparator.connect_to_all_sources():
            print("❌ Connexions insuffisantes pour continuer")
            return False
        
        # Récupérer tous les produits
        all_products = comparator.get_all_products()
        if not all_products:
            print("❌ Aucun produit récupéré")
            return False
        
        # Analyser les prix AVEC LOGIQUE INTELLIGENTE
        best_prices = comparator.find_best_prices(all_products)
        if not best_prices:
            print("❌ Aucun prix valide trouvé")
            return False
        
        # Sauvegarder les résultats
        if not comparator.save_comparison_results(best_prices):
            print("❌ Erreur lors de la sauvegarde")
            return False
        
        # Vérifier les résultats
        total_saved = comparator.verify_results()
        
        # Afficher le résumé final
        end_time = time.time()
        duration = end_time - start_time
        
        # Calculer les statistiques finales
        products_with_stock = sum(1 for p in best_prices if p['has_stock'])
        products_without_stock = len(best_prices) - products_with_stock
        
        print("\n" + "="*70)
        print("🎉 COMPARATEUR INTELLIGENT TERMINÉ AVEC SUCCÈS!")
        print("="*70)
        print(f"⏱️  Durée totale: {duration:.2f} secondes")
        print(f"📦 Références analysées: {len(all_products)}")
        print(f"💰 Produits avec prix valide: {len(best_prices)}")
        print(f"💾 Produits en base: {total_saved}")
        print(f"🟢 Produits AVEC stock: {products_with_stock} ({(products_with_stock/len(best_prices)*100):.1f}%)")
        print(f"🔴 Produits SANS stock: {products_without_stock} ({(products_without_stock/len(best_prices)*100):.1f}%)")
        print(f"✅ Nouveaux: {comparator.stats['database_operations']['inserted']}")
        print(f"🔄 Mis à jour: {comparator.stats['database_operations']['updated']}")
        print(f"❌ Erreurs: {comparator.stats['database_operations']['errors']}")
        print(f"📈 Augmentation appliquée: {comparator.price_increase_percentage}% sur prix seulement")
        print(f"🎯 Réduction calculée: wholesale_price - price")
        print("="*70)
        
        return True
        
    except Exception as e:
        print(f"💥 ERREUR CRITIQUE: {e}")
        import traceback
        print(traceback.format_exc())
        return False
    
    finally:
        comparator.disconnect_all()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)