from database import connect_scraper

conn = connect_scraper()
cursor = conn.cursor(dictionary=True)
cursor.execute("SELECT * FROM ps_brands_mapping WHERE brand_name LIKE '%HP%'")
results = cursor.fetchall()
print("Results for HP:")
for row in results:
    print(row)
conn.close()
