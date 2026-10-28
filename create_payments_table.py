
from db import get_db_connection
from mysql.connector import Error


def create_payments_table():
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                payment_id INT AUTO_INCREMENT PRIMARY KEY,
                sale_id INT NOT NULL,
                amount DECIMAL(12,2) NOT NULL,
                payment_method VARCHAR(30) NOT NULL DEFAULT 'Cash',
                reference_number VARCHAR(100) NULL,
                notes TEXT NULL,
                payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                CONSTRAINT fk_payments_sale
                    FOREIGN KEY (sale_id)
                    REFERENCES sales(sale_id)
                    ON UPDATE CASCADE
                    ON DELETE RESTRICT
            ) ENGINE=InnoDB
        """)

        connection.commit()
        print("Success! Payments table is ready.")
        print("Existing invoices and customer records were not changed.")

    except Error as error:
        if connection and connection.is_connected():
            connection.rollback()

        print("Could not create Payments table:", error)

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()


if __name__ == "__main__":
    create_payments_table()
