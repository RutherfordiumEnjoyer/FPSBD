import pymysql.cursors
from pymongo import MongoClient
import os

def connect_to_mysql():
    """
    Fungsi koneksi ke MySQL menggunakan PyMySQL,
    yang lebih kompatibel dengan lingkungan serverless.
    """
    try:

        conn = pymysql.connect(
            host=os.environ.get("DB_HOST"),
            user=os.environ.get("DB_USER"),
            password=os.environ.get("DB_PASSWORD"),
            database=os.environ.get("DB_NAME"),

            cursorclass=pymysql.cursors.DictCursor,

            ssl={'ca': os.environ.get("MYSQL_ATTR_SSL_CA")}
        )
        return conn
    except pymysql.MySQLError as e:

        print(f"Error saat menghubungkan ke MySQL dengan PyMySQL: {e}")
        return None

def connect_to_mongodb():
    """Fungsi koneksi ke MongoDB (tidak ada perubahan di sini)."""
    try:
        mongo_uri = os.environ.get("MONGO_URI")
        client = MongoClient(mongo_uri)
        db = client['library_nosql_db']
        return db
    except Exception as e:
        print(f"Error saat menghubungkan ke MongoDB: {e}")
        return None
