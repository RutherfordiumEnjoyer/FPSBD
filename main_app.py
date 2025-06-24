from collections import Counter
from database_connector import connect_to_mysql, connect_to_mongodb
from datetime import date, timedelta, datetime
from werkzeug.security import generate_password_hash, check_password_hash
import pymysql

def tambah_buku(title, author, publication_year, stock, category_id):
    conn = connect_to_mysql()
    if conn is None:
        return "Koneksi database gagal."
    try:
        cursor = conn.cursor()
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
        if conn.is_connected():
            cursor.close()
            conn.close()

def lihat_semua_buku():
    conn = connect_to_mysql()
    if conn is None: 
        return []
    try:
        cursor = conn.cursor(dictionary=True)
        query = "SELECT b.*, c.category_name FROM books b LEFT JOIN categories c ON b.category_id = c.category_id ORDER BY b.book_id"
        cursor.execute(query)
        books = cursor.fetchall()
        return books
    except Exception as e:
        print(f"[ERROR-lihat_semua_buku]: {e}")
        return []
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

def hapus_buku(book_id):
    conn = connect_to_mysql()
    if conn is None:
        return "Koneksi database gagal."
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM borrowals WHERE book_id = %s AND status = 'borrowed'", (book_id,))
        if cursor.fetchone()[0] > 0:
            return "Buku tidak dapat dihapus karena masih ada yang meminjam."

        cursor.execute("DELETE FROM books WHERE book_id = %s", (book_id,))
        conn.commit()
        if cursor.rowcount > 0:
            return True
        else:
            return "Buku dengan ID tersebut tidak ditemukan."
    except Exception as e:
        return f"Gagal menghapus buku: {e}"
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def get_book_by_id(book_id):
    conn = connect_to_mysql()
    if conn is None:
        return None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM books WHERE book_id = %s", (book_id,))
        book = cursor.fetchone()
        return book
    except Exception as e:
        print(f"[ERROR-get_book_by_id]: {e}")
        return None
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

def update_buku(book_id, title, author, publication_year, stock, category_id):
    conn = connect_to_mysql()
    if conn is None:
        return "Koneksi database gagal."
    try:
        cursor = conn.cursor()
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
        if conn.is_connected():
            cursor.close()
            conn.close()

def lihat_semua_kategori():
    conn = connect_to_mysql()
    if conn is None:
        return []
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM categories ORDER BY category_id")
        categories = cursor.fetchall()
        return categories
    except Exception as e:
        print(f"[ERROR-lihat_semua_kategori]: {e}")
        return []
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def pinjam_buku(user_id, username, book_id):
    conn = connect_to_mysql()
    if conn is None:
        return "Koneksi database gagal."
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT stock FROM books WHERE book_id = %s", (book_id,))
        result = cursor.fetchone()
        if result is None or result[0] <= 0:
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
        if conn.is_connected():
            cursor.close()
            conn.close()

def lihat_pinjaman_user(user_id):
    conn = connect_to_mysql()
    if conn is None:
        return []
    try:
        cursor = conn.cursor(dictionary=True)
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
        if conn.is_connected():
            cursor.close()
            conn.close()

def kembalikan_buku(user_id, username, borrowal_id):
    conn = connect_to_mysql()
    if conn is None:
        return "Koneksi database gagal."
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT book_id, status FROM borrowals WHERE borrowal_id = %s", (borrowal_id,))
        result = cursor.fetchone()
        if not result:
            return "ID Peminjaman tidak ditemukan."
        if result[1] == 'returned':
            return "Buku ini sudah pernah dikembalikan."
        
        book_id = result[0]
        cursor.execute("UPDATE borrowals SET status = 'returned', return_date = %s WHERE borrowal_id = %s", (date.today(), borrowal_id))
        cursor.execute("UPDATE books SET stock = stock + 1 WHERE book_id = %s", (book_id,))
        conn.commit()
        log_activity(user_id, username, "RETURN_BOOK", {"borrowal_id": borrowal_id, "book_id": book_id})
        return True
    except Exception as e:
        conn.rollback()
        return f"Terjadi kesalahan saat proses pengembalian: {e}"
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def tambah_ke_wishlist(user_id, username, book_id):
    conn = connect_to_mysql()
    if conn is None:
        return "Koneksi database gagal."
    try:
        cursor = conn.cursor()
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
        if conn.is_connected():
            cursor.close()
            conn.close()

def lihat_wishlist_user(user_id):
    conn = connect_to_mysql()
    if conn is None:
        return []
    try:
        cursor = conn.cursor(dictionary=True)
        query = "SELECT w.wishlist_id, b.title, b.author, b.book_id FROM wishlists w JOIN books b ON w.book_id = b.book_id WHERE w.user_id = %s"
        cursor.execute(query, (user_id,))
        wishlist = cursor.fetchall()
        return wishlist
    except Exception as e:
        print(f"[ERROR-lihat_wishlist_user]: {e}")
        return []
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def hapus_dari_wishlist(user_id, username, wishlist_id):
    conn = connect_to_mysql()
    if conn is None:
        return "Koneksi database gagal."
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM wishlists WHERE wishlist_id = %s AND user_id = %s", (wishlist_id, user_id))
        conn.commit()
        if cursor.rowcount > 0:
            log_activity(user_id, username, "REMOVE_WISHLIST", {"wishlist_id": wishlist_id})
            return True
        else:
            return "ID Wishlist tidak ditemukan di wishlist Anda."
    except Exception as e:
        return f"Gagal menghapus dari wishlist: {e}"
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def tambah_review(book_id, user_id, username, rating, komentar):
    db = connect_to_mongodb()
    if db is None:
        return "Koneksi ke MongoDB gagal."
    
    conn = connect_to_mysql()
    book_title = "Judul Tidak Ditemukan"
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT title FROM books WHERE book_id = %s", (book_id,))
            result = cursor.fetchone()
            if result:
                book_title = result[0]
        finally:
            if conn.is_connected():
                cursor.close()
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
    if db is None:
        return []
    reviews = list(db['reviews'].find({"book_id": book_id}).sort("tanggal_review", -1))
    return reviews

def log_activity(user_id, username, activity_type, details={}):
    db = connect_to_mongodb()
    if db is None: return
    logs_collection = db['activity_logs']
    log_document = {
        "user_id": user_id, "username": username, "activity_type": activity_type,
        "details": details, "timestamp": datetime.now().isoformat()
    }
    try:
        logs_collection.insert_one(log_document)
    except Exception as e:
        print(f"\n[SYSTEM-LOG-ERROR] Gagal mencatat aktivitas: {e}")

def lihat_log_aktivitas(limit=25):
    db = connect_to_mongodb()
    if db is None:
        return []
    logs = list(db['activity_logs'].find().sort("timestamp", -1).limit(limit))
    return logs

def _get_book_details(book_ids):
    if not book_ids: return {}
    conn = connect_to_mysql()
    if conn is None: return {}
    try:
        cursor = conn.cursor(dictionary=True)
        format_strings = ','.join(['%s'] * len(book_ids))
        query = f"SELECT book_id, title FROM books WHERE book_id IN ({format_strings})"
        cursor.execute(query, tuple(book_ids))
        books = cursor.fetchall()
        return {book['book_id']: book['title'] for book in books}
    except Exception as e:
        print(f"[ERROR-_get_book_details]: {e}")
        return {}
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def update_book_trends():
    conn_sql = connect_to_mysql()
    db_mongo = connect_to_mongodb()
    if conn_sql is None or db_mongo is None:
        return "Koneksi database gagal."
    try:
        cursor = conn_sql.cursor(dictionary=True)
        start_date = date.today() - timedelta(days=7)
        query = "SELECT book_id, COUNT(book_id) as jumlah_pinjam FROM borrowals WHERE borrow_date >= %s GROUP BY book_id ORDER BY jumlah_pinjam DESC LIMIT 5"
        cursor.execute(query, (start_date,))
        top_books_raw = cursor.fetchall()
        
        trends_collection = db_mongo['book_trends']
        trends_collection.delete_many({})
        
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
            trends_collection.insert_many(trends_data)
        return True
    except Exception as e:
        return f"Gagal memperbarui tren buku: {e}"
    finally:
        if conn_sql.is_connected():
            cursor.close()
            conn_sql.close()

def get_book_trends():
    db_mongo = connect_to_mongodb()
    if db_mongo is None:
        return []
    trends = list(db_mongo['book_trends'].find().sort("total_loans_last_7_days", -1))
    return trends

def update_user_preference_profile(user_id, username):
    conn_sql = connect_to_mysql()
    db_mongo = connect_to_mongodb()
    if conn_sql is None or db_mongo is None:
        return "Koneksi database gagal."

    try:
        cursor = conn_sql.cursor(dictionary=True)
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
            return "User belum memiliki riwayat peminjaman untuk dianalisis."

        total_borrowed = len(history)
        category_counts = Counter(item['category_name'] for item in history)
        author_counts = Counter(item['author'] for item in history)
        favorite_category = category_counts.most_common(1)[0] if category_counts else ("-", 0)
        favorite_author = author_counts.most_common(1)[0] if author_counts else ("-", 0)
        
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
        if conn_sql.is_connected():
            cursor.close()
            conn_sql.close()

def get_user_preference(user_id):
    db_mongo = connect_to_mongodb()
    if db_mongo is None:
        return None
    return db_mongo['user_preferences'].find_one({'user_id': user_id})

def update_book_and_log_changes(book_id, new_title, new_author, new_stock_str, admin_username="Admin"):
    conn_sql = connect_to_mysql()
    db_mongo = connect_to_mongodb()
    if conn_sql is None or db_mongo is None:
        return "Koneksi database gagal."

    try:
        cursor = conn_sql.cursor(dictionary=True)
        cursor.execute("SELECT * FROM books WHERE book_id = %s", (book_id,))
        old_data = cursor.fetchone()
        if not old_data:
            return f"Buku dengan ID {book_id} tidak ditemukan."

        update_fields = {}
        changes_to_log = []

        if new_title and new_title != old_data['title']:
            update_fields['title'] = new_title
            changes_to_log.append({"field": "title", "from": old_data['title'], "to": new_title})
        if new_author and new_author != old_data['author']:
            update_fields['author'] = new_author
            changes_to_log.append({"field": "author", "from": old_data['author'], "to": new_author})
        if new_stock_str and int(new_stock_str) != old_data['stock']:
            new_stock = int(new_stock_str)
            update_fields['stock'] = new_stock
            changes_to_log.append({"field": "stock", "from": old_data['stock'], "to": new_stock})
        
        if not update_fields:
            return "Tidak ada perubahan data yang dimasukkan."

        set_clause = ", ".join([f"{key} = %s" for key in update_fields.keys()])
        query_update = f"UPDATE books SET {set_clause} WHERE book_id = %s"
        values = list(update_fields.values()) + [book_id]
        cursor.execute(query_update, tuple(values))
        conn_sql.commit()

        history_collection = db_mongo['book_change_history']
        log_entry = {
            "changed_by": admin_username,
            "timestamp": datetime.now().isoformat(),
            "changes": changes_to_log
        }
        history_collection.update_one(
            {'book_id': book_id},
            {
                '$push': {'change_logs': log_entry},
                '$set': {'title': update_fields.get('title', old_data['title'])}
            },
            upsert=True
        )
        return True
    except ValueError:
        return "Input stok harus berupa angka."
    except Exception as e:
        conn_sql.rollback()
        return f"Terjadi kesalahan saat update: {e}"
    finally:
        if conn_sql.is_connected():
            cursor.close()
            conn_sql.close()

def lihat_perubahan_buku(book_id):
    db_mongo = connect_to_mongodb()
    if db_mongo is None:
        return None
    return db_mongo['book_change_history'].find_one({'book_id': book_id})

def dapatkan_kategori_wishlist(user_id):
    conn = connect_to_mysql()
    if conn is None:
        return []
    try:
        cursor = conn.cursor(dictionary=True)
        query = "SELECT DISTINCT b.category_id, c.category_name FROM wishlists w JOIN books b ON w.book_id = b.book_id JOIN categories c ON b.category_id = c.category_id WHERE w.user_id = %s"
        cursor.execute(query, (user_id,))
        kategori = cursor.fetchall()
        return kategori
    except Exception as e:
        print(f"[ERROR-dapatkan_kategori_wishlist]: {e}")
        return []
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def dapatkan_buku_per_kategori_limit(category_id, limit=3):
    conn = connect_to_mysql()
    if conn is None:
        return []
    try:
        cursor = conn.cursor(dictionary=True)
        query = "SELECT book_id, title FROM books WHERE category_id = %s ORDER BY RAND() LIMIT %s"
        cursor.execute(query, (category_id, limit))
        buku = cursor.fetchall()
        return buku
    except Exception as e:
        print(f"[ERROR-dapatkan_buku_per_kategori_limit]: {e}")
        return []
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def dapatkan_rekomendasi_buku(user_id):
    kategori_favorit = dapatkan_kategori_wishlist(user_id)
    if not kategori_favorit:
        return {}
    
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

def user_login(email, password):
    conn = connect_to_mysql()
    if conn is None:
        return None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT user_id, full_name, password_hash FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        
        # Cek jika user ada DAN hash passwordnya cocok
        if user and check_password_hash(user['password_hash'], password):
            return user
        else:
            return None
    except Exception as e:
        print(f"[ERROR-user_login]: {e}")
        return None
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def register_user(full_name, email, password):
    conn = None  # Definisikan di luar try agar bisa diakses di finally
    try:
        conn = connect_to_mysql()
        # Jika koneksi gagal, conn akan menjadi None. Kita harus cek di sini.
        if conn is None:
            # Mengembalikan pesan error yang jelas jika koneksi gagal dari awal
            return "Koneksi database gagal. Periksa kembali Environment Variables atau status database cloud."

        cursor = conn.cursor()
        
        hashed_password = generate_password_hash(password)
        
        query = "INSERT INTO users (full_name, email, password_hash) VALUES (%s, %s, %s)"
        values = (full_name, email, hashed_password)
        
        cursor.execute(query, values)
        conn.commit()
        return True
    
    except pymysql.MySQLError as e:
        # Menangkap error spesifik dari database (misal: duplicate email)
        error_message = f"Database Error: {e}"
        print(error_message) # Cetak ke log Vercel
        
        # Memberi pesan yang lebih ramah ke pengguna
        if "1062" in str(e):
             return "Email ini sudah terdaftar. Silakan gunakan email lain."
        return "Terjadi kesalahan pada database."

    except Exception as e:
        # Menangkap error tak terduga lainnya
        return f"An unexpected error occurred: {e}"
        
    finally:
        # Memastikan koneksi selalu ditutup
        if conn and conn.is_connected():
            conn.close()

def lihat_semua_review(limit=20):
    """
    Mengambil semua review dari MongoDB dan memperkayanya dengan data nama
    pengguna dan judul buku yang akurat dari MySQL.
    """
    db = connect_to_mongodb()
    if db is None:
        return []

    # Langkah 1: Ambil data nama yang akurat dari MySQL
    user_names = get_all_users_dict()
    book_titles = get_all_book_titles_dict()

    # Langkah 2: Ambil semua data ulasan dari MongoDB
    all_reviews = list(db['reviews'].find().sort("tanggal_review", -1).limit(limit))

    # Langkah 3: Perkaya setiap ulasan dengan data yang benar
    for review in all_reviews:
        # Perbaiki nama pengguna
        correct_user_name = user_names.get(review.get('user_id'))
        if correct_user_name:
            review['username'] = correct_user_name
        else:
            review['username'] = review.get('username', 'Pengguna Tidak Ditemukan')

        # Perbaiki judul buku
        correct_book_title = book_titles.get(review.get('book_id'))
        if correct_book_title:
            review['book_title'] = correct_book_title
        else:
            review['book_title'] = review.get('book_title', 'Buku Tidak Ditemukan')

    return all_reviews

def get_dashboard_stats():
    """
    Mengambil data statistik utama untuk ditampilkan di dasbor admin.
    NOTE: Ini masih menggunakan data dummy. Nanti bisa diganti dengan query SQL.
    """
    conn = connect_to_mysql()
    stats = {
        'total_books': 0,
        'total_users': 0,
        'books_borrowed': 0,
        'total_categories': 0
    }
    if conn is None:
        return stats # Mengembalikan nilai default jika koneksi gagal

    try:
        cursor = conn.cursor()
        
        # Query untuk total buku
        cursor.execute("SELECT COUNT(*) FROM books")
        stats['total_books'] = cursor.fetchone()[0]
        
        # Query untuk total pengguna
        cursor.execute("SELECT COUNT(*) FROM users")
        stats['total_users'] = cursor.fetchone()[0]
        
        # Query untuk buku yang sedang dipinjam
        cursor.execute("SELECT COUNT(*) FROM borrowals WHERE status = 'borrowed'")
        stats['books_borrowed'] = cursor.fetchone()[0]

        # Query untuk total kategori
        cursor.execute("SELECT COUNT(*) FROM categories")
        stats['total_categories'] = cursor.fetchone()[0]
        
        return stats
    except Exception as e:
        print(f"Error getting dashboard stats: {e}")
        return stats # Mengembalikan nilai default jika ada error
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def tambah_kategori(category_name):
    """Menambahkan kategori baru ke database."""
    conn = connect_to_mysql()
    if conn is None: return "Koneksi database gagal."
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO categories (category_name) VALUES (%s)", (category_name,))
        conn.commit()
        return True
    except Exception as e:
        if "1062" in str(e): # Error untuk duplicate entry
            return "Nama kategori sudah ada."
        return f"Gagal menambahkan kategori: {e}"
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def get_category_by_id(category_id):
    """Mengambil satu data kategori berdasarkan ID-nya."""
    conn = connect_to_mysql()
    if conn is None: return None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM categories WHERE category_id = %s", (category_id,))
        return cursor.fetchone()
    except Exception as e:
        print(f"[ERROR-get_category_by_id]: {e}")
        return None
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def update_kategori(category_id, category_name):
    """Memperbarui nama kategori yang ada."""
    conn = connect_to_mysql()
    if conn is None: return "Koneksi database gagal."
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE categories SET category_name = %s WHERE category_id = %s", (category_name, category_id))
        conn.commit()
        return True
    except Exception as e:
        return f"Gagal memperbarui kategori: {e}"
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def hapus_kategori(category_id):
    """Menghapus kategori jika tidak ada buku yang terkait."""
    conn = connect_to_mysql()
    if conn is None: return "Koneksi database gagal."
    try:
        cursor = conn.cursor()
        # PENTING: Cek dulu apakah ada buku dalam kategori ini
        cursor.execute("SELECT COUNT(*) FROM books WHERE category_id = %s", (category_id,))
        book_count = cursor.fetchone()[0]
        
        if book_count > 0:
            return f"Gagal menghapus: Masih ada {book_count} buku dalam kategori ini."
        
        # Jika tidak ada buku, baru hapus kategori
        cursor.execute("DELETE FROM categories WHERE category_id = %s", (category_id,))
        conn.commit()
        return True
    except Exception as e:
        return f"Gagal menghapus kategori: {e}"
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def lihat_semua_peminjaman(limit=50):
    """Mengambil semua data peminjaman dari semua user, diurutkan dari yang terbaru."""
    conn = connect_to_mysql()
    if conn is None:
        return []
    try:
        cursor = conn.cursor(dictionary=True)
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
        if conn.is_connected():
            cursor.close()
            conn.close()

def get_all_user_profiles():
    """
    Mengambil semua data profil dari MongoDB dan memperkayanya dengan nama pengguna yang benar dari MySQL.
    """
    db_mongo = connect_to_mongodb()
    if db_mongo is None:
        return []

    # Langkah 1: Ambil semua nama pengguna yang benar dari MySQL
    user_names_map = get_all_users_dict()
    
    # Langkah 2: Ambil semua data profil dari MongoDB
    profiles = list(db_mongo['user_preferences'].find().sort("total_books_borrowed", -1))

    # Langkah 3: Perkaya data profil dengan nama yang benar
    for profile in profiles:
        # Dapatkan nama yang benar dari map menggunakan user_id
        correct_name = user_names_map.get(profile['user_id'])
        
        # Jika nama yang benar ditemukan, gunakan itu. Jika tidak, gunakan nama yang ada di profil.
        if correct_name:
            profile['username'] = correct_name
        else:
            # Fallback jika user_id tidak ditemukan di MySQL (seharusnya tidak terjadi)
            profile['username'] = profile.get('username', 'Nama Tidak Ditemukan')
            
    return profiles

def get_all_users_dict():
    """Mengambil semua user dari MySQL dan menyusunnya dalam format kamus {user_id: full_name}."""
    conn = connect_to_mysql()
    if conn is None: return {}
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT user_id, full_name FROM users")
        users = cursor.fetchall()
        # Mengubah daftar pengguna menjadi kamus untuk pencarian cepat
        return {user['user_id']: user['full_name'] for user in users}
    except Exception as e:
        print(f"[ERROR-get_all_users_dict]: {e}")
        return {}
    finally:
        if conn.is_connected():
            conn.close()

# main_app.py

def get_books_by_category(category_id):
    """Mengambil semua buku yang termasuk dalam satu kategori tertentu."""
    conn = connect_to_mysql()
    if conn is None: return []
    try:
        cursor = conn.cursor(dictionary=True)
        # Mengambil data buku dan juga nama kategorinya melalui JOIN
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
        if conn.is_connected():
            cursor.close()
            conn.close()

def get_all_book_titles_dict():
    """Mengambil semua buku dari MySQL dan menyusunnya dalam format kamus {book_id: title}."""
    conn = connect_to_mysql()
    if conn is None: return {}
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT book_id, title FROM books")
        books = cursor.fetchall()
        return {book['book_id']: book['title'] for book in books}
    except Exception as e:
        print(f"[ERROR-get_all_book_titles_dict]: {e}")
        return {}
    finally:
        if conn.is_connected():
            conn.close()
