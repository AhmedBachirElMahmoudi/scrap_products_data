import mysql.connector
from database import connect_scraper

def reset_all_statuses():
    try:
        conn = connect_scraper()
        if not conn:
            print("Connexion echouee")
            return

        cursor = conn.cursor()
        
        sites = ['crenova', 'duga', 'linksolutions', 'tabtel', 'mies', 'rightech', 'joutech']
        
        # Construire la requête de mise à jour
        updates = []
        for site in sites:
            updates.append(f"{site}_status = 0")
            
        query = f"UPDATE ps_products_comparison_v2 SET {', '.join(updates)}"
        
        print(f"Execution de la requete: UPDATE ps_products_comparison_v2 SET ...")
        cursor.execute(query)
        
        rows_affected = cursor.rowcount
        conn.commit()
        
        print(f"Succes! {rows_affected} lignes mises a jour (tous les statuts remis a 0).")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Erreur: {e}")

if __name__ == "__main__":
    reset_all_statuses()
