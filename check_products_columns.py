from db import get_db_connection

connection = None
cursor = None

try:
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("SHOW COLUMNS FROM products")

    print("\nColumns in your products table:\n")

    for column in cursor.fetchall():
       print(column)

except Exception as error:
    print("Could not inspect products table:", error)

finally:
    if cursor:
        cursor.close()

    if connection and connection.is_connected():
        connection.close()