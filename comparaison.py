# comparator_v2.py - Version avec augmentation progressive
import mysql.connector
from datetime import datetime
import time
import sys

from database import get_disty_connection, get_disway_connection, get_logicom_connection, get_temp_connection

class ProductComparatorV2:
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
        
        # Règles d'augmentation progressive
        self.price_increase_rules = [
            (0, 500, 20),    # 0-500 DH : +20%
            (500, 1000, 15), # 500-1000 DH : +15%
            (1000, float('inf'), 9)  # +1000 DH : +9%
        ]
        
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
            'price_categories': {
                '0-500dh': 0,
                '500-1000dh': 0,
                '1000+dh': 0
            }
        }
        
        print("✅ ProductComparatorV2 initialisé")
        print("📈 Règles d'augmentation:")
        print("   - 0-500 DH : +20%")
        print("   - 500-1000 DH : +15%")
        print("   - 1000+ DH : +9%")
    
    def apply_progressive_increase(self, price):
        """Applique l'augmentation progressive selon les tranches"""
        if price and float(price) > 0:
            original_price = float(price)
            
            # Log pour debug
            original_price_rounded = round(original_price, 2)
            
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
    
    def connect_to_all_sources(self) -> bool:
        """Établit les connexions à toutes les bases de données"""
        successful_connections = 0
        
        try:
            print("🔗 Connexion à Disway...")
            self.connections['disway'] = get_disway_connection()
            if self.connections['disway'] and self.connections['disway'].is_connected():
                self.cursors['disway'] = self.connections['disway'].cursor(dictionary=True)
                self.stats['connection_status']['disway'] = True
                successful_connections += 1
                print("✅ Connexion Disway réussie")
            else:
                print("❌ Connexion Disway échouée")
        except Exception as e:
            print(f"❌ Erreur connexion Disway: {e}")
        
        try:
            print("🔗 Connexion à Disty...")
            self.connections['disty'] = get_disty_connection()
            if self.connections['disty'] and self.connections['disty'].is_connected():
                self.cursors['disty'] = self.connections['disty'].cursor(dictionary=True)
                self.stats['connection_status']['disty'] = True
                successful_connections += 1
                print("✅ Connexion Disty réussie")
            else:
                print("❌ Connexion Disty échouée")
        except Exception as e:
            print(f"❌ Erreur connexion Disty: {e}")
        
        try:
            print("🔗 Connexion à Logicom...")
            self.connections['logicom'] = get_logicom_connection()
            if self.connections['logicom'] and self.connections['logicom'].is_connected():
                self.cursors['logicom'] = self.connections['logicom'].cursor(dictionary=True)
                self.stats['connection_status']['logicom'] = True
                successful_connections += 1
                print("✅ Connexion Logicom réussie")
            else:
                print("❌ Connexion Logicom échouée")
        except Exception as e:
            print(f"❌ Erreur connexion Logicom: {e}")
        
        try:
            print("🔗 Connexion à la base Temp...")
            self.connections['temp'] = get_temp_connection()
            if self.connections['temp'] and self.connections['temp'].is_connected():
                self.cursors['temp'] = self.connections['temp'].cursor(dictionary=True)
                self.stats['connection_status']['temp'] = True
                successful_connections += 1
                print("✅ Connexion Temp réussie")
            else:
                print("❌ Connexion Temp échouée")
        except Exception as e:
            print(f"❌ Erreur connexion Temp: {e}")
        
        print(f"📊 Connexions réussies: {successful_connections}/4")
        return successful_connections >= 2
    
    def get_all_products(self):
        """Récupère tous les produits des différentes sources"""
        if not any(self.stats['connection_status'].values()):
            print("❌ Aucune connexion active")
            return None
        
        try:
            print("📥 Récupération des produits...")
            
            all_products = {}
            sources_count = {}
            
            # Récupération Disway
            if self.stats['connection_status']['disway']:
                print("📥 Récupération des produits Disway...")
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
                        
                        original_price = product['price']
                        original_wholesale = product['wholesale_price']
                        
                        # 🔥 Appliquer l'augmentation PROGRESSIVE
                        increased_price = self.apply_progressive_increase(original_price)
                        product['price'] = increased_price
                        
                        # Recalculer la réduction
                        product['reduction'] = self.calculate_reduction(original_wholesale, increased_price)
                        
                        all_products[ref]['disway'] = product
            
            # Récupération Disty
            if self.stats['connection_status']['disty']:
                print("📥 Récupération des produits Disty...")
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
                        
                        original_price = product['price']
                        original_wholesale = product['wholesale_price']
                        
                        # 🔥 Appliquer l'augmentation PROGRESSIVE
                        increased_price = self.apply_progressive_increase(original_price)
                        product['price'] = increased_price
                        
                        # Recalculer la réduction
                        product['reduction'] = self.calculate_reduction(original_wholesale, increased_price)
                        
                        all_products[ref]['disty'] = product
            
            # Récupération Logicom
            if self.stats['connection_status']['logicom']:
                print("📥 Récupération des produits Logicom...")
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
                        
                        original_price = product['price']
                        original_wholesale = product['wholesale_price']
                        
                        # 🔥 Appliquer l'augmentation PROGRESSIVE
                        increased_price = self.apply_progressive_increase(original_price)
                        product['price'] = increased_price
                        
                        # Recalculer la réduction
                        product['reduction'] = self.calculate_reduction(original_wholesale, increased_price)
                        
                        all_products[ref]['logicom'] = product
            
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
                    'id_category_default': best_data.get('id_category_default'),
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
                    (reference, best_source, id_product, id_category_default, price, 
                     wholesale_price, reduction, quantity, marge_inf, has_stock, 
                     all_sources, sources_count, brand_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                        sources_count,
                        None  # brand_id
                    )
                    
                    self.cursors['temp'].execute(upsert_query, values)
                    
                    # Déterminer si c'est un INSERT ou UPDATE
                    rowcount = self.cursors['temp'].rowcount
                    if rowcount == 1:
                        inserted += 1
                    elif rowcount == 2:
                        updated += 1
                        
                except Exception as e:
                    errors += 1
                    print(f"❌ Erreur produit {product['reference']}: {e}")
                    continue
            
            # Commit final
            self.connections['temp'].commit()
            
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
    
    def verify_v2_results(self):
        """Vérifie les résultats dans la table V2"""
        try:
            print("🔍 Vérification des résultats V2...")
            
            # Compter le total
            self.cursors['temp'].execute("SELECT COUNT(*) as total FROM ps_products_comparison_V2")
            total = self.cursors['temp'].fetchone()['total']
            
            # Statistiques par source
            self.cursors['temp'].execute("""
                SELECT best_source, COUNT(*) as count, 
                       AVG(price) as avg_price,
                       AVG(reduction) as avg_reduction,
                       SUM(has_stock) as with_stock
                FROM ps_products_comparison_V2 
                GROUP BY best_source
            """)
            source_stats = self.cursors['temp'].fetchall()
            
            # Produits avec plusieurs sources
            self.cursors['temp'].execute("SELECT COUNT(*) as multi_source FROM ps_products_comparison_V2 WHERE sources_count > 1")
            multi_source = self.cursors['temp'].fetchone()['multi_source']
            
            # Statistiques stock globales
            self.cursors['temp'].execute("SELECT COUNT(*) as total_with_stock FROM ps_products_comparison_V2 WHERE has_stock = TRUE")
            total_with_stock = self.cursors['temp'].fetchone()['total_with_stock']
            
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
    
    def disconnect_all(self):
        """Ferme toutes les connexions"""
        for source, cursor in self.cursors.items():
            if cursor:
                cursor.close()
        
        print("🔌 Toutes les connexions fermées")

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
        # Établir les connexions
        if not comparator.connect_to_all_sources():
            print("❌ Connexions insuffisantes")
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
            print("❌ Erreur lors de la sauvegarde")
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
        comparator.disconnect_all()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)