import mysql.connector
from pymongo import MongoClient
import os # <-- Tambahkan import ini

def connect_to_mysql():
    try:
        conn = mysql.connector.connect(
            # Ambil detail koneksi dari Environment Variables
            host=os.environ.get("DB_HOST"),
            user=os.environ.get("DB_USER"),
            password=os.environ.get("DB_PASSWORD"),
            database=os.environ.get("DB_NAME")
        )
        return conn
    except mysql.connector.Error as e:
        print(f"Error saat menghubungkan ke MySQL: {e}")
        return None


def connect_to_mongodb():
    """Fungsi untuk membuat dan mengembalikan koneksi ke database MongoDB."""
    try:
        # Ambil connection string dari Environment Variable
        mongo_uri = os.environ.get("MONGO_URI")
        client = MongoClient(mongo_uri)
        db = client['library_nosql_db'] # Anda bisa tetap menggunakan nama db ini
        return db
    except Exception as e:
        print(f"Error saat menghubungkan ke MongoDB: {e}")
        return None
