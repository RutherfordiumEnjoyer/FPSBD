# database_connector.py (Versi Debugging dengan Hardcode)

import pymysql.cursors
from pymongo import MongoClient
import os

def connect_to_mysql():
    """
    Fungsi koneksi ke MySQL untuk tes debugging.
    Kredensial ditulis langsung untuk memastikan tidak ada masalah Environment Variable.
    """
    try:
        # --- UBAH BAGIAN INI DENGAN DETAIL DARI RAILWAY ANDA ---
        conn = pymysql.connect(
            host="yamanote.proxy.rlwy.net",
            user="root",
            password="BThcMOXoyxnuZWGbjtfBSVSXFRESgphg",
            database="railway",
            port=38093,
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=30
        )
        return conn
    except pymysql.MySQLError as e:
        # Kita buat pesan errornya lebih spesifik untuk tes ini
        print(f"Error dengan kredensial hardcoded: {e}")
        return None

def connect_to_mongodb():
    # ... (fungsi ini tidak perlu diubah)
    try:
        mongo_uri = os.environ.get("MONGO_URI")
        client = MongoClient(mongo_uri)
        db = client['library_nosql_db']
        return db
    except Exception as e:
        print(f"Error saat menghubungkan ke MongoDB: {e}")
        return None
