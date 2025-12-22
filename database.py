"""
database.py
Connecteur simple et efficace pour les bases de données
4 bases de données :
1. dix_scraper (local)
2. dix_wp_ozar0 (distant)
3. dix_logicom (distant)
4. dix_temp (distant)
"""

import mysql.connector
from mysql.connector import Error
from typing import Optional, Dict, Any, List, Tuple
import logging
from datetime import datetime

# Configuration du logging
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Database:
    """
    Connecteur simple pour les bases de données
    """
    
    # Configuration - MODIFIEZ LES MOTS DE PASSE ICI
    CONFIG = {
        # 1. Base de données locale (scraping)
        'scraper': {
            'host': 'localhost',
            'user': 'root',
            'password': '',  # Mot de passe MySQL local
            'database': 'dix_scraper',
            'port': 3306,
            'charset': 'utf8mb4',
            'autocommit': True,
            'pool_name': 'scraper_pool',
            'pool_size': 5
        },
        
        # 2. Base de données WordPress distante
        'wp_ozar0': {
            'host': '146.59.110.187',
            'user': 'dix_wp_l1qfd',
            'password': 'eqzAJ$~2U7q25Nz%',  # À MODIFIER
            'database': 'dix_wp_ozar0',
            'connection_timeout': 10,
            'autocommit': True,
            'raise_on_warnings': False
        },
        
        # 3. Base de données Logicom distante
        'logicom': {
            'host': '146.59.110.187',
            'user': 'dix_wp_l1qfd',
            'password': 'eqzAJ$~2U7q25Nz%',  # Même mot de passe
            'database': 'dix_logicom',
            'connection_timeout': 10,
            'autocommit': True,
            'raise_on_warnings': False
        },
        
        # 4. Base de données Temp distante (synchronisation)
        'temp': {
            'host': '146.59.110.187',
            'user': 'dix_wp_l1qfd',
            'password': 'eqzAJ$~2U7q25Nz%',  # Même mot de passe
            'database': 'dix_temp',
            'connection_timeout': 10,
            'autocommit': True,
            'raise_on_warnings': False
        }
    }
    
    _connections_pool = {}
    
    @classmethod
    def get_connection(cls, db_type: str = 'scraper', use_pool: bool = True) -> Optional[mysql.connector.MySQLConnection]:
        """
        Obtient une connexion avec support de pool
        
        Args:
            db_type: 'scraper', 'wp_ozar0', 'logicom'
            use_pool: Utiliser le pooling de connexion
        """
        if db_type not in cls.CONFIG:
            logger.error(f"Type de base de données inconnu: {db_type}")
            return None
        
        try:
            config = cls.CONFIG[db_type].copy()
            
            if use_pool:
                pool_name = config.get('pool_name', f'{db_type}_pool')
                if pool_name not in cls._connections_pool:
                    # Créer le pool
                    cls._connections_pool[pool_name] = mysql.connector.pooling.MySQLConnectionPool(
                        pool_name=pool_name,
                        pool_size=config.get('pool_size', 3),
                        **{k: v for k, v in config.items() if k not in ['pool_name', 'pool_size']}
                    )
                
                return cls._connections_pool[pool_name].get_connection()
            else:
                # Connexion simple sans pool
                return mysql.connector.connect(**config)
                
        except Error as e:
            logger.error(f"Erreur connexion {db_type}: {e}")
            return None
    
    @staticmethod
    def execute_query(conn_type: str, query: str, params: Tuple = None, 
                     fetch: str = 'all', commit: bool = True) -> Any:
        """
        Exécute une requête SQL avec gestion robuste des erreurs
        
        Args:
            conn_type: Type de connexion
            query: Requête SQL
            params: Paramètres
            fetch: 'all', 'one', 'none'
            commit: Commit automatique
        """
        conn = Database.get_connection(conn_type)
        if not conn:
            logger.error(f"Impossible d'établir la connexion: {conn_type}")
            return None
        
        cursor = None
        try:
            cursor = conn.cursor(dictionary=True, buffered=True)
            start_time = datetime.now()
            
            cursor.execute(query, params or ())
            
            # Logging pour le débogage
            if logger.level <= logging.DEBUG:
                elapsed = (datetime.now() - start_time).total_seconds()
                logger.debug(f"Query executed in {elapsed:.3f}s: {query[:100]}...")
            
            if fetch == 'all':
                result = cursor.fetchall()
            elif fetch == 'one':
                result = cursor.fetchone()
            else:  # 'none'
                result = cursor.rowcount
                if commit and conn.autocommit is False:
                    conn.commit()
            
            return result
            
        except Error as e:
            logger.error(f"Erreur requête {conn_type}: {e}")
            if conn and conn.autocommit is False:
                conn.rollback()
            return None
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    @staticmethod
    def execute_many(conn_type: str, query: str, params_list: List[Tuple]) -> int:
        """
        Exécute plusieurs insertions en une fois
        """
        conn = Database.get_connection(conn_type)
        if not conn:
            return 0
        
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.executemany(query, params_list)
            conn.commit()
            return cursor.rowcount
        except Error as e:
            logger.error(f"Erreur executemany {conn_type}: {e}")
            conn.rollback()
            return 0
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    @staticmethod
    def get_scraper_tables() -> Dict[str, List[str]]:
        """Liste toutes les tables de dix_scraper par catégorie"""
        tables = Database.execute_query('scraper', "SHOW TABLES", fetch='all')
        if not tables:
            return {}
        
        categories = {
            'disty': [],
            'disway': [],
            'logicom': [],
            'gestion': [],
            'comparison': [],
            'other': []
        }
        
        for row in tables:
            table_name = list(row.values())[0]
            
            if 'dix_disty' in table_name:
                categories['disty'].append(table_name)
            elif 'dix_disway' in table_name:
                categories['disway'].append(table_name)
            elif 'dix_logicom' in table_name:
                categories['logicom'].append(table_name)
            elif table_name.startswith('gestion_'):
                categories['gestion'].append(table_name)
            elif table_name.startswith('ps_'):
                categories['comparison'].append(table_name)
            else:
                categories['other'].append(table_name)
        
        return categories

# ==================== FONCTIONS D'ACCÈS RAPIDE ====================

def connect_scraper(use_pool: bool = True):
    """Connexion à dix_scraper (local)"""
    return Database.get_connection('scraper', use_pool)

def connect_wp_ozar0(use_pool: bool = True):
    """Connexion à dix_wp_ozar0 (distant)"""
    return Database.get_connection('wp_ozar0', use_pool)

def connect_logicom(use_pool: bool = True):
    """Connexion à dix_logicom (distant)"""
    return Database.get_connection('logicom', use_pool)

def connect_temp(use_pool: bool = True):
    """Connexion à dix_temp (distant)"""
    return Database.get_connection('temp', use_pool)

# ==================== FONCTIONS DE REQUÊTES ====================

def query_scraper(query: str, params: Tuple = None, fetch: str = 'all', commit: bool = True):
    """Requête sur dix_scraper"""
    return Database.execute_query('scraper', query, params, fetch, commit)

def query_wp_ozar0(query: str, params: Tuple = None, fetch: str = 'all', commit: bool = True):
    """Requête sur dix_wp_ozar0"""
    return Database.execute_query('wp_ozar0', query, params, fetch, commit)

def query_logicom(query: str, params: Tuple = None, fetch: str = 'all', commit: bool = True):
    """Requête sur dix_logicom"""
    return Database.execute_query('logicom', query, params, fetch, commit)

# ==================== ALIAS POUR COMPATIBILITÉ ====================

# Pour votre code existant
disty_connect_srv = connect_scraper
connect_disway_srv = connect_scraper
connect_dix = connect_wp_ozar0

# N'utilisez pas cette fonction - elle est déjà définie plus haut
# connect_logicom_srv = connect_logicom  # Supprimez cette ligne

# Alias de compatibilité
connect_ozar0 = connect_wp_ozar0
query_ozar0 = query_wp_ozar0

# ==================== FONCTIONS UTILES ====================

def list_databases(server_type: str = 'local') -> List[str]:
    """
    Liste les bases de données disponibles
    """
    if server_type == 'local':
        return Database.execute_query('scraper', "SHOW DATABASES", fetch='all')
    else:
        return Database.execute_query('wp_ozar0', "SHOW DATABASES", fetch='all')

def test_all_connections():
    """Teste toutes les connexions configurées"""
    results = {}
    
    for db_name in Database.CONFIG.keys():
        try:
            conn = Database.get_connection(db_name, use_pool=False)
            if conn and conn.is_connected():
                # Test avec une requête simple
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()
                results[db_name] = "✅ Connecté et opérationnel"
                cursor.close()
                conn.close()
            else:
                results[db_name] = "❌ Échec de connexion"
        except Exception as e:
            results[db_name] = f"❌ Erreur: {str(e)[:100]}"
    
    return results

def get_database_info(db_type: str):
    """Affiche les informations de connexion pour une base de données"""
    if db_type in Database.CONFIG:
        config = Database.CONFIG[db_type].copy()
        # Masquer le mot de passe pour la sécurité
        if 'password' in config:
            config['password'] = '******' if config['password'] else '(vide)'
        return config
    return None

def get_table_schema(db_type: str, table_name: str):
    """Récupère le schéma d'une table"""
    query = f"DESCRIBE {table_name}"
    return Database.execute_query(db_type, query, fetch='all')

def check_table_exists(db_type: str, table_name: str) -> bool:
    """Vérifie si une table existe"""
    query = """
    SELECT COUNT(*) as count 
    FROM information_schema.tables 
    WHERE table_schema = DATABASE() 
    AND table_name = %s
    """
    result = Database.execute_query(db_type, query, (table_name,), fetch='one')
    return result and result['count'] > 0

# ==================== EXEMPLES D'UTILISATION ====================

if __name__ == "__main__":
    print("✅ CONNECTEUR DATABASE - 3 BASES DE DONNÉES")
    print("=" * 50)
    
    print("\n📊 Bases de données disponibles:")
    print("-" * 50)
    print("1. scraper    - Base locale (dix_scraper)")
    print("2. wp_ozar0   - WordPress distant (dix_wp_ozar0)")
    print("3. logicom    - Logicom distant (dix_logicom)")
    
    print("\n🔧 Configuration actuelle:")
    print("-" * 50)
    for db_name in Database.CONFIG.keys():
        info = get_database_info(db_name)
        print(f"\n{db_name}:")
        for key, value in info.items():
            print(f"  {key}: {value}")
    
    print("\n🧪 Test des connexions:")
    print("-" * 50)
    
    results = test_all_connections()
    for db_name, status in results.items():
        print(f"{db_name:15} {status}")
    
    # Exemple d'utilisation
    print("\n📋 Exemples d'utilisation:")
    print("-" * 50)
    print("""
# Connexion simple
conn = connect_scraper()

# Requête simple
result = query_scraper("SELECT * FROM ma_table LIMIT 5")

# Requête avec paramètres
result = query_scraper("SELECT * FROM ma_table WHERE id = %s", (1,), fetch='one')

# Insertion
query_scraper(
    "INSERT INTO ma_table (col1, col2) VALUES (%s, %s)", 
    ('valeur1', 'valeur2'), 
    fetch='none'
)

# Vérifier si une table existe
if check_table_exists('scraper', 'ma_table'):
    print("Table existe")
    """)
    
    print("\n⚠️  IMPORTANT: Modifiez les mots de passe dans la configuration CONFIG")
    print("=" * 50)
    print("✅ Connecteur prêt à l'emploi !")