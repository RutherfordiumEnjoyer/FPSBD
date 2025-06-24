import mysql.connector
from pymongo import MongoClient

def connect_to_mysql():
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="fp_kelompok6"
        )
        return conn
    except mysql.connector.Error as e:
        print(f"Error saat menghubungkan ke MySQL: {e}")
        return None


def connect_to_mongodb():
    """Fungsi untuk membuat dan mengembalikan koneksi ke database MongoDB."""
    try:
        client = MongoClient('mongodb://localhost:27017/')
        db = client['library_nosql_db']
        return db
    except Exception as e:
        print(f"Error saat menghubungkan ke MongoDB: {e}")
        return None