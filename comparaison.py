# comparator_v2.py - Version avec augmentation progressive
import mysql.connector
from datetime import datetime
import time
import sys

from database import connect_scraper

class ProductComparatorV2:
    def __init__(self):
        self.connection = None
        self.cursor = None
        
        # Règles d'augmentation progressive
        self.price_increase_rules = [
            (0, 500, 20),    # 0-500 DH : +20%
            (500, 1000, 15), # 500-1000 DH : +15%
            (1000, float('inf'), 9)  # +1000 DH : +9%
        ]
        
        self.stats = {
            'connection_status': False,
            'database_operations': {
                'inserted': 0,
                'updated': 0,
                'errors': 0
            },
            'price_categories': {
                '0-500dh': 0,
                '500-1000dh': 0,
                '1000+dh': 0
            },
            'tables_status': {
                'disty': False,
                'disway': False,
                'logicom': False
            }
        }
        
        print("✅ ProductComparatorV2 initialisé")
        print("📈 Règles d'augmentation:")
        print("   - 0-500 DH : +20%")
        print("   - 500-1000 DH : +15%")
        print("   - 1000+ DH : +9%")
    
    def connect_to_database(self) -> bool:
        """Établit la connexion à la base de données unique"""
        try:
            print("🔗 Connexion à la base de données unique...")
            self.connection = connect_scraper()
            
            if self.connection and self.connection.is_connected():
                self.cursor = self.connection.cursor(dictionary=True)
                self.stats['connection_status'] = True
                print("✅ Connexion réussie à la base unique")
                
                # Vérifier que les tables existent
                return self.verify_tables_existence()
            else:
                print("❌ Connexion échouée")
                return False
                
        except Exception as e:
            print(f"❌ Erreur connexion: {e}")
            return False
    
    def verify_tables_existence(self) -> bool:
        """Vérifie que les tables nécessaires existent"""
        try:
            required_tables = ['dix_disty', 'dix_disway', 'dix_logicom']
            existing_tables = []
            
            # Vérifier chaque table
            for table_name in required_tables:
                self.cursor.execute(f"""
                    SELECT COUNT(*) as table_exists 
                    FROM information_schema.tables 
                    WHERE table_schema = DATABASE() 
                    AND table_name = '{table_name}'
                """)
                result = self.cursor.fetchone()
                
                if result['table_exists'] > 0:
                    # Extraire le nom source (sans 'dix_')
                    source_name = table_name.replace('dix_', '')
                    self.stats['tables_status'][source_name] = True
                    existing_tables.append(table_name)
                    print(f"✅ Table trouvée: {table_name}")
                else:
                    print(f"❌ Table manquante: {table_name}")
            
            print(f"📊 Tables disponibles: {len(existing_tables)}/{len(required_tables)}")
            
            # Requiert au moins 2 tables pour fonctionner
            return len(existing_tables) >= 2
            
        except Exception as e:
            print(f"❌ Erreur vérification tables: {e}")
            return False
    
    def apply_progressive_increase(self, price):
        """Applique l'augmentation progressive selon les tranches"""
        if price and float(price) > 0:
            original_price = float(price)
            
            # Trouver la tranche correspondante
            for min_price, max_price, percentage in self.price_increase_rules:
                if min_price <= original_price < max_price:
                    increased_price = original_price * (1 + percentage / 100)
                    increased_price_rounded = round(increased_price, 2)
                    
                    # Statistiques
                    if min_price == 0:
                        self.stats['price_categories']['0-500dh'] += 1
                    elif min_price == 500:
                        self.stats['price_categories']['500-1000dh'] += 1
                    else:
                        self.stats['price_categories']['1000+dh'] += 1
                    
                    return increased_price_rounded
            
            # Par défaut (au-dessus de 1000)
            increased_price = original_price * 1.09
            self.stats['price_categories']['1000+dh'] += 1
            return round(increased_price, 2)
        return price
    
    def calculate_reduction(self, wholesale_price, price):
        """Calcule la réduction comme wholesale_price - price"""
        try:
            if (wholesale_price and float(wholesale_price) > 0 and 
                price and float(price) > 0):
                wholesale = float(wholesale_price)
                selling_price = float(price)
                
                reduction = wholesale - selling_price
                
                if reduction < 0:
                    return 0.0
                
                return round(reduction, 2)
            return 0.0
        except (ValueError, TypeError):
            return 0.0
    
    def get_all_products(self):
        """Récupère tous les produits des différentes tables"""
        if not self.stats['connection_status']:
            print("❌ Aucune connexion active")
            return None
        
        try:
            print("📥 Récupération des produits...")
            
            all_products = {}
            sources_count = {}
            
            # Liste des sources/tables disponibles
            sources = []
            if self.stats['tables_status']['disty']:
                sources.append(('disty', 'dix_disty'))
            if self.stats['tables_status']['disway']:
                sources.append(('disway', 'dix_disway'))
            if self.stats['tables_status']['logicom']:
                sources.append(('logicom', 'dix_logicom'))
            
            # Récupération depuis chaque table
            for source_name, table_name in sources:
                print(f"📥 Récupération des produits {source_name}...")
                
                query = f"""
                    SELECT id_product, reference, price, 
                           wholesale_price, reduction, quantity, marge_inf 
                    FROM {table_name} 
                    WHERE reference IS NOT NULL AND reference != ''
                """
                
                self.cursor.execute(query)
                products = self.cursor.fetchall()
                sources_count[source_name] = len(products)
                
                for product in products:
                    ref = product['reference'].strip()
                    if ref:
                        if ref not in all_products:
                            all_products[ref] = {}
                        
                        original_price = product['price']
                        original_wholesale = product['wholesale_price']
                        
                        # 🔥 Appliquer l'augmentation PROGRESSIVE
                        increased_price = self.apply_progressive_increase(original_price)
                        product['price'] = increased_price
                        
                        # Recalculer la réduction
                        product['reduction'] = self.calculate_reduction(original_wholesale, increased_price)
                        
                        all_products[ref][source_name] = product
            
            # Statistiques
            print("📊 Statistiques de récupération:")
            for source, count in sources_count.items():
                print(f"  {source.upper()}: {count} produits")
            print(f"  TOTAL: {len(all_products)} références uniques")
            
            return all_products
            
        except Exception as e:
            print(f"❌ Erreur récupération produits: {e}")
            return None
    
    def find_best_prices(self, all_products):
        """Trouve le meilleur produit (STOCK PRIORITAIRE sur prix)"""
        if not all_products:
            print("❌ Aucune donnée à analyser")
            return None
        
        try:
            print("🔍 Analyse des meilleurs produits (STOCK PRIORITAIRE)...")
            
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
                    
                elif sources_without_stock:
                    stats['without_stock_but_price'] += 1
                    # Si AUCUN stock, prendre le MEILLEUR PRIX parmi ceux sans stock
                    best_source = min(sources_without_stock.keys(), 
                                    key=lambda x: float(sources_without_stock[x]['price']))
                    best_data = sources_without_stock[best_source]
                else:
                    continue
                
                result = {
                    'reference': ref,
                    'best_source': best_source,
                    'id_product': best_data.get('id_product'),
                    'price': float(best_data['price']) if best_data.get('price') else 0.0,
                    'wholesale_price': float(best_data['wholesale_price']) if best_data.get('wholesale_price') else 0.0,
                    'reduction': float(best_data['reduction']) if best_data.get('reduction') else 0.0,
                    'quantity': int(best_data['quantity']) if best_data.get('quantity') else 0,
                    'marge_inf': bool(best_data.get('marge_inf', False)),
                    'has_stock': has_any_stock,
                    'all_sources': list(sources.keys()),
                    'sources_with_price': list(sources_with_price.keys()),
                    'sources_with_stock': list(sources_with_stock.keys())
                }
                
                best_prices_results.append(result)
            
            print(f"📈 Analyse terminée:")
            print(f"  ✅ Produits AVEC stock et prix: {stats['with_stock_and_price']}")
            print(f"  ⚠️  Produits SANS stock mais avec prix: {stats['without_stock_but_price']}")
            print(f"  ❌ Produits sans prix valide: {stats['no_price']}")
            print(f"  📦 Total analysé: {stats['total']}")
            
            return best_prices_results
            
        except Exception as e:
            print(f"❌ Erreur analyse prix: {e}")
            return None
    
    def save_to_v2_table(self, best_prices_results):
        """Sauvegarde les résultats dans la table V2"""
        if not best_prices_results:
            print("❌ Aucun résultat à sauvegarder")
            return False
        
        try:
            print("💾 Sauvegarde dans ps_products_comparison_V2...")
            
            # Vérifier si la table V2 existe, sinon la créer
            if not self.ensure_v2_table_exists():
                print("❌ Impossible de créer la table V2")
                return False
            
            inserted = 0
            updated = 0
            errors = 0
            
            for i, product in enumerate(best_prices_results, 1):
                try:
                    # Afficher la progression
                    if i % 100 == 0 or i <= 5 or i == len(best_prices_results):
                        progress_percent = (i / len(best_prices_results)) * 100
                        stock_status = "🟢" if product['has_stock'] else "🔴"
                        print(f"⏳ {stock_status} Progression: {i}/{len(best_prices_results)} ({progress_percent:.1f}%) - {product['reference']}")
                    
                    # Convertir les listes en chaînes
                    all_sources_str = ",".join(product['all_sources'])
                    sources_count = len(product['sources_with_price'])
                    
                    # Requête UPSERT pour la table V2
                    upsert_query = """
                    INSERT INTO ps_products_comparison_V2 
                    (reference, best_source, id_product, price, 
                     wholesale_price, reduction, quantity, marge_inf, has_stock, 
                     all_sources, sources_count, brand_id, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                    ON DUPLICATE KEY UPDATE
                    best_source = VALUES(best_source),
                    id_product = VALUES(id_product),
                    price = VALUES(price),
                    wholesale_price = VALUES(wholesale_price),
                    reduction = VALUES(reduction),
                    quantity = VALUES(quantity),
                    marge_inf = VALUES(marge_inf),
                    has_stock = VALUES(has_stock),
                    all_sources = VALUES(all_sources),
                    sources_count = VALUES(sources_count),
                    updated_at = NOW()
                    """
                    
                    values = (
                        product['reference'],
                        product['best_source'],
                        product['id_product'],
                        product['price'],
                        product['wholesale_price'],
                        product['reduction'],
                        product['quantity'],
                        product['marge_inf'],
                        product['has_stock'],
                        all_sources_str,
                        sources_count,
                        None  # brand_id
                    )
                    
                    self.cursor.execute(upsert_query, values)
                    
                    # Déterminer si c'est un INSERT ou UPDATE
                    rowcount = self.cursor.rowcount
                    if rowcount == 1:
                        inserted += 1
                    elif rowcount == 2:
                        updated += 1
                        
                except Exception as e:
                    errors += 1
                    print(f"❌ Erreur produit {product['reference']}: {e}")
                    continue
            
            # Commit final
            self.connection.commit()
            
            # Mettre à jour les statistiques
            self.stats['database_operations']['inserted'] = inserted
            self.stats['database_operations']['updated'] = updated
            self.stats['database_operations']['errors'] = errors
            
            print(f"✅ Sauvegarde V2 terminée:")
            print(f"  ✅ Nouveaux produits: {inserted}")
            print(f"  🔄 Produits mis à jour: {updated}")
            print(f"  ❌ Erreurs: {errors}")
            
            return True
            
        except Exception as e:
            print(f"❌ Erreur sauvegarde V2: {e}")
            return False

    def save_to_main_table(self, best_prices_results):
        """Sauvegarde les résultats calculés dans la table PRINCIPALE ps_products_comparison"""
        if not best_prices_results:
            return False
        
        try:
            print("💾 Sauvegarde dans ps_products_comparison (PRINCIPALE)...")
            
            # Vérifier que la table existe
            try:
                self.cursor.execute("SELECT 1 FROM ps_products_comparison LIMIT 1")
                self.cursor.fetchall() # Consommer le résultat
            except:
                print("❌ Table ps_products_comparison inexistante")
                return False
            
            inserted = 0
            updated = 0
            errors = 0
            
            for i, product in enumerate(best_prices_results, 1):
                try:
                    all_sources_str = ",".join(product['all_sources'])
                    sources_count = len(product['sources_with_price'])
                    
                    # Requête UPSERT pour la table principale
                    # On ne touche PAS au titre/desc/image ici pour ne pas écraser le travail des scrapers
                    upsert_query = """
                    INSERT INTO ps_products_comparison 
                    (reference, best_source, price, wholesale_price, reduction, 
                     quantity, marge_inf, has_stock, all_sources, sources_count, 
                     created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                    ON DUPLICATE KEY UPDATE
                    price = VALUES(price),
                    wholesale_price = VALUES(wholesale_price),
                    reduction = VALUES(reduction),
                    quantity = VALUES(quantity),
                    marge_inf = VALUES(marge_inf),
                    has_stock = VALUES(has_stock),
                    all_sources = VALUES(all_sources),
                    sources_count = VALUES(sources_count),
                    updated_at = NOW()
                    """
                    
                    values = (
                        product['reference'],
                        product['best_source'],
                        product['price'],
                        product['wholesale_price'],
                        product['reduction'],
                        product['quantity'],
                        product['marge_inf'],
                        product['has_stock'],
                        all_sources_str,
                        sources_count
                    )
                    
                    self.cursor.execute(upsert_query, values)
                    
                    if self.cursor.rowcount == 1:
                        inserted += 1
                    elif self.cursor.rowcount == 2:
                        updated += 1
                        
                except Exception as e:
                    errors += 1
                    # print(f"❌ Erreur table principale {product['reference']}: {e}")
                    continue
            
            self.connection.commit()
            
            print(f"✅ Sauvegarde Table Principale terminée:")
            print(f"  ✅ Nouveaux: {inserted}")
            print(f"  🔄 Mis à jour: {updated}")
            
            return True
            
        except Exception as e:
            print(f"❌ Erreur sauvegarde table principale: {e}")
            return False
    
    def ensure_v2_table_exists(self):
        """Vérifie et crée la table V2 si elle n'existe pas"""
        try:
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS ps_products_comparison_V2 (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    reference VARCHAR(64) UNIQUE NOT NULL,
                    best_source VARCHAR(50) NOT NULL,
                    id_product INT,
                    price DECIMAL(20,6) DEFAULT 0.000000,
                    wholesale_price DECIMAL(20,6) DEFAULT 0.000000,
                    reduction DECIMAL(20,6) DEFAULT 0.000000,
                    quantity INT DEFAULT 0,
                    marge_inf BOOLEAN DEFAULT FALSE,
                    has_stock BOOLEAN DEFAULT FALSE,
                    all_sources TEXT,
                    sources_count INT DEFAULT 1,
                    brand_id INT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_reference (reference),
                    INDEX idx_best_source (best_source),
                    INDEX idx_has_stock (has_stock),
                    INDEX idx_price (price),
                    INDEX idx_quantity (quantity)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("✅ Table ps_products_comparison_V2 vérifiée/créée")
            return True
        except Exception as e:
            print(f"❌ Erreur création table V2: {e}")
            return False
    
    def verify_v2_results(self):
        """Vérifie les résultats dans la table V2"""
        try:
            print("🔍 Vérification des résultats V2...")
            
            # Compter le total
            self.cursor.execute("SELECT COUNT(*) as total FROM ps_products_comparison_V2")
            total = self.cursor.fetchone()['total']
            
            # Statistiques par source
            self.cursor.execute("""
                SELECT best_source, COUNT(*) as count, 
                       AVG(price) as avg_price,
                       AVG(reduction) as avg_reduction,
                       SUM(has_stock) as with_stock
                FROM ps_products_comparison_V2 
                GROUP BY best_source
            """)
            source_stats = self.cursor.fetchall()
            
            # Produits avec plusieurs sources
            self.cursor.execute("SELECT COUNT(*) as multi_source FROM ps_products_comparison_V2 WHERE sources_count > 1")
            multi_source = self.cursor.fetchone()['multi_source']
            
            # Statistiques stock globales
            self.cursor.execute("SELECT COUNT(*) as total_with_stock FROM ps_products_comparison_V2 WHERE has_stock = TRUE")
            total_with_stock = self.cursor.fetchone()['total_with_stock']
            
            print(f"📊 VÉRIFICATION V2 TERMINÉE:")
            print(f"  Produits totaux: {total}")
            print(f"  Produits AVEC stock: {total_with_stock} ({(total_with_stock/total*100):.1f}%)")
            print(f"  Produits multi-sources: {multi_source} ({(multi_source/total*100):.1f}%)")
            
            print(f"\n📋 RÉPARTITION PAR SOURCE:")
            for stat in source_stats:
                stock_percentage = (stat['with_stock'] / stat['count']) * 100 if stat['count'] > 0 else 0
                print(f"  {stat['best_source'].upper():<8}: {stat['count']:>4} produits")
                print(f"           Prix moyen: {stat['avg_price']:.2f} DH")
                print(f"           Réduction moyenne: {stat['avg_reduction']:.2f} DH")
                print(f"           En stock: {stat['with_stock']} ({stock_percentage:.1f}%)")
            
            return total
            
        except Exception as e:
            print(f"❌ Erreur vérification V2: {e}")
            return 0
    
    def disconnect(self):
        """Ferme la connexion"""
        if self.cursor:
            self.cursor.close()
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print("🔌 Connexion fermée")

def main():
    """Fonction principale"""
    print("\n" + "="*70)
    print("🔄 COMPARATEUR V2 - AUGMENTATION PROGRESSIVE")
    print("🎯 STRATÉGIE: STOCK PRIORITAIRE sur prix")
    print("📈 RÈGLES D'AUGMENTATION:")
    print("   - 0-500 DH : +20% de marge")
    print("   - 500-1000 DH : +15% de marge")
    print("   - 1000+ DH : +9% de marge")
    print("="*70)
    
    start_time = time.time()
    
    comparator = ProductComparatorV2()
    
    try:
        # Établir la connexion unique
        if not comparator.connect_to_database():
            print("❌ Connexion impossible")
            return False
        
        # Récupérer tous les produits
        all_products = comparator.get_all_products()
        if not all_products:
            print("❌ Aucun produit récupéré")
            return False
        
        # Analyser les prix
        best_prices = comparator.find_best_prices(all_products)
        if not best_prices:
            print("❌ Aucun prix valide trouvé")
            return False
        
        # Sauvegarder dans la table V2
        if not comparator.save_to_v2_table(best_prices):
            print("❌ Erreur lors de la sauvegarde V2")
            return False
            
        # Sauvegarder dans la table PRINCIPALE
        if not comparator.save_to_main_table(best_prices):
            print("❌ Erreur lors de la sauvegarde table principale")
            return False
        
        # Vérifier les résultats
        total_saved = comparator.verify_v2_results()
        
        # Afficher le résumé final
        end_time = time.time()
        duration = end_time - start_time
        
        # Calculer les statistiques finales
        products_with_stock = sum(1 for p in best_prices if p['has_stock'])
        products_without_stock = len(best_prices) - products_with_stock
        
        print("\n" + "="*70)
        print("🎉 COMPARATEUR V2 TERMINÉ AVEC SUCCÈS!")
        print("="*70)
        print(f"⏱️  Durée totale: {duration:.2f} secondes")
        print(f"📦 Références analysées: {len(all_products)}")
        print(f"💰 Produits avec prix valide: {len(best_prices)}")
        print(f"💾 Produits en base (V2): {total_saved}")
        print(f"🟢 Produits AVEC stock: {products_with_stock} ({(products_with_stock/len(best_prices)*100):.1f}%)")
        print(f"🔴 Produits SANS stock: {products_without_stock} ({(products_without_stock/len(best_prices)*100):.1f}%)")
        print(f"✅ Nouveaux: {comparator.stats['database_operations']['inserted']}")
        print(f"🔄 Mis à jour: {comparator.stats['database_operations']['updated']}")
        print(f"❌ Erreurs: {comparator.stats['database_operations']['errors']}")
        
        # Afficher les statistiques des tranches de prix
        print(f"\n📊 RÉPARTITION DES PRIX (après augmentation):")
        print(f"  Tranche 0-500 DH: {comparator.stats['price_categories']['0-500dh']} produits")
        print(f"  Tranche 500-1000 DH: {comparator.stats['price_categories']['500-1000dh']} produits")
        print(f"  Tranche 1000+ DH: {comparator.stats['price_categories']['1000+dh']} produits")
        
        print("="*70)
        
        return True
        
    except Exception as e:
        print(f"💥 ERREUR CRITIQUE: {e}")
        return False
    
    finally:
        comparator.disconnect()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)