import os
import pyodbc
from dotenv import load_dotenv

# Cargar variables del archivo .env
load_dotenv()

def get_connection():
    server = os.getenv("DB_SERVER")
    database = os.getenv("DB_NAME")
    driver = os.getenv("DB_DRIVER")
    trust_certificate = os.getenv("DB_TRUST_CERTIFICATE", "yes")

    connection_string = (
        f"DRIVER={{{driver}}};"
        f"SERVER={server};"
        f"DATABASE={database};"
        "Trusted_Connection=yes;"
        f"TrustServerCertificate={trust_certificate};"
    )

    return pyodbc.connect(connection_string, timeout=5)


def test_connection():
    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute("SELECT @@SERVERNAME, DB_NAME(), SYSTEM_USER")

        result = cursor.fetchone()

        print("CONEXIÓN EXITOSA")
        print("Servidor:", result[0])
        print("Base de datos:", result[1])
        print("Usuario:", result[2])

        cursor.close()
        connection.close()

    except pyodbc.Error as error:
        print("ERROR DE CONEXIÓN:")
        print(error)


if __name__ == "__main__":
    test_connection()