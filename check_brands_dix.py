#!/usr/bin/env python3
"""
Script pour CORRIGER AUTOMATIQUEMENT les brand_id basé sur les brand
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
        logging.FileHandler('fix_brands_auto.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

class BrandFixerAuto:
    def __init__(self):
        self.conn = None
        self.cursor = None
        self.logger = logging.getLogger(__name__)
        self.stats = {
            'total_products': 0,
            'products_processed': 0,
            'brands_fixed': 0,
            'already_correct': 0,
            'no_match_found': 0,
            'errors': 0,
            'brands_created': 0
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
    
    def get_brand_mapping(self) -> Dict:
        """Récupère le mapping des marques depuis ps_brands_mapping"""
        try:
            self.cursor.execute("""
                SELECT brand_name, id, brand_slug, external_id 
                FROM ps_brands_mapping 
                WHERE is_active = 1
                AND external_id IS NOT NULL  # ← AJOUTÉ
            """)
            results = self.cursor.fetchall()
            
            mapping_exact = {}
            mapping_lower = {}
            mapping_normalized = {}
            
            for row in results:
                brand_name = row['brand_name']
                external_id = row['external_id']  # ← UTILISER external_id au lieu de id
                
                # Exact match - stocker external_id
                mapping_exact[brand_name] = external_id
                
                # Lowercase match
                mapping_lower[brand_name.lower()] = external_id
                
                # Normalized match (sans espaces, tirets, points)
                normalized = self.normalize_brand_name(brand_name)
                mapping_normalized[normalized] = external_id
            
            self.logger.info(f"📊 Mapping chargé: {len(mapping_exact)} marques avec external_id")
            return {
                'exact': mapping_exact,
                'lower': mapping_lower,
                'normalized': mapping_normalized
            }
            
        except Exception as e:
            self.logger.error(f"❌ Erreur chargement mapping marques: {e}")
            return {'exact': {}, 'lower': {}, 'normalized': {}}
        
    def normalize_brand_name(self, brand_name: str) -> str:
        """Normalise un nom de marque pour la comparaison"""
        if not brand_name:
            return ""
        return (brand_name.lower()
                .replace(' ', '')
                .replace('-', '')
                .replace('.', '')
                .replace(',', '')
                .replace('_', '')
                .strip())
    
    def create_missing_brand(self, brand_name: str) -> Optional[int]:
        """Crée une marque manquante dans ps_brands_mapping"""
        try:
            # Générer un slug à partir du nom
            brand_slug = (brand_name.lower()
                         .replace(' ', '-')
                         .replace('.', '')
                         .replace(',', '')
                         .replace('_', '-'))
            
            # Vérifier si le slug existe déjà
            check_query = "SELECT id FROM ps_brands_mapping WHERE brand_slug = %s"
            self.cursor.execute(check_query, (brand_slug,))
            existing = self.cursor.fetchone()
            
            if existing:
                return existing['id']
            
            # Insérer la nouvelle marque
            insert_query = """
            INSERT INTO ps_brands_mapping (brand_name, brand_slug, is_active, created_at, updated_at)
            VALUES (%s, %s, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """
            
            self.cursor.execute(insert_query, (brand_name, brand_slug))
            new_brand_id = self.cursor.lastrowid
            
            self.conn.commit()
            self.stats['brands_created'] += 1
            self.logger.info(f"➕ NOUVELLE MARQUE: '{brand_name}' → ID: {new_brand_id}")
            
            return new_brand_id
            
        except Exception as e:
            self.logger.error(f"❌ Erreur création marque '{brand_name}': {e}")
            self.conn.rollback()
            return None
    
    def get_products_to_fix(self):
        """Récupère les produits avec brand qui peuvent avoir des brand_id invalides"""
        try:
            query = """
            SELECT 
                id,
                reference,
                brand,
                brand_id
            FROM ps_products_comparison 
            WHERE brand IS NOT NULL 
            AND brand != ''
            AND LENGTH(brand) > 0
            ORDER BY id
            """
            
            self.cursor.execute(query)
            products = self.cursor.fetchall()
            
            self.logger.info(f"📦 {len(products)} produits avec brand trouvés")
            return products
            
        except Exception as e:
            self.logger.error(f"❌ Erreur récupération produits: {e}")
            return []
    
    def find_brand_match(self, brand_str: str, mapping: Dict) -> Optional[int]:
        """Trouve la correspondance de marque"""
        if not brand_str:
            return None
        
        # Nettoyer la chaîne
        brand_clean = brand_str.strip()
        
        # 1. Essayer la correspondance exacte
        if brand_clean in mapping['exact']:
            return mapping['exact'][brand_clean]
        
        # 2. Essayer en minuscules
        brand_lower = brand_clean.lower()
        if brand_lower in mapping['lower']:
            return mapping['lower'][brand_lower]
        
        # 3. Essayer la version normalisée
        brand_normalized = self.normalize_brand_name(brand_clean)
        if brand_normalized in mapping['normalized']:
            return mapping['normalized'][brand_normalized]
        
        return None
    
    def update_product_brand(self, product_id: int, reference: str, new_brand_id: int, old_brand_id: int):
        """Met à jour le brand_id d'un produit"""
        try:
            query = """
            UPDATE ps_products_comparison 
            SET brand_id = %s, 
                updated_at = CURRENT_TIMESTAMP 
            WHERE id = %s
            """
            
            self.cursor.execute(query, (new_brand_id, product_id))
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erreur mise à jour produit {reference}: {e}")
            return False
    
    def fix_brands(self, create_missing=True):
        """Corrige les brand_id basé sur les brand"""
        self.logger.info("🔧 Début de la correction automatique des marques...")
        
        # Charger le mapping
        brand_mapping = self.get_brand_mapping()
        if not brand_mapping['exact']:
            self.logger.error("❌ Aucun mapping de marques chargé")
            return False
        
        # Récupérer les produits
        products = self.get_products_to_fix()
        if not products:
            self.logger.warning("⚠️ Aucun produit à corriger trouvé")
            return True
        
        self.stats['total_products'] = len(products)
        
        if create_missing:
            self.logger.info("➕ MODE: Création automatique des marques manquantes")
        else:
            self.logger.info("🔍 MODE: Recherche uniquement (pas de création)")
        
        for i, product in enumerate(products, 1):
            try:
                product_id = product['id']
                reference = product['reference']
                brand = product['brand']
                current_brand_id = product['brand_id']
                
                # Afficher la progression
                if i % 1000 == 0 or i <= 10 or i == len(products):
                    progress = (i / len(products)) * 100
                    self.logger.info(f"⏳ Progression: {i}/{len(products)} ({progress:.1f}%)")
                
                self.stats['products_processed'] += 1
                
                # Trouver la correspondance
                correct_brand_id = self.find_brand_match(brand, brand_mapping)
                
                # Créer la marque si elle n'existe pas
                if not correct_brand_id and create_missing:
                    correct_brand_id = self.create_missing_brand(brand)
                    if correct_brand_id:
                        # Recharger le mapping avec la nouvelle marque
                        brand_mapping = self.get_brand_mapping()
                
                if correct_brand_id:
                    # Vérifier si la marque doit être mise à jour
                    if current_brand_id != correct_brand_id:
                        if self.update_product_brand(product_id, reference, correct_brand_id, current_brand_id):
                            self.stats['brands_fixed'] += 1
                            if self.stats['brands_fixed'] <= 10:  # Log seulement les 10 premiers
                                self.logger.info(f"🔄 CORRIGÉ: {reference}")
                                self.logger.info(f"   Brand: {brand}")
                                self.logger.info(f"   Ancien ID: {current_brand_id} → Nouvel ID: {correct_brand_id}")
                        else:
                            self.stats['errors'] += 1
                    else:
                        self.stats['already_correct'] += 1
                else:
                    self.stats['no_match_found'] += 1
                    if self.stats['no_match_found'] <= 5:  # Log seulement les 5 premiers
                        self.logger.warning(f"❌ AUCUN MATCH: {reference} - Brand: '{brand}'")
                
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
        self.logger.info("📊 RAPPORT DE CORRECTION DES MARQUES")
        self.logger.info("="*60)
        self.logger.info(f"📦 Produits traités: {self.stats['products_processed']}")
        self.logger.info(f"🔄 Marques corrigées: {self.stats['brands_fixed']}")
        self.logger.info(f"✅ Déjà correctes: {self.stats['already_correct']}")
        self.logger.info(f"❌ Aucune correspondance: {self.stats['no_match_found']}")
        self.logger.info(f"➕ Marques créées: {self.stats['brands_created']}")
        self.logger.info(f"💥 Erreurs: {self.stats['errors']}")
        
        if self.stats['products_processed'] > 0:
            fixed_percent = (self.stats['brands_fixed'] / self.stats['products_processed']) * 100
            match_percent = ((self.stats['brands_fixed'] + self.stats['already_correct']) / self.stats['products_processed']) * 100
            self.logger.info(f"📈 Taux de correction: {fixed_percent:.1f}%")
            self.logger.info(f"🎯 Taux de matching: {match_percent:.1f}%")
    
    def show_unmatched_brands(self, limit=20):
        """Affiche les marques qui n'ont pas de correspondance"""
        try:
            self.logger.info(f"\n🔍 Top {limit} marques sans correspondance:")
            
            query = """
            SELECT brand, COUNT(*) as count
            FROM ps_products_comparison 
            WHERE brand IS NOT NULL 
            AND brand != ''
            AND brand_id IS NULL
            GROUP BY brand
            ORDER BY count DESC
            LIMIT %s
            """
            
            self.cursor.execute(query, (limit,))
            unmatched = self.cursor.fetchall()
            
            if unmatched:
                for item in unmatched:
                    self.logger.info(f"   - '{item['brand']}': {item['count']} produits")
            else:
                self.logger.info("   ✅ Toutes les marques ont une correspondance!")
                
        except Exception as e:
            self.logger.error(f"❌ Erreur récupération marques sans match: {e}")
    
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
    print("🔧 CORRECTEUR AUTOMATIQUE DE MARQUES")
    print("🎯 Objectif: Corriger brand_id basé sur les brand")
    print("⚡ MODE: Automatique avec création des marques manquantes")
    print("="*70)
    
    start_time = time.time()
    
    fixer = BrandFixerAuto()
    
    try:
        # Connexion
        if not fixer.connect():
            return False
        
        # Correction automatique
        if fixer.fix_brands(create_missing=True):
            fixer.show_statistics()
            fixer.show_unmatched_brands()
        else:
            print("❌ Échec de la correction des marques")
            return False
        
        # Calcul du temps
        end_time = time.time()
        duration = end_time - start_time
        
        print("\n" + "="*70)
        print("🎉 CORRECTION AUTOMATIQUE TERMINÉE!")
        print("="*70)
        print(f"⏱️  Durée totale: {duration:.2f} secondes")
        print(f"📦 Produits traités: {fixer.stats['products_processed']}")
        print(f"🔄 Marques corrigées: {fixer.stats['brands_fixed']}")
        print(f"✅ Déjà correctes: {fixer.stats['already_correct']}")
        print(f"❌ Aucune correspondance: {fixer.stats['no_match_found']}")
        print(f"➕ Marques créées: {fixer.stats['brands_created']}")
        
        if fixer.stats['products_processed'] > 0:
            fixed_rate = (fixer.stats['brands_fixed'] / fixer.stats['products_processed']) * 100
            print(f"📈 Taux de correction: {fixed_rate:.1f}%")
        
        print("💡 Consultez fix_brands_auto.log pour les détails")
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