
from db import get_db_connection
from mysql.connector import Error


def create_products_table():
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                product_id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(150) NOT NULL,
                description TEXT NULL,
                price DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
                stock_quantity INT NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    ON UPDATE CURRENT_TIMESTAMP
            )
        """)

        connection.commit()
        print("Success! Products table is ready.")
        print("Database: salesmanager_db")
        print("Existing customer records have not been changed.")

    except Error as error:
        if connection and connection.is_connected():
            connection.rollback()

        print("Could not create Products table:", error)

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()


if __name__ == "__main__":
    create_products_table()
