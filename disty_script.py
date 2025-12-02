from selenium import webdriver
import time
import os
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
import traceback
from database import get_disty_connection
import mysql.connector
from datetime import datetime
from contextlib import contextmanager

@contextmanager
def get_db_connection():
    """Context manager pour gérer automatiquement les connexions"""
    cnx = None
    try:
        cnx = get_disty_connection()
        yield cnx
    except Exception as e:
        print(f"❌ Erreur connexion DB: {e}")
        raise

def create_driver():
    """Crée et configure le driver Selenium"""
    options = webdriver.FirefoxOptions()
    driver = webdriver.Firefox(options=options)
    return driver

def login_disty(driver):
    """Connexion au site Disty"""
    driver.get("https://www.distytechnologies.com/connexion")
    try:
        input_email = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.NAME, 'email'))
        )
        input_email.send_keys('n.adil@disup.ma')
        time.sleep(2)

        input_password = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.ID, 'field-password'))
        )
        input_password.send_keys('P002128')
        input_password.send_keys(Keys.RETURN)
        time.sleep(5)
        print("✅ Login réussi")
    except Exception as e:
        print(f"❌ Erreur login: {e}")

def get_links_categories():
    """Récupère les liens des catégories depuis la base"""
    try:
        with get_db_connection() as cnx:
            if cnx:
                cursor = cnx.cursor()
                query = "SELECT id_dix_categories, link FROM disty_categories_link"
                cursor.execute(query)
                rows = cursor.fetchall()
                cursor.close()
                print(f"📋 {len(rows)} catégories récupérées")
                return rows
    except Exception as e:
        print(f"❌ Erreur récupération catégories: {e}")
        return None

def get_stock_value(statut_class, statut_text):
    """Détermine la quantité de stock basée sur la classe et le texte"""
    statut_text = statut_text.lower()
    
    if 'pavailable' in statut_class:
        return 10
    elif 'notavailable' in statut_class:
        return 0
    elif 'upcoming' in statut_class:
        if 'qte limite' in statut_text:
            return 1
        else:
            return 0
    else:
        if 'dispo' in statut_text:
            return 10
        elif 'non dispo' in statut_text or 'rupture' in statut_text:
            return 0
        elif 'qte limite' in statut_text:
            return 1
        else:
            return 0

def extract_product_data(product_element, id_categorie):
    """Extrait les données d'un produit depuis l'élément HTML"""
    try:
        # URL du produit
        url = product_element.find_element(By.CLASS_NAME, 'product-thumbnail').get_attribute('href')
        
        # Référence
        ref = product_element.find_element(By.CLASS_NAME, 'ref-pdr').text
        
        # Nettoyage référence
        reference_split = ['BHN', 'B19', 'BEW', 'A80', 'ABB', 'BH4', 'BHL', 'AC3', 'ABF', 'AB6','BGX']
        for value in reference_split:
            if value in ref:
                ref = ref.split('-')[0]
                break
        
        # TITRE
        title_element = product_element.find_element(By.CLASS_NAME, 'product-title')
        title_text = title_element.text.split('\n')[0].strip()
        title = f"{title_text} ({ref})"
        
        # Prix public
        public_price = 0.0
        public_price_elements = product_element.find_elements(By.XPATH, ".//*[contains(text(), 'Prix public :')]")
        if public_price_elements:
            public_price_text = public_price_elements[0].text
            public_price = float(public_price_text.split('Prix public :')[1].split()[0])
        
        # Prix promo/remisé
        remise_price = public_price
        promo_elements = product_element.find_elements(By.XPATH, ".//*[contains(text(), 'Prix promo :')]")
        remise_elements = product_element.find_elements(By.XPATH, ".//*[contains(text(), 'Prix remisé :')]")
        
        if promo_elements:
            promo_text = promo_elements[0].text
            remise_price = float(promo_text.split('Prix promo :')[1].split()[0])
        elif remise_elements:
            remise_text = remise_elements[0].text
            remise_price = float(remise_text.split('Prix remisé :')[1].split()[0])
        
        # STOCK
        qte = 0
        statut_elements = product_element.find_elements(By.CLASS_NAME, 'etat-stock')
        if statut_elements:
            statut = statut_elements[0]
            statut_class = statut.get_attribute('class')
            statut_text = statut.text.strip().lower()
            qte = get_stock_value(statut_class, statut_text)
        
        reduction = public_price - remise_price
        
        product_data = {
            'ref': str(ref),
            'title': title,
            'qte': qte,
            'public_price': public_price,
            'remise_price': remise_price,
            'reduction': reduction,
            'url': url,
            'id_categorie': id_categorie,
        }
        
        return product_data
        
    except Exception as e:
        print(f"      ❌ Erreur extraction données produit: {e}")
        return None

def update_or_insert_products(products):
    """Met à jour ou insère les produits dans ps_product"""
    if not products:
        print("❌ Aucun produit à sauvegarder")
        return False
        
    try:
        with get_db_connection() as cnx:
            if not cnx:
                return False
                
            cursor = cnx.cursor()
            
            updated_count = 0
            inserted_count = 0
            error_count = 0
            
            total_products = len(products)
            print(f"\n💾 Sauvegarde de {total_products} produits dans la base...")
            
            for index, product in enumerate(products, 1):
                try:
                    # Afficher la progression
                    if index % 10 == 0 or index == total_products:
                        print(f"   📊 Progression: {index}/{total_products} ({index/total_products*100:.1f}%)")
                    
                    # Vérifier si le produit existe déjà par référence
                    check_query = "SELECT id_product FROM ps_product WHERE reference = %s"
                    cursor.execute(check_query, (product['ref'],))
                    existing_product = cursor.fetchone()
                    
                    if existing_product:
                        # UPDATE du produit existant
                        update_query = """
                        UPDATE ps_product 
                        SET id_category_default = %s, 
                            price = %s, 
                            wholesale_price = %s, 
                            reduction = %s, 
                            quantity = %s,
                            marge_inf = 0
                        WHERE reference = %s
                        """
                        cursor.execute(update_query, (
                            product['id_categorie'],
                            product['remise_price'],
                            product['public_price'],
                            product['reduction'],
                            product['qte'],
                            product['ref']
                        ))
                        updated_count += 1
                        
                    else:
                        # INSERT nouveau produit
                        cursor.execute("SELECT COALESCE(MAX(id_product), 0) + 1 FROM ps_product")
                        new_id = cursor.fetchone()[0]
                        
                        insert_query = """
                        INSERT INTO ps_product 
                        (id_product, reference, id_category_default, price, wholesale_price, reduction, quantity, marge_inf) 
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """
                        cursor.execute(insert_query, (
                            new_id,
                            product['ref'],
                            product['id_categorie'],
                            product['remise_price'],
                            product['public_price'],
                            product['reduction'],
                            product['qte'],
                            0
                        ))
                        inserted_count += 1
                            
                except Exception as e:
                    error_count += 1
                    print(f"   ❌ Erreur produit {product['ref']}: {e}")
                    continue
            
            cnx.commit()
            cursor.close()
            
            print(f"\n📊 RÉSULTAT BASE DE DONNÉES:")
            print(f"   🔄 Produits mis à jour: {updated_count}")
            print(f"   ✅ Nouveaux produits insérés: {inserted_count}")
            print(f"   ❌ Erreurs: {error_count}")
            print(f"   📦 Total traité: {len(products)} produits")
            
            return True
            
    except Exception as e:
        print(f"❌ Erreur base de données: {e}")
        return False

def scrape_disty_products():
    """Fonction principale de scraping"""
    driver = create_driver()
    
    try:
        login_disty(driver)
        
        categories = get_links_categories()
        if not categories:
            print("❌ Aucune catégorie trouvée")
            return []
            
        all_products = []
        total_categories = len(categories)
        total_products_scraped = 0
        
        print(f"\n🎯 DÉBUT DU SCRAPING - {total_categories} catégories à traiter")
        print("=" * 70)
        
        for index, (id_categorie, link) in enumerate(categories, 1):
            print(f"\n📂 [{index}/{total_categories}] Catégorie ID: {id_categorie}")
            print(f"🔗 {link}")
            
            category_products = 0
            
            try:
                driver.get(link)
                time.sleep(3)

                # Détection du nombre de pages
                max_page = 1
                try:
                    pagine_div = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CLASS_NAME, 'page-list'))
                    )
                    if pagine_div:
                        page_items = pagine_div.find_elements(By.TAG_NAME, 'li')
                        if len(page_items) >= 2:
                            max_page = int(page_items[-2].find_element(By.TAG_NAME, 'a').get_attribute('innerHTML'))
                except Exception:
                    max_page = 1
                
                print(f"   📄 {max_page} pages détectées")

                for page_num in range(1, max_page + 1):
                    page_url = f"{link}?page={page_num}" if page_num > 1 else link
                    print(f"\n   🔍 Page {page_num}/{max_page}")
                    
                    if page_num > 1:
                        driver.get(page_url)
                        # time.sleep(2)

                    products = driver.find_elements(By.CLASS_NAME, 'item-prd')
                    
                    if not products:
                        print("   ⚠️ Aucun produit trouvé sur cette page")
                        break

                    page_products = 0
                    print(f"   ✅ {len(products)} produits trouvés sur la page")

                    for product in products:
                        try:
                            product_data = extract_product_data(product, id_categorie)
                            if product_data:
                                all_products.append(product_data)
                                page_products += 1
                                total_products_scraped += 1
                                
                                # Afficher chaque produit
                                stock_msg = "🟢 DISPO (10)" if product_data['qte'] == 10 else "🟡 LIMITE (1)" if product_data['qte'] == 1 else "🔴 RUPTURE (0)"
                                print(f"      ✅ {product_data['ref']} | {stock_msg}")
                                
                        except Exception as e:
                            print(f"      ❌ Erreur produit: {e}")
                            continue
                    
                    category_products += page_products
                    print(f"   📦 {page_products} produits ajoutés de cette page")
                
                print(f"   🎉 Catégorie terminée: {category_products} produits")
                
                # Progression globale
                progress = (index / total_categories) * 100
                print(f"   📊 Progression globale: {index}/{total_categories} catégories ({progress:.1f}%)")
                
            except Exception as e:
                print(f"❌ Erreur catégorie {id_categorie}: {e}")
                continue
        
        # Résumé final détaillé
        print(f"\n{'='*70}")
        print("🎉 SCRAPING DISTY TERMINÉ !")
        print(f"📊 RÉSULTATS FINAUX:")
        print(f"   📂 Catégories traitées: {total_categories}")
        print(f"   📦 Produits scrapés: {total_products_scraped}")
        
        if all_products:
            stock_10 = sum(1 for p in all_products if p['qte'] == 10)
            stock_1 = sum(1 for p in all_products if p['qte'] == 1)
            stock_0 = sum(1 for p in all_products if p['qte'] == 0)
            
            print(f"   📊 DÉTAIL STOCK:")
            print(f"      🟢 Disponible (10): {stock_10} produits")
            print(f"      🟡 Limitée (1): {stock_1} produits") 
            print(f"      🔴 Rupture (0): {stock_0} produits")
            print(f"      📈 Taux de disponibilité: {(stock_10/len(all_products)*100):.1f}%")
        
        return all_products
        
    except Exception as e:
        print(f"💥 Erreur générale: {e}")
        traceback.print_exc()
        return []
    finally:
        if driver:
            driver.quit()
            print("\n🔚 Navigateur fermé")

def scrape_and_save_disty_products():
    """Fonction principale qui gère tout le processus"""
    print("🚀 DÉMARRAGE DU SCRAPING DISTY")
    print("=" * 70)
    print(f"🕐 Début: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    start_time = time.time()
    
    # Scraper les produits
    products = scrape_disty_products()
    
    if products:
        # Sauvegarder dans la base de données
        db_success = update_or_insert_products(products)
        
        end_time = time.time()
        duration = end_time - start_time
        
        if db_success:
            print(f"\n🎉 PROCESSUS DISTY TERMINÉ AVEC SUCCÈS!")
            print(f"⏱️  Durée totale: {duration:.2f} secondes")
            print(f"📦 Produits traités: {len(products)}")
            print(f"🕐 Fin: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print(f"\n⚠️ PROCESSUS DISTY TERMINÉ AVEC DES ERREURS")
            
    else:
        print("\n❌ AUCUN PRODUIT TROUVÉ - PROCESSUS ARRÊTÉ")
    
    return products

# Exécuter le scraping
if __name__ == "__main__":
    products = scrape_and_save_disty_products()