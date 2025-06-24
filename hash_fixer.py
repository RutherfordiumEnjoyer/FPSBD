# hash_fixer.py

from werkzeug.security import generate_password_hash
import mysql.connector

# --- Konfigurasi Database (Pastikan ini sesuai dengan setup Anda) ---
DB_CONFIG = {
    'host': "localhost",
    'user': "root",
    'password': "",
    'database': "fp_kelompok6"
}

def fix_plaintext_passwords():
    """
    Skrip ini akan memindai tabel 'users', mencari password yang belum di-hash,
    dan mengubahnya menjadi hash yang aman.
    """
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        # Ambil semua user dari database
        cursor.execute("SELECT user_id, password_hash FROM users")
        users = cursor.fetchall()
        
        print("Memindai password pengguna...")
        passwords_fixed = 0

        for user in users:
            password = user['password_hash']
            user_id = user['user_id']
            
            # Cek sederhana: jika password tidak mengandung '$', kemungkinan besar itu teks biasa
            if password and '$' not in password:
                print(f"  -> Menemukan password teks biasa untuk user ID {user_id}: '{password}'. Proses hashing...")
                
                # Hash password tersebut
                hashed_password = generate_password_hash(password)
                
                # Update database dengan hash yang baru
                update_cursor = conn.cursor()
                update_cursor.execute(
                    "UPDATE users SET password_hash = %s WHERE user_id = %s",
                    (hashed_password, user_id)
                )
                print(f"  -> SUKSES: Password untuk user ID {user_id} telah di-hash dengan aman.")
                passwords_fixed += 1
        
        if passwords_fixed > 0:
            conn.commit()
            print(f"\nSelesai! {passwords_fixed} password pengguna telah diperbarui.")
        else:
            print("\nSemua password sudah dalam format hash yang aman. Tidak ada yang perlu diubah.")

    except mysql.connector.Error as e:
        print(f"\nError database: {e}")
        conn.rollback()
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == '__main__':
    print("--- Utilitas Perbaikan Password ---")
    fix_plaintext_passwords()