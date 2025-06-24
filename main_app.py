# main_app.py (VERSI FINAL - LENGKAP & DIPERIKSA ULANG)

from collections import Counter
from database_connector import connect_to_mysql, connect_to_mongodb
from datetime import date, timedelta, datetime
from werkzeug.security import generate_password_hash, check_password_hash
import pymysql

def get_all_users_dict():
    conn = connect_to_mysql()
    if conn is None: return {}
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT user_id, full_name FROM users")
            users = cursor.fetchall()
        return {user['user_id']: user['full_name'] for user in users}
    except Exception as e:
        print(f"[ERROR-get_all_users_dict]: {e}")
        return {}
    finally:
        if conn:
            conn.close()

def get_all_book_titles_dict():
    conn = connect_to_mysql()
    if conn is None: return {}
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT book_id, title FROM books")
            books = cursor.fetchall()
        return {book['book_id']: book['title'] for book in books}
    except Exception as e:
        print(f"[ERROR-get_all_book_titles_dict]: {e}")
        return {}
    finally:
        if conn:
            conn.close()

def tambah_buku(title, author, publication_year, stock, category_id):
    conn = connect_to_mysql()
    if conn is None:
        return "Koneksi database gagal."
    try:
        with conn.cursor() as cursor:
            query = "INSERT INTO books (title, author, publication_year, stock, category_id) VALUES (%s, %s, %s, %s, %s)"
            values = (title, author, publication_year, stock, category_id)
            cursor.execute(query, values)
        conn.commit()
        return True
    except Exception as e:
        if "1452" in str(e):
            return "Gagal menambahkan buku: ID Kategori tidak ditemukan."
        else:
            return f"Gagal menambahkan buku: {e}"
    finally:
        if conn:
            conn.close()

def lihat_semua_buku():
    conn = connect_to_mysql()
    if conn is None: 
        return []
    try:
        with conn.cursor() as cursor:
            query = "SELECT b.*, c.category_name FROM books b LEFT JOIN categories c ON b.category_id = c.category_id ORDER BY b.book_id"
            cursor.execute(query)
            books = cursor.fetchall()
        return books
    except Exception as e:
        print(f"[ERROR-lihat_semua_buku]: {e}")
        return []
    finally:
        if conn:
            conn.close()

def hapus_buku(book_id):
    conn = connect_to_mysql()
    if conn is None:
        return "Koneksi database gagal."
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM borrowals WHERE book_id = %s AND status = 'borrowed'", (book_id,))
            if cursor.fetchone()['COUNT(*)'] > 0:
                return "Buku tidak dapat dihapus karena masih ada yang meminjam."

            cursor.execute("DELETE FROM books WHERE book_id = %s", (book_id,))
            rowcount = cursor.rowcount
        conn.commit()
        if rowcount > 0:
            return True
        else:
            return "Buku dengan ID tersebut tidak ditemukan."
    except Exception as e:
        return f"Gagal menghapus buku: {e}"
    finally:
        if conn:
            conn.close()

def get_book_by_id(book_id):
    conn = connect_to_mysql()
    if conn is None:
        return None
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM books WHERE book_id = %s", (book_id,))
            book = cursor.fetchone()
        return book
    except Exception as e:
        print(f"[ERROR-get_book_by_id]: {e}")
        return None
    finally:
        if conn:
            conn.close()

def update_buku(book_id, title, author, publication_year, stock, category_id):
    conn = connect_to_mysql()
    if conn is None:
        return "Koneksi database gagal."
    try:
        with conn.cursor() as cursor:
            query = """
                UPDATE books 
                SET title = %s, author = %s, publication_year = %s, stock = %s, category_id = %s 
                WHERE book_id = %s
            """
            values = (title, author, publication_year, stock, category_id, book_id)
            cursor.execute(query, values)
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        return f"Gagal memperbarui buku: {e}"
    finally:
        if conn:
            conn.close()

def lihat_semua_kategori():
    conn = connect_to_mysql()
    if conn is None:
        return []
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM categories ORDER BY category_id")
            categories = cursor.fetchall()
        return categories
    except Exception as e:
        print(f"[ERROR-lihat_semua_kategori]: {e}")
        return []
    finally:
        if conn:
            conn.close()

def pinjam_buku(user_id, username, book_id):
    conn = connect_to_mysql()
    if conn is None: return "Koneksi database gagal."
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT stock FROM books WHERE book_id = %s", (book_id,))
            result = cursor.fetchone()
            if result is None or result['stock'] <= 0:
                return "Gagal meminjam: Buku tidak ditemukan atau stok habis."
            
            cursor.execute("UPDATE books SET stock = stock - 1 WHERE book_id = %s", (book_id,))
            tgl_pinjam = date.today()
            tgl_kembali = tgl_pinjam + timedelta(days=7)
            query_borrow = "INSERT INTO borrowals (user_id, book_id, borrow_date, due_date, status) VALUES (%s, %s, %s, %s, %s)"
            values_borrow = (user_id, book_id, tgl_pinjam, tgl_kembali, 'borrowed')
            cursor.execute(query_borrow, values_borrow)
        conn.commit()
        log_activity(user_id, username, "BORROW_BOOK", {"book_id": book_id})
        return True
    except Exception as e:
        conn.rollback()
        return f"Terjadi kesalahan saat proses peminjaman: {e}"
    finally:
        if conn:
            conn.close()

def lihat_pinjaman_user(user_id):
    conn = connect_to_mysql()
    if conn is None: return []
    try:
        with conn.cursor() as cursor:
            query = """
                SELECT br.borrowal_id, b.title, br.borrow_date, br.due_date, br.status, br.return_date
                FROM borrowals br
                JOIN books b ON br.book_id = b.book_id
                WHERE br.user_id = %s
                ORDER BY br.borrow_date DESC
            """
            cursor.execute(query, (user_id,))
            pinjaman = cursor.fetchall()
        for p in pinjaman:
            if p['status'] == 'borrowed' and date.today() > p['due_date']:
                p['status_display'] = "JATUH TEMPO"
            elif p['return_date']:
                p['status_display'] = f"Returned (pada {p['return_date']})"
            else:
                p['status_display'] = p['status'].capitalize()
        return pinjaman
    except Exception as e:
        print(f"[ERROR-lihat_pinjaman_user]: {e}")
        return []
    finally:
        if conn:
            conn.close()

def kembalikan_buku(user_id, username, borrowal_id):
    conn = connect_to_mysql()
    if conn is None: return "Koneksi database gagal."
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT book_id, status FROM borrowals WHERE borrowal_id = %s", (borrowal_id,))
            result = cursor.fetchone()
            if not result:
                return "ID Peminjaman tidak ditemukan."
            if result['status'] == 'returned':
                return "Buku ini sudah pernah dikembalikan."
            
            book_id = result['book_id']
            cursor.execute("UPDATE borrowals SET status = 'returned', return_date = %s WHERE borrowal_id = %s", (date.today(), borrowal_id))
            cursor.execute("UPDATE books SET stock = stock + 1 WHERE book_id = %s", (book_id,))
        conn.commit()
        log_activity(user_id, username, "RETURN_BOOK", {"borrowal_id": borrowal_id, "book_id": book_id})
        return True
    except Exception as e:
        conn.rollback()
        return f"Terjadi kesalahan saat proses pengembalian: {e}"
    finally:
        if conn:
            conn.close()

def tambah_ke_wishlist(user_id, username, book_id):
    conn = connect_to_mysql()
    if conn is None: return "Koneksi database gagal."
    try:
        with conn.cursor() as cursor:
            query = "INSERT INTO wishlists (user_id, book_id) VALUES (%s, %s)"
            cursor.execute(query, (user_id, book_id))
        conn.commit()
        log_activity(user_id, username, "ADD_WISHLIST", {"book_id": book_id})
        return True
    except Exception as e:
        if "1062" in str(e):
            return "Buku ini sudah ada di dalam wishlist Anda."
        elif "1452" in str(e):
            return "Gagal menambahkan ke wishlist: User ID atau Book ID tidak ditemukan."
        else:
            return f"Gagal menambahkan ke wishlist: {e}"
    finally:
        if conn:
            conn.close()

def lihat_wishlist_user(user_id):
    conn = connect_to_mysql()
    if conn is None: return []
    try:
        with conn.cursor() as cursor:
            query = "SELECT w.wishlist_id, b.title, b.author, b.book_id FROM wishlists w JOIN books b ON w.book_id = b.book_id WHERE w.user_id = %s"
            cursor.execute(query, (user_id,))
            wishlist = cursor.fetchall()
        return wishlist
    except Exception as e:
        print(f"[ERROR-lihat_wishlist_user]: {e}")
        return []
    finally:
        if conn:
            conn.close()

def hapus_dari_wishlist(user_id, username, wishlist_id):
    conn = connect_to_mysql()
    if conn is None: return "Koneksi database gagal."
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM wishlists WHERE wishlist_id = %s AND user_id = %s", (wishlist_id, user_id))
            rowcount = cursor.rowcount
        conn.commit()
        if rowcount > 0:
            log_activity(user_id, username, "REMOVE_WISHLIST", {"wishlist_id": wishlist_id})
            return True
        else:
            return "ID Wishlist tidak ditemukan di wishlist Anda."
    except Exception as e:
        return f"Gagal menghapus dari wishlist: {e}"
    finally:
        if conn:
            conn.close()

def tambah_review(book_id, user_id, username, rating, komentar):
    db = connect_to_mongodb()
    if db is None: return "Koneksi ke MongoDB gagal."
    
    conn = connect_to_mysql()
    book_title = "Judul Tidak Ditemukan"
    if conn:
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT title FROM books WHERE book_id = %s", (book_id,))
                result = cursor.fetchone()
                if result:
                    book_title = result['title']
        finally:
            if conn:
                conn.close()
    
    review_document = {
        "book_id": book_id, "user_id": user_id, "username": username,
        "book_title": book_title, "rating": rating, "komentar": komentar,
        "tanggal_review": date.today().isoformat()
    }
    try:
        db['reviews'].insert_one(review_document)
        log_activity(user_id, username, "ADD_REVIEW", {"book_id": book_id, "rating": rating})
        return True
    except Exception as e:
        return f"Gagal menyimpan review: {e}"

def lihat_review_buku(book_id):
    db = connect_to_mongodb()
    if db is None: return []
    reviews = list(db['reviews'].find({"book_id": book_id}).sort("tanggal_review", -1))
    return reviews

def log_activity(user_id, username, activity_type, details={}):
    db = connect_to_mongodb()
    if db is None: return
    try:
        log_document = {
            "user_id": user_id, "username": username, "activity_type": activity_type,
            "details": details, "timestamp": datetime.now().isoformat()
        }
        db['activity_logs'].insert_one(log_document)
    except Exception as e:
        print(f"\n[SYSTEM-LOG-ERROR] Gagal mencatat aktivitas: {e}")

def lihat_log_aktivitas(limit=25):
    db = connect_to_mongodb()
    if db is None: return []
    logs = list(db['activity_logs'].find().sort("timestamp", -1).limit(limit))
    return logs

def _get_book_details(book_ids):
    if not book_ids: return {}
    conn = connect_to_mysql()
    if conn is None: return {}
    try:
        with conn.cursor() as cursor:
            format_strings = ','.join(['%s'] * len(book_ids))
            query = f"SELECT book_id, title FROM books WHERE book_id IN ({format_strings})"
            cursor.execute(query, tuple(book_ids))
            books = cursor.fetchall()
        return {book['book_id']: book['title'] for book in books}
    except Exception as e:
        print(f"[ERROR-_get_book_details]: {e}")
        return {}
    finally:
        if conn:
            conn.close()

def update_book_trends():
    db_mongo = connect_to_mongodb()
    conn_sql = connect_to_mysql()
    if conn_sql is None or db_mongo is None: return "Koneksi database gagal."
    try:
        with conn_sql.cursor() as cursor:
            start_date = date.today() - timedelta(days=7)
            query = "SELECT book_id, COUNT(book_id) as jumlah_pinjam FROM borrowals WHERE borrow_date >= %s GROUP BY book_id ORDER BY jumlah_pinjam DESC LIMIT 5"
            cursor.execute(query, (start_date,))
            top_books_raw = cursor.fetchall()
        
        if not top_books_raw:
            return "Tidak ada data peminjaman dalam 7 hari terakhir."
        
        book_ids = [item['book_id'] for item in top_books_raw]
        book_details = _get_book_details(book_ids)
        
        trends_data = []
        for item in top_books_raw:
            book_id = item['book_id']
            trends_data.append({
                "book_id": book_id,
                "title": book_details.get(book_id, "Judul Tidak Ditemukan"),
                "total_loans_last_7_days": item['jumlah_pinjam'],
                "last_updated": date.today().isoformat()
            })
            
        if trends_data:
            db_mongo['book_trends'].delete_many({})
            db_mongo['book_trends'].insert_many(trends_data)
        return True
    except Exception as e:
        return f"Gagal memperbarui tren buku: {e}"
    finally:
        if conn_sql:
            conn_sql.close()

def get_book_trends():
    db = connect_to_mongodb()
    if db is None: return []
    trends = list(db['book_trends'].find().sort("total_loans_last_7_days", -1))
    return trends

def update_user_preference_profile(user_id, username):
    conn = connect_to_mysql()
    if conn is None: return "Koneksi database gagal."
    try:
        with conn.cursor() as cursor:
            query = """
                SELECT c.category_name, b.author
                FROM borrowals br
                JOIN books b ON br.book_id = b.book_id
                JOIN categories c ON b.category_id = c.category_id
                WHERE br.user_id = %s
            """
            cursor.execute(query, (user_id,))
            history = cursor.fetchall()
        
        if not history:
            return True

        total_borrowed = len(history)
        category_counts = Counter(item['category_name'] for item in history)
        author_counts = Counter(item['author'] for item in history)
        favorite_category = category_counts.most_common(1)[0] if category_counts else ("-", 0)
        favorite_author = author_counts.most_common(1)[0] if author_counts else ("-", 0)
        
        db_mongo = connect_to_mongodb()
        if db_mongo is None: return "Koneksi MongoDB gagal."

        profile_document = {
            "user_id": user_id, "username": username,
            "total_books_borrowed": total_borrowed,
            "favorite_category": {"name": favorite_category[0], "count": favorite_category[1]},
            "favorite_author": {"name": favorite_author[0], "count": favorite_author[1]},
            "last_updated": datetime.now().isoformat()
        }
        db_mongo['user_preferences'].update_one({'user_id': user_id}, {'$set': profile_document}, upsert=True)
        return True
    except Exception as e:
        return f"Gagal membuat profil preferensi: {e}"
    finally:
        if conn:
            conn.close()

def get_user_preference(user_id):
    db = connect_to_mongodb()
    if db is None: return None
    return db['user_preferences'].find_one({'user_id': user_id})

def dapatkan_kategori_wishlist(user_id):
    conn = connect_to_mysql()
    if conn is None: return []
    try:
        with conn.cursor() as cursor:
            query = "SELECT DISTINCT b.category_id, c.category_name FROM wishlists w JOIN books b ON w.book_id = b.book_id JOIN categories c ON b.category_id = c.category_id WHERE w.user_id = %s"
            cursor.execute(query, (user_id,))
            kategori = cursor.fetchall()
        return kategori
    except Exception as e:
        print(f"[ERROR-dapatkan_kategori_wishlist]: {e}")
        return []
    finally:
        if conn:
            conn.close()

def dapatkan_buku_per_kategori_limit(category_id, limit=3):
    conn = connect_to_mysql()
    if conn is None: return []
    try:
        with conn.cursor() as cursor:
            query = "SELECT book_id, title FROM books WHERE category_id = %s ORDER BY RAND() LIMIT %s"
            cursor.execute(query, (category_id, limit))
            buku = cursor.fetchall()
        return buku
    except Exception as e:
        print(f"[ERROR-dapatkan_buku_per_kategori_limit]: {e}")
        return []
    finally:
        if conn:
            conn.close()

def dapatkan_rekomendasi_buku(user_id):
    kategori_favorit = dapatkan_kategori_wishlist(user_id)
    if not kategori_favorit: return {}
    rekomendasi = {}
    for kat in kategori_favorit:
        rekomendasi_buku = dapatkan_buku_per_kategori_limit(kat['category_id'], 3)
        rekomendasi[kat['category_name']] = rekomendasi_buku
    return rekomendasi

def admin_login(username, password):
    if username == "admin" and password == "admin123":
        return {"username": username, "role": "admin"}
    else:
        return None

def get_dashboard_stats():
    conn = connect_to_mysql()
    stats = {'total_books': 0, 'total_users': 0, 'books_borrowed': 0, 'total_categories': 0}
    if conn is None: return stats
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM books")
            stats['total_books'] = cursor.fetchone()['COUNT(*)']
            cursor.execute("SELECT COUNT(*) FROM users")
            stats['total_users'] = cursor.fetchone()['COUNT(*)']
            cursor.execute("SELECT COUNT(*) FROM borrowals WHERE status = 'borrowed'")
            stats['books_borrowed'] = cursor.fetchone()['COUNT(*)']
            cursor.execute("SELECT COUNT(*) FROM categories")
            stats['total_categories'] = cursor.fetchone()['COUNT(*)']
        return stats
    except Exception as e:
        print(f"Error getting dashboard stats: {e}")
        return stats
    finally:
        if conn:
            conn.close()

def tambah_kategori(category_name):
    conn = connect_to_mysql()
    if conn is None: return "Koneksi database gagal."
    try:
        with conn.cursor() as cursor:
            cursor.execute("INSERT INTO categories (category_name) VALUES (%s)", (category_name,))
        conn.commit()
        return True
    except Exception as e:
        if "1062" in str(e):
            return "Nama kategori sudah ada."
        return f"Gagal menambahkan kategori: {e}"
    finally:
        if conn:
            conn.close()

def get_category_by_id(category_id):
    conn = connect_to_mysql()
    if conn is None: return None
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM categories WHERE category_id = %s", (category_id,))
            category = cursor.fetchone()
        return category
    except Exception as e:
        print(f"[ERROR-get_category_by_id]: {e}")
        return None
    finally:
        if conn:
            conn.close()

def update_kategori(category_id, category_name):
    conn = connect_to_mysql()
    if conn is None: return "Koneksi database gagal."
    try:
        with conn.cursor() as cursor:
            cursor.execute("UPDATE categories SET category_name = %s WHERE category_id = %s", (category_name, category_id))
        conn.commit()
        return True
    except Exception as e:
        return f"Gagal memperbarui kategori: {e}"
    finally:
        if conn:
            conn.close()

def hapus_kategori(category_id):
    conn = connect_to_mysql()
    if conn is None: return "Koneksi database gagal."
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM books WHERE category_id = %s", (category_id,))
            book_count = cursor.fetchone()['COUNT(*)']
            if book_count > 0:
                return f"Gagal menghapus: Masih ada {book_count} buku dalam kategori ini."
            cursor.execute("DELETE FROM categories WHERE category_id = %s", (category_id,))
        conn.commit()
        return True
    except Exception as e:
        return f"Gagal menghapus kategori: {e}"
    finally:
        if conn:
            conn.close()

def lihat_semua_peminjaman(limit=50):
    conn = connect_to_mysql()
    if conn is None: return []
    try:
        with conn.cursor() as cursor:
            query = """
                SELECT br.borrowal_id, b.title, u.full_name, br.borrow_date, br.due_date, br.status, br.return_date
                FROM borrowals br
                JOIN books b ON br.book_id = b.book_id
                JOIN users u ON br.user_id = u.user_id
                ORDER BY br.borrow_date DESC
                LIMIT %s
            """
            cursor.execute(query, (limit,))
            borrowals = cursor.fetchall()
        return borrowals
    except Exception as e:
        print(f"[ERROR-lihat_semua_peminjaman]: {e}")
        return []
    finally:
        if conn:
            conn.close()
            
def get_books_by_category(category_id):
    conn = connect_to_mysql()
    if conn is None: return []
    try:
        with conn.cursor() as cursor:
            query = """
                SELECT b.*, c.category_name 
                FROM books b 
                JOIN categories c ON b.category_id = c.category_id 
                WHERE b.category_id = %s
            """
            cursor.execute(query, (category_id,))
            books = cursor.fetchall()
        return books
    except Exception as e:
        print(f"[ERROR-get_books_by_category]: {e}")
        return []
    finally:
        if conn:
            conn.close()
