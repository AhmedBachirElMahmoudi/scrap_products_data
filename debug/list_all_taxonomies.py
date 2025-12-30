from database import connect_wp_ozar0

def list_taxonomies():
    conn = connect_wp_ozar0()
    cursor = conn.cursor(dictionary=True)
    PREFIX = "9Ew5q6v_"
    
    print("Fetching all taxonomies starting with 'pa_'...")
    cursor.execute(f"SELECT DISTINCT taxonomy FROM {PREFIX}term_taxonomy WHERE taxonomy LIKE 'pa_%'")
    rows = cursor.fetchall()
    
    print(f"Found {len(rows)} attribute taxonomies:")
    for row in rows:
        print(f" - {row['taxonomy']}")
        
    conn.close()

if __name__ == "__main__":
    list_taxonomies()
