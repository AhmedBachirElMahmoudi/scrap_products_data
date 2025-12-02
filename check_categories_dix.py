#!/usr/bin/env python3
"""
Script pour CORRIGER les id_category_default basé sur les subcategories
"""

import mysql.connector
from database import get_temp_connection
import logging
import sys
import time
from typing import Dict, List, Optional

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('fix_categories.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

class CategoryFixer:
    def __init__(self):
        self.conn = None
        self.cursor = None
        self.logger = logging.getLogger(__name__)
        self.stats = {
            'total_products': 0,
            'products_processed': 0,
            'categories_fixed': 0,
            'already_correct': 0,
            'no_match_found': 0,
            'errors': 0
        }
    
    def connect(self):
        """Établit la connexion à la base de données"""
        try:
            self.conn = get_temp_connection()
            if self.conn and self.conn.is_connected():
                self.cursor = self.conn.cursor(dictionary=True)
                self.logger.info("✅ Connexion à la base de données réussie")
                return True
            else:
                self.logger.error("❌ Échec de connexion à la base de données")
                return False
        except Exception as e:
            self.logger.error(f"❌ Erreur de connexion: {e}")
            return False
    
    def get_category_mapping(self) -> Dict:
        """Récupère le mapping des catégories depuis categories_scrap"""
        try:
            self.cursor.execute("SELECT nom_scrap, id_categorie_dix FROM categories_scrap")
            results = self.cursor.fetchall()
            
            mapping_exact = {}
            mapping_lower = {}
            
            for row in results:
                nom_scrap = row['nom_scrap']
                id_categorie = row['id_categorie_dix']
                
                mapping_exact[nom_scrap] = id_categorie
                mapping_lower[nom_scrap.lower()] = id_categorie
            
            self.logger.info(f"📊 Mapping chargé: {len(mapping_exact)} catégories")
            return {
                'exact': mapping_exact,
                'lower': mapping_lower
            }
            
        except Exception as e:
            self.logger.error(f"❌ Erreur chargement mapping: {e}")
            return {'exact': {}, 'lower': {}}
    
    def get_products_to_fix(self):
        """Récupère les produits avec subcategories qui peuvent avoir des IDs invalides"""
        try:
            query = """
            SELECT 
                id,
                reference,
                subcategories,
                id_category_default
            FROM ps_products_comparison 
            WHERE subcategories IS NOT NULL 
            AND subcategories != ''
            AND LENGTH(subcategories) > 0
            """
            
            self.cursor.execute(query)
            products = self.cursor.fetchall()
            
            self.logger.info(f"📦 {len(products)} produits avec subcategories trouvés")
            return products
            
        except Exception as e:
            self.logger.error(f"❌ Erreur récupération produits: {e}")
            return []
    
    def find_category_match(self, subcategories_str: str, mapping: Dict) -> Optional[int]:
        """Trouve la correspondance de catégorie pour les subcategories"""
        if not subcategories_str:
            return None
        
        # Essayer la correspondance exacte d'abord
        if subcategories_str in mapping['exact']:
            return mapping['exact'][subcategories_str]
        
        # Essayer en minuscules
        subcategories_lower = subcategories_str.lower()
        if subcategories_lower in mapping['lower']:
            return mapping['lower'][subcategories_lower]
        
        # Si la subcategory contient des virgules, essayer chaque partie
        if ',' in subcategories_str:
            subcategories = [s.strip() for s in subcategories_str.split(',')]
            for subcat in subcategories:
                if subcat in mapping['exact']:
                    return mapping['exact'][subcat]
                subcat_lower = subcat.lower()
                if subcat_lower in mapping['lower']:
                    return mapping['lower'][subcat_lower]
        
        return None
    
    def update_product_category(self, product_id: int, reference: str, new_category_id: int, old_category_id: int):
        """Met à jour l'id_category_default d'un produit"""
        try:
            query = """
            UPDATE ps_products_comparison 
            SET id_category_default = %s, 
                updated_at = CURRENT_TIMESTAMP 
            WHERE id = %s
            """
            
            self.cursor.execute(query, (new_category_id, product_id))
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erreur mise à jour produit {reference}: {e}")
            return False
    
    def fix_categories(self):
        """Corrige les catégories basé sur les subcategories"""
        # Charger le mapping
        category_mapping = self.get_category_mapping()
        if not category_mapping['exact']:
            self.logger.error("❌ Aucun mapping chargé")
            return False
        
        # Récupérer les produits
        products = self.get_products_to_fix()
        if not products:
            self.logger.warning("⚠️ Aucun produit à corriger trouvé")
            return True
        
        self.stats['total_products'] = len(products)
        
        self.logger.info("🔧 Début de la correction des catégories...")
        
        for i, product in enumerate(products, 1):
            try:
                product_id = product['id']
                reference = product['reference']
                subcategories = product['subcategories']
                current_category = product['id_category_default']
                
                # Afficher la progression
                if i % 100 == 0 or i <= 10 or i == len(products):
                    progress = (i / len(products)) * 100
                    self.logger.info(f"⏳ Progression: {i}/{len(products)} ({progress:.1f}%)")
                
                self.stats['products_processed'] += 1
                
                # Trouver la correspondance
                correct_category = self.find_category_match(subcategories, category_mapping)
                
                if correct_category:
                    # Vérifier si la catégorie doit être mise à jour
                    if current_category != correct_category:
                        if self.update_product_category(product_id, reference, correct_category, current_category):
                            self.stats['categories_fixed'] += 1
                            self.logger.info(f"🔄 CORRIGÉ: {reference}")
                            self.logger.info(f"   Subcategories: {subcategories}")
                            self.logger.info(f"   Ancien ID: {current_category} → Nouvel ID: {correct_category}")
                        else:
                            self.stats['errors'] += 1
                    else:
                        self.stats['already_correct'] += 1
                        if i <= 5:  # Log seulement les 5 premiers pour éviter le spam
                            self.logger.debug(f"✅ DÉJÀ CORRECT: {reference} (ID: {current_category})")
                else:
                    self.stats['no_match_found'] += 1
                    if i <= 5:  # Log seulement les 5 premiers pour éviter le spam
                        self.logger.warning(f"❌ AUCUN MATCH: {reference}")
                        self.logger.warning(f"   Subcategories: {subcategories}")
                
            except Exception as e:
                self.stats['errors'] += 1
                self.logger.error(f"❌ Erreur produit {product.get('reference', 'N/A')}: {e}")
                continue
        
        # Commit final
        self.conn.commit()
        self.logger.info("💾 Toutes les modifications sauvegardées")
        
        return True
    
    def show_statistics(self):
        """Affiche les statistiques finales"""
        self.logger.info("\n" + "="*60)
        self.logger.info("📊 RAPPORT DE CORRECTION")
        self.logger.info("="*60)
        self.logger.info(f"📦 Produits traités: {self.stats['products_processed']}")
        self.logger.info(f"🔄 Catégories corrigées: {self.stats['categories_fixed']}")
        self.logger.info(f"✅ Déjà correctes: {self.stats['already_correct']}")
        self.logger.info(f"❌ Aucune correspondance: {self.stats['no_match_found']}")
        self.logger.info(f"💥 Erreurs: {self.stats['errors']}")
        
        if self.stats['products_processed'] > 0:
            fixed_percent = (self.stats['categories_fixed'] / self.stats['products_processed']) * 100
            self.logger.info(f"📈 Taux de correction: {fixed_percent:.1f}%")
    
    def verify_fixes(self):
        """Vérifie quelques corrections pour confirmer"""
        try:
            self.logger.info("\n🔍 Vérification des corrections...")
            
            query = """
            SELECT reference, subcategories, id_category_default 
            FROM ps_products_comparison 
            WHERE updated_at > DATE_SUB(NOW(), INTERVAL 5 MINUTE)
            ORDER BY updated_at DESC 
            LIMIT 5
            """
            
            self.cursor.execute(query)
            recent_updates = self.cursor.fetchall()
            
            if recent_updates:
                self.logger.info("📋 Dernières corrections appliquées:")
                for product in recent_updates:
                    self.logger.info(f"   - {product['reference']}: {product['subcategories']} → ID: {product['id_category_default']}")
            else:
                self.logger.info("ℹ️ Aucune correction récente trouvée")
                
        except Exception as e:
            self.logger.error(f"❌ Erreur vérification: {e}")
    
    def disconnect(self):
        """Ferme la connexion"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        self.logger.info("🔌 Connexion fermée")

def main():
    """Fonction principale"""
    print("\n" + "="*70)
    print("🔧 CORRECTEUR DE CATÉGORIES")
    print("🎯 Objectif: Corriger id_category_default basé sur les subcategories")
    print("⚠️  ATTENTION: Ce script MODIFIE la base de données")
    print("="*70)
    
    # Confirmation
    response = input("❓ Voulez-vous continuer? (oui/non): ")
    if response.lower() not in ['oui', 'o', 'yes', 'y']:
        print("❌ Opération annulée")
        return False
    
    start_time = time.time()
    
    fixer = CategoryFixer()
    
    try:
        # Connexion
        if not fixer.connect():
            return False
        
        # Correction
        if fixer.fix_categories():
            fixer.show_statistics()
            fixer.verify_fixes()
        else:
            print("❌ Échec de la correction des catégories")
            return False
        
        # Calcul du temps
        end_time = time.time()
        duration = end_time - start_time
        
        print("\n" + "="*70)
        print("🎉 CORRECTION TERMINÉE!")
        print("="*70)
        print(f"⏱️  Durée totale: {duration:.2f} secondes")
        print(f"📦 Produits traités: {fixer.stats['products_processed']}")
        print(f"🔄 Catégories corrigées: {fixer.stats['categories_fixed']}")
        print(f"✅ Déjà correctes: {fixer.stats['already_correct']}")
        print(f"❌ Aucune correspondance: {fixer.stats['no_match_found']}")
        
        if fixer.stats['products_processed'] > 0:
            fixed_rate = (fixer.stats['categories_fixed'] / fixer.stats['products_processed']) * 100
            print(f"📈 Taux de correction: {fixed_rate:.1f}%")
        
        print("💡 Consultez fix_categories.log pour les détails")
        print("="*70)
        
        return True
        
    except Exception as e:
        print(f"💥 ERREUR CRITIQUE: {e}")
        import traceback
        print(traceback.format_exc())
        return False
    
    finally:
        fixer.disconnect()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)