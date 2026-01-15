import requests
import urllib.parse
import re
from bs4 import BeautifulSoup
import json
import time
import sys
import os
from datetime import datetime

# Try to import pandas for Excel reading
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

from utils import clean_text, extract_price, normalize_image_url, update_product_in_database
from database import connect_scraper

def print_flush(msg):
    print(msg, flush=True)

# ==============================================================================================
# CONFIGURATION
# ==============================================================================================
BASE_URL = "https://www.ultrapc.ma"
SEARCH_URL_TEMPLATE = "https://www.ultrapc.ma/recherche?controller=search&s={}"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
}

# ==============================================================================================
# DATABASE FUNCTIONS
# ==============================================================================================

def get_or_create_product(reference, name=None):
    """
    Check if a product exists in the DB by reference.
    If yes, return its ID.
    If no, create it (partially) and return new ID.
    Returns: (id, is_new)
    """
    if not reference:
        return None, False
        
    conn = connect_scraper()
    cursor = conn.cursor()
    
    try:
        # Check existence
        cursor.execute("SELECT id FROM ps_products_comparison_v2 WHERE reference = %s", (reference,))
        res = cursor.fetchone()
        
        if res:
            return res[0], False
        
        # Create new
        print_flush(f"🆕 Creating new product in DB: {reference}")
        cursor.execute(
            "INSERT INTO ps_products_comparison_v2 (reference, created_at) VALUES (%s, NOW())", 
            (reference,)
        )
        conn.commit()
        
        new_id = cursor.lastrowid
        return new_id, True
        
    except Exception as e:
        print_flush(f"❌ Database error: {e}")
        return None, False
    finally:
        cursor.close()
        conn.close()

# ==============================================================================================
# SCRAPER FUNCTIONS
# ==============================================================================================

def search_product_ultrapc(query):
    """
    Search for a product on UltraPC and return the first matching URL.
    """
    encoded_query = urllib.parse.quote(query)
    url = SEARCH_URL_TEMPLATE.format(encoded_query)
    
    print_flush(f"🔍 Searching for: {query} -> {url}")
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Look for product miniatures
        products = soup.select('.js-product-miniature')
        
        if not products:
            print_flush(f"❌ No results found for '{query}'")
            return None
            
        print_flush(f"✅ Found {len(products)} results.")
        
        # Take the first one (most relevant)
        first_product = products[0]
        link = first_product.select_one('a.product-thumbnail')
        
        if link and link.get('href'):
            product_url = link.get('href')
            print_flush(f"🔗 Found Product URL: {product_url}")
            return product_url
            
        return None
        
    except Exception as e:
        print_flush(f"❌ Error during search: {e}")
        return None

def scrape_ultrapc_details(url):
    """
    Scrape detailed information from a product page.
    """
    print_flush(f"🌐 Scraping: {url}")
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 1. Title
        title_tag = soup.select_one('h1[itemprop="name"]') or soup.select_one('h1')
        title = clean_text(title_tag.get_text()) if title_tag else "No Title"
        
        # 2. Price
        price = 0.0
        price_tag = soup.select_one('span[itemprop="price"]')
        if price_tag:
            price_text = price_tag.get('content') or price_tag.get_text()
            price = extract_price(price_text) or 0.0
            
        # Old Price
        old_price = 0.0
        # Look for regular price (crossed out)
        old_price_tag = soup.select_one('.regular-price')
        if old_price_tag:
            old_price = extract_price(old_price_tag.get_text()) or 0.0
            
        # 3. Description
        description = ""
        desc_div = soup.select_one('#description .product-description') or soup.find('div', class_='product-description')
        if desc_div:
            description = str(desc_div)
            
        # 4. Short Description
        short_desc = ""
        short_desc_div = soup.select_one('#product-description-short') or soup.find('div', itemprop='description')
        if short_desc_div:
            short_desc = clean_text(short_desc_div.get_text())
            
        # 5. Image
        image_url = ""
        img_tag = soup.select_one('.product-cover img') or soup.select_one('img[itemprop="image"]')
        if img_tag:
            image_url = img_tag.get('src')
            
        # 6. Categories (Breadcrumb from JS)
        category_str = ""
        subcategory_str = ""
        categories = []
        
        try:
            # Try to extract from Prestashop JS object first (most reliable)
            script_tag = soup.find('script', string=re.compile(r'var prestashop ='))
            if script_tag:
                match = re.search(r'var prestashop = ({.*?});', script_tag.string, re.DOTALL)
                if match:
                    json_str = match.group(1)
                    data_js = json.loads(json_str)
                    
                    if 'breadcrumb' in data_js and 'links' in data_js['breadcrumb']:
                        links = data_js['breadcrumb']['links']
                        # Filter out 'Accueil'
                        categories_raw = [
                            l['title'] for l in links 
                            if l['title'] != 'Accueil'
                        ]
                        
                        # Remove the last item if it is the product title
                        if categories_raw:
                            last_item = categories_raw[-1].strip()
                            # If the last item is very similar to the title, assume it's the productbreadcrumb
                            if last_item.lower() in title.lower() or title.lower() in last_item.lower():
                                categories_raw.pop()
                                
                        categories = [clean_text(c) for c in categories_raw]
        except Exception as e:
            print_flush(f"⚠️ Error parsing JS categories: {e}")
            
        # Fallback to HTML if JS failed or empty
        if not categories:
            breadcrumb_links = soup.select('.breadcrumb li a')
            if breadcrumb_links:
                # Skip Home (usually first)
                categories = [clean_text(link.get_text()) for link in breadcrumb_links[1:]]

        if categories:
            # User logic: 
            # Category = First item (e.g. "Périphériques")
            # Subcategory = Last item (e.g. "Périphériques de jeu")
            category_str = categories[0]
            subcategory_str = categories[-1] if len(categories) > 1 else ""
            
            # Optional: If you want subcategory to be everything else joined:
            # subcategory_str = " > ".join(categories[1:]) if len(categories) > 1 else ""
        
        # 7. Attributes (Features)
        attributes = {}
        # Try finding DL list
        dl_list = soup.select('.product-features dl.data-sheet')
        if dl_list:
            for dl in dl_list:
                dt = dl.select_one('dt')
                dd = dl.select_one('dd')
                if dt and dd:
                    key = clean_text(dt.get_text()).rstrip(':')
                    val = clean_text(dd.get_text())
                    attributes[key] = val
        
        # 8. Brand (from JSON-LD or Manufacturer specific)
        brand = ""
        # Check for brand image in product-manufacturer
        brand_img = soup.select_one('.product-manufacturer img')
        if brand_img:
            brand = brand_img.get('alt')
        
        data = {
            'product_url': url,
            'title': title,
            'price': price,
            'old_price': old_price,
            'description': description,
            'short_description': short_desc,
            'image': image_url,
            'categories': category_str,
            'subcategories': subcategory_str,
            'brand': brand,
            'attributes': json.dumps(attributes, ensure_ascii=False) if attributes else None,
            'source': 'ultrapc'
        }
        
        return data
        
    except Exception as e:
        print_flush(f"❌ Error scraping details: {e}")
        return None

def process_excel_and_scrap(excel_path):
    """
    Read Excel file, loop through products, and scrape them.
    UPDATE: Inserts directly into DB.
    """
    if not PANDAS_AVAILABLE:
        print_flush("❌ Pandas library not found.")
        return

    print_flush(f"📂 Reading Excel: {excel_path}")
    try:
        df = pd.read_excel(excel_path, engine='openpyxl')
        print_flush(f"✅ Loaded {len(df)} rows.")
        
        # Identify Reference column
        cols = [c.lower() for c in df.columns]
        ref_col = None
        for c in df.columns:
            if c.lower() in ['ref', 'reference', 'code', 'sku']:
                ref_col = c
                break
        
        if not ref_col:
            print_flush("❌ Could not identify a Reference column in Excel.")
            return

        print_flush(f"ℹ️  Using column '{ref_col}' for references.")
        
        success_count = 0
        
        for index, row in df.iterrows():
            reference = str(row[ref_col]).strip()
            # Clean reference (remove .0 if it looks like int)
            if reference.endswith('.0'):
                reference = reference[:-2]
                
            if not reference or reference.lower() == 'nan':
                continue
                
            print_flush(f"\n[{index+1}/{len(df)}] Processing Code: {reference}")
            
            # 1. Get or Create Product in DB
            product_id, is_new = get_or_create_product(reference)
            if not product_id:
                print_flush("⚠️ Could not get/create product in DB. Skipping.")
                continue
                
            # 2. Search on UltraPC
            product_url = search_product_ultrapc(reference)
            
            if product_url:
                # 3. Scrape Data
                data = scrape_ultrapc_details(product_url)
                
                if data:
                    if data.get('old_price'):
                        print_flush(f"💰 Price found: {data.get('price')} MAD (Was: {data.get('old_price')} MAD)")
                    else:
                        print_flush(f"💰 Price found: {data.get('price')} MAD")
                    
                    # 4. Update Database
                    if update_product_in_database(product_id, data, 'ultrapc'):
                        print_flush("✅ Database updated successfully.")
                        success_count += 1
                    else:
                        print_flush("❌ Failed to update database.")
                else:
                    print_flush("❌ Scraping failed.")
            else:
                 print_flush("❌ Product not found on UltraPC.")
            
            # Rate limiting
            time.sleep(1)
        
        print_flush(f"\n🎉 Finished! Successfully processed {success_count} products.")

    except Exception as e:
        print_flush(f"❌ Error processing Excel: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        excel_file = sys.argv[1]
    else:
        excel_file = "BACHIR CODES.xlsx"
    
    if os.path.exists(excel_file):
        process_excel_and_scrap(excel_file)
    else:
        print_flush(f"❌ File {excel_file} not found.")

