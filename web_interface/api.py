"""
API Flask pour la comparaison de prix DIX vs concurrents
"""
import sys
import os

# Ajouter le dossier parent au path pour importer database.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, jsonify, request
from flask_cors import CORS
from decimal import Decimal
import json
from database import connect_scraper

app = Flask(__name__)
CORS(app)

def get_db_connection():
    """Crée une connexion à la base de données en utilisant le module database"""
    try:
        conn = connect_scraper(use_pool=False)
        if conn is None:
            print("❌ Erreur: La connexion à la base de données a échoué")
            print("Vérifiez les paramètres de connexion dans database.py")
            return None
        
        # Vérifier que la connexion est active
        if not conn.is_connected():
            print("❌ Erreur: La connexion n'est pas active")
            return None
            
        return conn
    except Exception as e:
        print(f"❌ Erreur lors de la connexion: {e}")
        return None

def decimal_to_float(obj):
    """Convertit les Decimal en float pour JSON"""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

@app.route('/api/products', methods=['GET'])
def get_products():
    """Récupère tous les produits avec leurs prix"""
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({
                'success': False,
                'error': 'Impossible de se connecter à la base de données. Vérifiez que MySQL est démarré et que les identifiants dans database.py sont corrects.'
            }), 500
            
        cursor = conn.cursor(dictionary=True)
        
        query = """
        SELECT 
            id,
            reference,
            price as dix_price,
            crenova_price,
            duga_price,
            linksolutions_price,
            tabtel_price,
            mies_price,
            rightech_price,
            joutech_price
        FROM ps_products_comparison_v2
        WHERE price IS NOT NULL
        ORDER BY reference
        """
        
        cursor.execute(query)
        products = cursor.fetchall()
        
        # Enrichir les données avec calculs
        enriched_products = []
        for product in products:
            enriched = enrich_product_data(product)
            enriched_products.append(enriched)
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'count': len(enriched_products),
            'products': enriched_products
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/products/search', methods=['GET'])
def search_products():
    """Recherche produits par référence ou titre"""
    query = request.args.get('q', '').strip()
    
    if not query:
        return jsonify({
            'success': False,
            'error': 'Query parameter required'
        }), 400
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        sql = """
        SELECT 
            id,
            reference,
            price as dix_price,
            crenova_price,
            duga_price,
            linksolutions_price,
            tabtel_price,
            mies_price,
            rightech_price,
            joutech_price
        FROM ps_products_comparison_v2
        WHERE price IS NOT NULL
        AND reference LIKE %s
        ORDER BY reference
        """
        
        search_term = f'%{query}%'
        cursor.execute(sql, (search_term,))
        products = cursor.fetchall()
        
        enriched_products = [enrich_product_data(p) for p in products]
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'count': len(enriched_products),
            'products': enriched_products
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/products/cheaper', methods=['GET'])
def get_cheaper_products():
    """Produits où DIX est moins cher que tous les concurrents"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = """
        SELECT 
            id,
            reference,
            price as dix_price,
            crenova_price,
            duga_price,
            linksolutions_price,
            tabtel_price,
            mies_price,
            rightech_price,
            joutech_price
        FROM ps_products_comparison_v2
        WHERE price IS NOT NULL
        AND (
            (crenova_price IS NULL OR price < crenova_price) AND
            (duga_price IS NULL OR price < duga_price) AND
            (linksolutions_price IS NULL OR price < linksolutions_price) AND
            (tabtel_price IS NULL OR price < tabtel_price) AND
            (mies_price IS NULL OR price < mies_price) AND
            (rightech_price IS NULL OR price < rightech_price) AND
            (joutech_price IS NULL OR price < joutech_price)
        )
        ORDER BY reference
        """
        
        cursor.execute(query)
        products = cursor.fetchall()
        
        enriched_products = [enrich_product_data(p) for p in products]
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'count': len(enriched_products),
            'products': enriched_products
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/products/expensive', methods=['GET'])
def get_expensive_products():
    """Produits où DIX est plus cher que le minimum concurrent"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = """
        SELECT 
            id,
            reference,
            price as dix_price,
            crenova_price,
            duga_price,
            linksolutions_price,
            tabtel_price,
            mies_price,
            rightech_price,
            joutech_price
        FROM ps_products_comparison_v2
        WHERE price IS NOT NULL
        ORDER BY reference
        """
        
        cursor.execute(query)
        products = cursor.fetchall()
        
        # Filtrer ceux où DIX est plus cher
        expensive_products = []
        for product in products:
            enriched = enrich_product_data(product)
            if enriched.get('status') == 'expensive':
                expensive_products.append(enriched)
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'count': len(expensive_products),
            'products': expensive_products
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Statistiques globales"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Total produits avec prix DIX
        cursor.execute("""
            SELECT COUNT(*) as total 
            FROM ps_products_comparison_v2 
            WHERE price IS NOT NULL
        """)
        total = cursor.fetchone()['total']
        
        # Produits où DIX est le moins cher
        query = """
        SELECT COUNT(*) as count
        FROM ps_products_comparison_v2
        WHERE price IS NOT NULL
        AND (
            (crenova_price IS NULL OR price <= crenova_price) AND
            (duga_price IS NULL OR price <= duga_price) AND
            (linksolutions_price IS NULL OR price <= linksolutions_price) AND
            (tabtel_price IS NULL OR price <= tabtel_price) AND
            (mies_price IS NULL OR price <= mies_price) AND
            (rightech_price IS NULL OR price <= rightech_price) AND
            (joutech_price IS NULL OR price <= joutech_price)
        )
        """
        cursor.execute(query)
        cheaper = cursor.fetchone()['count']
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'stats': {
                'total_products': total,
                'dix_cheaper': cheaper,
                'dix_expensive': total - cheaper,
                'dix_cheaper_percentage': round((cheaper / total * 100), 2) if total > 0 else 0
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def enrich_product_data(product):
    """Enrichit les données produit avec calculs de comparaison"""
    dix_price = float(product['dix_price']) if product['dix_price'] else None
    
    # Liste des prix concurrents
    competitor_prices = []
    sites = ['crenova', 'duga', 'linksolutions', 'tabtel', 'mies', 'rightech', 'joutech']
    
    competitor_data = {}
    for site in sites:
        price = product.get(f'{site}_price')
        if price:
            price_float = float(price)
            competitor_prices.append(price_float)
            competitor_data[site] = price_float
        else:
            competitor_data[site] = None
    
    # Calculs
    min_competitor = min(competitor_prices) if competitor_prices else None
    max_competitor = max(competitor_prices) if competitor_prices else None
    avg_competitor = sum(competitor_prices) / len(competitor_prices) if competitor_prices else None
    
    # Position et statut
    status = 'best'
    position = 1
    dix_vs_min_percent = None
    
    if dix_price and min_competitor:
        dix_vs_min_percent = round(((dix_price - min_competitor) / min_competitor * 100), 2)
        
        # Calculer position
        all_prices = [dix_price] + competitor_prices
        all_prices_sorted = sorted(all_prices)
        position = all_prices_sorted.index(dix_price) + 1
        
        # Déterminer statut
        if dix_price <= min_competitor:
            status = 'best'
        elif dix_vs_min_percent <= 5:
            status = 'competitive'
        else:
            status = 'expensive'
    
    return {
        'id': product['id'],
        'reference': product['reference'],
        'dix_price': dix_price,
        'competitor_prices': competitor_data,
        'min_competitor': min_competitor,
        'max_competitor': max_competitor,
        'avg_competitor': round(avg_competitor, 2) if avg_competitor else None,
        'dix_vs_min': f"{'+' if dix_vs_min_percent and dix_vs_min_percent > 0 else ''}{dix_vs_min_percent}%" if dix_vs_min_percent is not None else None,
        'position': position,
        'status': status,
        'available_sites': len([p for p in competitor_prices if p]) + 1
    }

if __name__ == '__main__':
    print("🚀 Démarrage de l'API de comparaison de prix...")
    print("📊 Endpoints disponibles:")
    print("  GET /api/products - Tous les produits")
    print("  GET /api/products/search?q=<query> - Recherche")
    print("  GET /api/products/cheaper - DIX moins cher")
    print("  GET /api/products/expensive - DIX plus cher")
    print("  GET /api/stats - Statistiques")
    print("\n🌐 API accessible sur: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
