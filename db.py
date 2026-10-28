
import os

import mysql.connector
from dotenv import load_dotenv

load_dotenv()


def get_db_connection():
    """Create and return a connection to the SalesManager database."""
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        database=os.getenv("DB_NAME", "salesmanager_db"),
        user=os.getenv("DB_USER", "salesmanager_user"),
        password=os.getenv("DB_PASSWORD"),
    )


if __name__ == "__main__":
    try:
        connection = get_db_connection()
        print("Success! Connected to SalesManager MySQL database.")

        cursor = connection.cursor()
        cursor.execute("SELECT DATABASE()")
        print("Database:", cursor.fetchone()[0])

        cursor.close()
        connection.close()

    except mysql.connector.Error as error:
        print("Database connection failed:", error)
