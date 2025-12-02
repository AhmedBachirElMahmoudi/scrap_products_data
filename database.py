import mysql.connector
from mysql.connector import Error
from typing import Optional
import time
import logging

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DatabaseManager:
    """Gestionnaire centralisé des connexions aux bases de données"""
    
    # Configuration centralisée - VERSION FONCTIONNELLE
    _CONFIG = {
        'host': '146.59.110.187',
        'user': 'dix_wp_l1qfd',
        'password': 'eqzAJ$~2U7q25Nz%',
        'connection_timeout': 10,
        'autocommit': True,
        'raise_on_warnings': False
    }
    
    # Bases de données disponibles
    _DATABASES = {
        'disty': 'dix_disty',
        'disway': 'dix_disway',
        'dix': 'dix_wp_ozar0',
        'logicom': 'dix_logicom',
        'temp': 'dix_temp'
    }
    
    # Cache des connexions
    _connections = {}
    
    @classmethod
    def get_connection(cls, db_name: str, retry_count: int = 3, silent: bool = False) -> Optional[mysql.connector.MySQLConnection]:
        """
        Obtient une connexion à la base de données avec retry
        
        Args:
            db_name: Nom de la base (disty, disway, dix, logicom, temp)
            retry_count: Nombre de tentatives de reconnexion
            silent: Si True, réduit les logs
            
        Returns:
            Connexion MySQL ou None
        """
        if db_name not in cls._DATABASES:
            if not silent:
                logger.error(f"❌ Base de données '{db_name}' non reconnue")
                logger.info(f"Bases disponibles: {', '.join(cls._DATABASES.keys())}")
            return None
        
        database_name = cls._DATABASES[db_name]
        
        if not silent:
            logger.info(f"🔄 Connexion à {db_name.upper()}...")
        
        # Vérifier si une connexion existe déjà et est valide
        if db_name in cls._connections:
            try:
                if cls._connections[db_name].is_connected():
                    if not silent:
                        logger.info(f"♻️ Réutilisation connexion existante")
                    return cls._connections[db_name]
            except (Error, AttributeError):
                pass
        
        # Tentatives de connexion avec retry
        for attempt in range(1, retry_count + 1):
            try:
                start_time = time.time()
                
                connection = mysql.connector.connect(
                    **cls._CONFIG,
                    database=database_name
                )
                
                connection_time = time.time() - start_time
                
                if connection.is_connected():
                    if not silent:
                        # Récupérer des infos sur la connexion
                        cursor = connection.cursor()
                        cursor.execute("SELECT DATABASE(), VERSION()")
                        db_info = cursor.fetchone()
                        cursor.close()
                        
                        logger.info(f"✅ Connexion réussie à {db_name.upper()}")
                        logger.info(f"   📊 Base: {db_info[0]}")
                        logger.info(f"   🔧 Serveur: {db_info[1]}")
                        logger.info(f"   ⚡ Temps: {connection_time:.2f}s")
                    
                    cls._connections[db_name] = connection
                    return connection
                    
            except Error as e:
                if attempt < retry_count:
                    wait_time = attempt * 2
                    if not silent:
                        logger.warning(f"⚠️ Tentative {attempt} échouée, retry dans {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"❌ Échec de connexion à {db_name}: {e}")
                    return None
            
            except Exception as e:
                logger.error(f"💣 Erreur inattendue: {type(e).__name__}: {e}")
                return None
        
        return None
    
    @classmethod
    def execute_query(cls, db_name: str, query: str, params: tuple = None, fetch: str = 'all'):
        """
        Exécute une requête SQL sur une base donnée
        
        Args:
            db_name: Nom de la base
            query: Requête SQL
            params: Paramètres de la requête (tuple)
            fetch: 'all', 'one', 'none' (pour INSERT/UPDATE/DELETE)
            
        Returns:
            Résultats de la requête ou None
        """
        conn = cls.get_connection(db_name, silent=True)
        if not conn:
            return None
        
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, params or ())
            
            if fetch == 'all':
                result = cursor.fetchall()
            elif fetch == 'one':
                result = cursor.fetchone()
            else:
                result = cursor.rowcount
            
            cursor.close()
            return result
            
        except Error as e:
            logger.error(f"❌ Erreur requête sur {db_name}: {e}")
            logger.error(f"   Query: {query[:100]}...")
            return None
    
    @classmethod
    def test_connection(cls, db_name: str) -> bool:
        """
        Test rapide de connexion
        
        Args:
            db_name: Nom de la base
            
        Returns:
            True si connexion réussie, False sinon
        """
        if db_name not in cls._DATABASES:
            return False
        
        try:
            connection = mysql.connector.connect(
                **cls._CONFIG,
                database=cls._DATABASES[db_name]
            )
            
            if connection.is_connected():
                connection.close()
                return True
            
        except:
            return False
        
        return False
    
    @classmethod
    def close_connection(cls, db_name: str):
        """Ferme une connexion spécifique"""
        if db_name in cls._connections:
            try:
                if cls._connections[db_name].is_connected():
                    cls._connections[db_name].close()
                    logger.info(f"🔌 Connexion {db_name} fermée")
                del cls._connections[db_name]
            except Error as e:
                logger.error(f"Erreur fermeture {db_name}: {e}")
    
    @classmethod
    def close_all_connections(cls):
        """Ferme toutes les connexions actives"""
        logger.info("🔌 Fermeture de toutes les connexions...")
        for db_name in list(cls._connections.keys()):
            cls.close_connection(db_name)
        logger.info("✅ Toutes les connexions fermées")
    
    @classmethod
    def get_connection_status(cls):
        """Affiche le statut de toutes les connexions"""
        logger.info("📊 STATUT DES CONNEXIONS")
        logger.info("=" * 60)
        
        for db_name in cls._DATABASES.keys():
            if db_name in cls._connections:
                try:
                    is_connected = cls._connections[db_name].is_connected()
                    status = "✅ ACTIVE" if is_connected else "❌ INACTIVE"
                except:
                    status = "⚠️ ERREUR"
            else:
                status = "⭕ AUCUNE"
            
            logger.info(f"   {db_name.upper():10} : {status}")
        
        logger.info("=" * 60)
    
    @classmethod
    def get_table_count(cls, db_name: str) -> int:
        """Retourne le nombre de tables dans une base"""
        result = cls.execute_query(db_name, "SHOW TABLES", fetch='all')
        return len(result) if result else 0
    
    @classmethod
    def get_database_info(cls, db_name: str) -> dict:
        """Retourne des informations détaillées sur une base"""
        conn = cls.get_connection(db_name, silent=True)
        if not conn:
            return {}
        
        try:
            cursor = conn.cursor()
            
            # Info générale
            cursor.execute("SELECT DATABASE(), VERSION()")
            db_info = cursor.fetchone()
            
            # Nombre de tables
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            
            # Taille de la base
            cursor.execute("""
                SELECT 
                    SUM(data_length + index_length) / 1024 / 1024 AS size_mb
                FROM information_schema.TABLES 
                WHERE table_schema = %s
            """, (cls._DATABASES[db_name],))
            size = cursor.fetchone()
            
            cursor.close()
            
            return {
                'database': db_info[0],
                'version': db_info[1],
                'table_count': len(tables),
                'size_mb': round(size[0], 2) if size and size[0] else 0
            }
            
        except Error as e:
            logger.error(f"Erreur info base {db_name}: {e}")
            return {}

# Fonctions d'accès direct pour faciliter l'importation
def get_disty_connection():
    return DatabaseManager.get_connection('disty')

def get_disway_connection():
    return DatabaseManager.get_connection('disway')

def get_dix_connection():
    return DatabaseManager.get_connection('dix')

def get_logicom_connection():
    return DatabaseManager.get_connection('logicom')

def get_temp_connection():
    return DatabaseManager.get_connection('temp')

# Alias pour compatibilité avec votre code existant
disty_connect_srv = get_disty_connection
connect_disway_srv = get_disway_connection
connect_dix = get_dix_connection
connect_logicom_srv = get_logicom_connection
connect_temp_srv = get_temp_connection

# Script de test si exécuté directement
if __name__ == "__main__":
    logger.info("🧪 TEST COMPLET DU DATABASE MANAGER")
    logger.info("=" * 60)
    
    # Test de toutes les bases
    databases_to_test = ['temp', 'disway', 'disty', 'logicom', 'dix']
    
    for db_name in databases_to_test:
        logger.info(f"\n📦 Test de {db_name.upper()}")
        logger.info("-" * 60)
        
        conn = DatabaseManager.get_connection(db_name)
        
        if conn:
            info = DatabaseManager.get_database_info(db_name)
            if info:
                logger.info(f"   📋 Tables: {info['table_count']}")
                logger.info(f"   💾 Taille: {info['size_mb']} MB")
        
        time.sleep(0.5)
    
    # Afficher le statut final
    logger.info("\n")
    DatabaseManager.get_connection_status()
    
    # Test de requête simple
    logger.info("\n🔍 TEST DE REQUÊTE")
    logger.info("-" * 60)
    result = DatabaseManager.execute_query('temp', "SHOW TABLES", fetch='all')
    if result:
        logger.info(f"✅ Requête réussie: {len(result)} tables trouvées")
    
    # Fermer toutes les connexions
    logger.info("\n")
    DatabaseManager.close_all_connections()
    
    logger.info("\n✅ TOUS LES TESTS TERMINÉS")