
from db import get_db_connection

connection = None
cursor = None

try:
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("SHOW TABLES")
    tables = [row[0] for row in cursor.fetchall()]

    print("\nTables in salesmanager_db:")
    for table in tables:
        print("-", table)

    for table in tables:
        if table.lower() in {
            "sales", "sale_items", "sales_items",
            "invoices", "payments", "customers", "products"
        }:
            print(f"\nColumns in {table}:")
            cursor.execute(f"SHOW COLUMNS FROM `{table}`")
            for column in cursor.fetchall():
                print(column)

except Exception as error:
    print("Database inspection failed:", error)

finally:
    if cursor:
        cursor.close()

    if connection and connection.is_connected():
        connection.close()
