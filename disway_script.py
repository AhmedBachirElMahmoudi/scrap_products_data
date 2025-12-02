from selenium import webdriver
import time
import os
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import traceback
from database import get_disway_connection
from datetime import datetime
from contextlib import contextmanager

username = 'n.adil@rysasoft.ma'
password = 'Rysasoft@2023'
login_url = 'https://www.disway.com/profile/login'

@contextmanager
def get_db_connection():
    """Context manager pour gérer automatiquement les connexions"""
    cnx = None
    try:
        cnx = get_disway_connection()
        yield cnx
    except Exception as e:
        print(f"❌ Erreur connexion DB: {e}")
        raise

def create_driver():
    """Crée et configure le driver Selenium"""
    options = webdriver.FirefoxOptions()
    driver = webdriver.Firefox(options=options)
    return driver

def login_disway(driver):
    """Connexion au site Disway"""
    driver.get(login_url)
    try:
        # Find the username and password fields and enter your credentials
        username_field = driver.find_element(
            by=webdriver.common.by.By.NAME, value='email')
        username_field.send_keys(username)
        password_field = driver.find_element(
            by=webdriver.common.by.By.NAME, value='password')
        password_field.send_keys(password)
        checkbox = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.NAME, 'persistent'))
        )
        # Click on the checkbox
        checkbox.click()
        # Submit the login form
        submit_button = driver.find_element(
            by=webdriver.common.by.By.CLASS_NAME, value='Login_submit-btn')
        submit_button.click()
        time.sleep(5)
        print("✅ Login réussi sur Disway")
    except Exception as e:
        print(f"❌ Erreur login Disway: {e}")

def get_links_categories():
    """Récupère les liens des catégories depuis la base"""
    try:
        with get_db_connection() as cnx:
            if cnx:
                cursor = cnx.cursor()
                query = "SELECT category_dix_id, link FROM disway_categories_link"
                cursor.execute(query)
                rows = cursor.fetchall()
                cursor.close()
                print(f"📋 {len(rows)} catégories récupérées")
                return rows
    except Exception as e:
        print(f"❌ Erreur récupération catégories: {e}")
        return None

def clean_price(price_text):
    """Nettoie le format de prix Disway"""
    try:
        cleaned = price_text.replace("MAD", "").strip()
        if "," in cleaned and "." in cleaned:
            cleaned = cleaned.replace(",", "")
        elif "," in cleaned:
            cleaned = cleaned.replace(",", ".")
        return float(cleaned)
    except ValueError as e:
        print(f"Erreur conversion prix '{price_text}': {e}")
        return 0.0

def get_stock_value(dispo_text):
    """Détermine la quantité de stock"""
    if not dispo_text:
        return 0
    
    dispo_text_lower = dispo_text.lower()
    
    if "unité(s) restante(s)" in dispo_text_lower:
        try:
            qte = int(dispo_text.strip().split()[0])
            return min(qte, 10)
        except:
            return 1
    elif "disponible" in dispo_text_lower:
        return 10
    elif "rupture" in dispo_text_lower or "non disponible" in dispo_text_lower:
        return 0
    else:
        return 0

def extract_product_data(product_element, id_categorie):
    """Extrait les données d'un produit depuis l'élément HTML Disway"""
    try:
        # Référence
        ref_element = product_element.find_element(By.CLASS_NAME, "PLP_item-number")
        ref_text = ref_element.text
        if "Référence " in ref_text:
            ref = ref_text.replace("Référence ", "").strip()
        else:
            ref = ref_text.strip()
        
        # Titre
        title_element = product_element.find_element(By.CLASS_NAME, "PLP_product-title")
        title_text = title_element.text.strip()
        title = f"{title_text} ({ref})"
        
        # URL du produit
        url = title_element.get_attribute('href')
        
        # Disponibilité et stock
        qte = 0
        dispo_text = ""
        
        stock_selectors = [
            ".Product_stock-value",
            ".stock",
            ".availability",
            "[class*='stock']",
            "[class*='available']"
        ]
        
        for selector in stock_selectors:
            try:
                stock_element = product_element.find_element(By.CSS_SELECTOR, selector)
                dispo_text = stock_element.text
                if dispo_text.strip():
                    qte = get_stock_value(dispo_text)
                    break
            except NoSuchElementException:
                continue
        
        # Si aucun sélecteur ne fonctionne, chercher par texte
        if qte == 0:
            try:
                elements = product_element.find_elements(By.XPATH, ".//*[contains(text(), 'restante') or contains(text(), 'Disponible') or contains(text(), 'stock') or contains(text(), 'Stock')]")
                for element in elements:
                    if element.is_displayed() and element.text.strip():
                        dispo_text = element.text
                        qte = get_stock_value(dispo_text)
                        break
            except:
                qte = 0
        
        # Prix actuel
        price = 0
        price_selectors = [
            ".PLP_actual-price",
            ".price",
            ".actual-price",
            "[class*='price']",
            "[class*='actual']"
        ]
        
        for selector in price_selectors:
            try:
                price_element = product_element.find_element(By.CSS_SELECTOR, selector)
                price_text = price_element.text
                if price_text.strip():
                    price = clean_price(price_text)
                    break
            except NoSuchElementException:
                continue
        
        # Ancien prix (prix public)
        old_price = price
        old_price_selectors = [
            ".PLP_action-price",
            ".old-price",
            ".regular-price",
            "[class*='old']",
            "[class*='regular']",
            "[class*='action']"
        ]
        
        for selector in old_price_selectors:
            try:
                old_price_element_div = product_element.find_element(By.CSS_SELECTOR, selector)
                old_price_element = old_price_element_div.find_element(By.TAG_NAME, 'span')
                old_price_text = old_price_element.text
                if old_price_text.strip():
                    old_price = clean_price(old_price_text)
                    break
            except (NoSuchElementException, TimeoutException):
                continue
            except Exception:
                continue
        
        # Calcul de la réduction
        reduction = round(old_price - price, 2)
        
        product_data = {
            'ref': str(ref),
            'title': title,
            'qte': qte,
            'old_price': old_price,
            'price': price,
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
                            product['price'],
                            product['old_price'],
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
                            product['price'],
                            product['old_price'],
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

def scrape_disway_products():
    """Fonction principale de scraping Disway"""
    driver = create_driver()
    
    try:
        login_disway(driver)
        
        categories = get_links_categories()
        if not categories:
            print("❌ Aucune catégorie trouvée")
            return []
            
        all_products = []
        total_categories = len(categories)
        total_products_scraped = 0
        
        print(f"\n🎯 DÉBUT DU SCRAPING DISWAY - {total_categories} catégories à traiter")
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
                        EC.presence_of_element_located((By.CLASS_NAME, 'Paging_pagination'))
                    )
                    if pagine_div:
                        pagine_ul = pagine_div.find_element(By.TAG_NAME, 'ul')
                        page_items = pagine_ul.find_elements(By.TAG_NAME, 'li')
                        if page_items:
                            max_page = int(page_items[-1].get_attribute('data-index')) + 1
                except Exception as e:
                    print(f"   ⚠️ Pagination non détectée: {e}")
                    max_page = 1
                
                print(f"   📄 {max_page} pages détectées")

                for page_num in range(1, max_page + 1):
                    page_url = f"{link}?page={page_num}" if page_num > 1 else link
                    print(f"\n   🔍 Page {page_num}/{max_page}")
                    
                    try:
                        if page_num > 1:
                            driver.get(page_url)
                            time.sleep(3)

                        products = driver.find_elements(By.CLASS_NAME, 'PLP_item')
                        
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
                                    if product_data['qte'] == 10:
                                        stock_msg = "🟢 DISPO (10)"
                                    elif product_data['qte'] > 0:
                                        stock_msg = f"🟡 LIMITE ({product_data['qte']})"
                                    else:
                                        stock_msg = "🔴 RUPTURE (0)"
                                    
                                    print(f"      ✅ {product_data['ref']} | {stock_msg}")
                                    
                            except Exception as e:
                                print(f"      ❌ Erreur produit: {e}")
                                continue
                        
                        category_products += page_products
                        print(f"   📦 {page_products} produits ajoutés de cette page")
                    
                    except Exception as e:
                        print(f"   ❌ Erreur page {page_num}: {e}")
                        continue
                
                print(f"   🎉 Catégorie terminée: {category_products} produits")
                
                # Progression globale
                progress = (index / total_categories) * 100
                print(f"   📊 Progression globale: {index}/{total_categories} catégories ({progress:.1f}%)")
                
            except Exception as e:
                print(f"❌ Erreur catégorie {id_categorie}: {e}")
                continue
        
        # Résumé final détaillé
        print(f"\n{'='*70}")
        print("🎉 SCRAPING DISWAY TERMINÉ !")
        print(f"📊 RÉSULTATS FINAUX:")
        print(f"   📂 Catégories traitées: {total_categories}")
        print(f"   📦 Produits scrapés: {total_products_scraped}")
        
        if all_products:
            stock_10 = sum(1 for p in all_products if p['qte'] == 10)
            stock_limited = sum(1 for p in all_products if 1 <= p['qte'] < 10)
            stock_0 = sum(1 for p in all_products if p['qte'] == 0)
            
            print(f"   📊 DÉTAIL STOCK:")
            print(f"      🟢 Disponible (10): {stock_10} produits")
            print(f"      🟡 Limitée (1-9): {stock_limited} produits") 
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

def scrape_and_save_disway_products():
    """Fonction principale qui gère tout le processus"""
    print("🚀 DÉMARRAGE DU SCRAPING DISWAY")
    print("=" * 70)
    print(f"🕐 Début: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    start_time = time.time()
    
    # Scraper les produits
    products = scrape_disway_products()
    
    if products:
        # Sauvegarder dans la base de données
        db_success = update_or_insert_products(products)
        
        end_time = time.time()
        duration = end_time - start_time
        
        if db_success:
            print(f"\n🎉 PROCESSUS DISWAY TERMINÉ AVEC SUCCÈS!")
            print(f"⏱️  Durée totale: {duration:.2f} secondes")
            print(f"📦 Produits traités: {len(products)}")
            print(f"🕐 Fin: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print(f"\n⚠️ PROCESSUS DISWAY TERMINÉ AVEC DES ERREURS")
            
    else:
        print("\n❌ AUCUN PRODUIT TROUVÉ - PROCESSUS ARRÊTÉ")
    
    return products

# Exécuter le scraping
if __name__ == "__main__":
    products = scrape_and_save_disway_products()