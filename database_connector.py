import mysql.connector
from pymongo import MongoClient
import os

def connect_to_mysql():
    try:
        conn = mysql.connector.connect(
            host=os.environ.get("DB_HOST"),
            user=os.environ.get("DB_USER"),
            password=os.environ.get("DB_PASSWORD"),
            database=os.environ.get("DB_NAME"),
            ssl_verify_cert=True,
            ssl_ca=os.environ.get("MYSQL_ATTR_SSL_CA")
        )
        return conn
    except mysql.connector.Error as e:
        # Mencetak error ke log Vercel untuk debugging
        print(f"Error saat menghubungkan ke MySQL: {e}")
        return None

def connect_to_mongodb():
    """Fungsi untuk membuat dan mengembalikan koneksi ke database MongoDB."""
    try:
        mongo_uri = os.environ.get("MONGO_URI")
        client = MongoClient(mongo_uri)
        db = client['library_nosql_db']
        return db
    except Exception as e:
        print(f"Error saat menghubungkan ke MongoDB: {e}")
        return None
