
from db import get_db_connection
from mysql.connector import Error


def create_sales_tables():
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        # Table 1: Sales invoices
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sales (
                sale_id INT AUTO_INCREMENT PRIMARY KEY,
                invoice_number VARCHAR(40) NOT NULL UNIQUE,
                customer_id INT NOT NULL,
                sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                subtotal DECIMAL(12,2) NOT NULL DEFAULT 0.00,
                discount_amount DECIMAL(12,2) NOT NULL DEFAULT 0.00,
                tax_amount DECIMAL(12,2) NOT NULL DEFAULT 0.00,
                total_amount DECIMAL(12,2) NOT NULL DEFAULT 0.00,
                amount_paid DECIMAL(12,2) NOT NULL DEFAULT 0.00,
                payment_status VARCHAR(20) NOT NULL DEFAULT 'Unpaid',

                CONSTRAINT fk_sales_customer
                    FOREIGN KEY (customer_id)
                    REFERENCES customers(customer_id)
                    ON UPDATE CASCADE
                    ON DELETE RESTRICT
            ) ENGINE=InnoDB
        """)

        # Table 2: Products belonging to each invoice
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sale_items (
                sale_item_id INT AUTO_INCREMENT PRIMARY KEY,
                sale_id INT NOT NULL,
                product_id INT NULL,
                product_name VARCHAR(150) NOT NULL,
                quantity DECIMAL(12,2) NOT NULL,
                unit_price DECIMAL(12,2) NOT NULL,
                line_total DECIMAL(12,2) NOT NULL,

                CONSTRAINT fk_sale_items_sale
                    FOREIGN KEY (sale_id)
                    REFERENCES sales(sale_id)
                    ON UPDATE CASCADE
                    ON DELETE CASCADE,

                CONSTRAINT fk_sale_items_product
                    FOREIGN KEY (product_id)
                    REFERENCES products(product_id)
                    ON UPDATE CASCADE
                    ON DELETE SET NULL
            ) ENGINE=InnoDB
        """)

        connection.commit()

        print("Success! Sales tables are ready.")
        print("Created or verified: sales")
        print("Created or verified: sale_items")
        print("Existing customer and product records were not changed.")

    except Error as error:
        if connection and connection.is_connected():
            connection.rollback()

        print("Could not create sales tables:", error)

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()


if __name__ == "__main__":
    create_sales_tables()
