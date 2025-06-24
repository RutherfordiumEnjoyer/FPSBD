# database_connector.py (VERSI FINAL)

import pymysql.cursors
from pymongo import MongoClient
import os

def connect_to_mysql():
    """
    Fungsi koneksi ke MySQL menggunakan PyMySQL dengan semua konfigurasi
    yang diperlukan untuk koneksi cloud yang stabil.
    """
    try:
        # Mengambil port dan mengubahnya menjadi integer
        db_port = int(os.environ.get("DB_PORT"))

        conn = pymysql.connect(
            host=os.environ.get("DB_HOST"),
            user=os.environ.get("DB_USER"),
            password=os.environ.get("DB_PASSWORD"),
            database=os.environ.get("DB_NAME"),
            port=db_port,
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=30 # Waktu tunggu koneksi
        )
        return conn
    except (pymysql.MySQLError, TypeError, ValueError) as e:
        # Menangkap error jika koneksi gagal atau jika DB_PORT tidak ada/bukan angka
        print(f"Error saat menghubungkan ke MySQL: {e}")
        return None

def connect_to_mongodb():
    """Fungsi koneksi ke MongoDB."""
    try:
        mongo_uri = os.environ.get("MONGO_URI")
        client = MongoClient(mongo_uri)
        # Menggunakan nama database dari URI jika memungkinkan, atau nama default
        db_name = MongoClient(mongo_uri).get_default_database().name
        db = client[db_name]
        return db
    except Exception as e:
        print(f"Error saat menghubungkan ke MongoDB: {e}")
        return None
