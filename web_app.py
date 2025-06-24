from flask import Flask, render_template, request, redirect, url_for, flash, session
from functools import wraps
from main_app import (
    # Fungsi Buku & Kategori
    lihat_semua_buku, tambah_buku, hapus_buku, get_book_by_id, update_buku,
    lihat_semua_kategori, tambah_kategori, get_category_by_id, update_kategori, hapus_kategori,
    get_books_by_category,
    
    # Fungsi User & Peminjaman
    user_login, admin_login, register_user,
    lihat_pinjaman_user, kembalikan_buku, pinjam_buku, lihat_semua_peminjaman,
    
    # Fungsi Fitur Tambahan
    tambah_ke_wishlist, lihat_wishlist_user, hapus_dari_wishlist,
    update_book_trends, get_book_trends,
    tambah_review, lihat_review_buku, lihat_semua_review,
    dapatkan_rekomendasi_buku,
    
    # Fungsi Analitik & Log
    update_user_preference_profile, get_user_preference, get_all_user_profiles,
    lihat_log_aktivitas, get_dashboard_stats
)

app = Flask(__name__)
app.secret_key = 'ini_adalah_kunci_rahasia_acak_milik_anda'

# == Decorators ==
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'admin':
            flash('Anda harus login sebagai admin untuk mengakses halaman ini.', 'danger')
            return redirect(url_for('admin_login_proses'))
        return f(*args, **kwargs)
    return decorated_function

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Anda harus login untuk mengakses halaman ini.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# == Rute Utama ==
@app.route('/')
def index():
    if 'user_id' in session:
        if session.get('role') == 'user':
            return redirect(url_for('dashboard'))
        elif session.get('role') == 'admin':
            return redirect(url_for('admin_dashboard'))
    return render_template('landing.html')

# == Rute Admin ===============================================
@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    dashboard_stats = get_dashboard_stats()
    return render_template('admin_dashboard.html', stats=dashboard_stats)

# -- Manajemen Buku --
@app.route('/admin/books')
@admin_required
def admin_book_list():
    daftar_buku = lihat_semua_buku()
    return render_template('index.html', books=daftar_buku)

@app.route('/tambah', methods=['GET', 'POST'])
@admin_required
def halaman_tambah_buku():
    if request.method == 'POST':
        hasil = tambah_buku(request.form['title'], request.form['author'], request.form['publication_year'], request.form['stock'], request.form['category_id'])
        if hasil is True:
            flash(f"Buku '{request.form['title']}' berhasil ditambahkan!", "success")
        else:
            flash(f"Gagal menambahkan buku. Error: {hasil}", "danger")
        return redirect(url_for('admin_book_list'))
    semua_kategori = lihat_semua_kategori() 
    return render_template('tambah_buku.html', categories=semua_kategori)

@app.route('/edit/<int:book_id>', methods=['GET', 'POST'])
@admin_required
def halaman_edit_buku(book_id):
    if request.method == 'POST':
        hasil = update_buku(book_id, request.form['title'], request.form['author'], request.form['publication_year'], request.form['stock'], request.form['category_id'])
        if hasil is True:
            flash(f"Buku '{request.form['title']}' berhasil diperbarui!", "success")
        else:
            flash(f"Gagal memperbarui buku. Error: {hasil}", "danger")
        return redirect(url_for('admin_book_list'))
    
    buku = get_book_by_id(book_id)
    semua_kategori = lihat_semua_kategori()
    if buku:
        return render_template('edit_buku.html', book=buku, categories=semua_kategori)
    else:
        flash("Buku tidak ditemukan.", "danger")
        return redirect(url_for('admin_book_list'))

@app.route('/hapus/<int:book_id>', methods=['POST'])
@admin_required
def hapus_buku_proses(book_id):
    hasil = hapus_buku(book_id)
    if hasil is True:
        flash("Buku berhasil dihapus.", "success")
    else:
        flash(f"Gagal menghapus buku. Pesan: {hasil}", "danger")
    return redirect(url_for('admin_book_list'))

# -- Manajemen Kategori --
@app.route('/admin/categories')
@admin_required
def admin_category_list():
    categories = lihat_semua_kategori()
    return render_template('admin_kategori_list.html', categories=categories)

@app.route('/admin/categories/add', methods=['GET', 'POST'])
@admin_required
def admin_add_category():
    if request.method == 'POST':
        name = request.form['category_name']
        result = tambah_kategori(name)
        if result is True:
            flash(f"Kategori '{name}' berhasil ditambahkan!", "success")
            return redirect(url_for('admin_category_list'))
        else:
            flash(f"Error: {result}", "danger")
    return render_template('admin_kategori_form.html')

@app.route('/admin/categories/edit/<int:category_id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_category(category_id):
    category = get_category_by_id(category_id)
    if not category:
        flash("Kategori tidak ditemukan.", "danger")
        return redirect(url_for('admin_category_list'))
    if request.method == 'POST':
        name = request.form['category_name']
        result = update_kategori(category_id, name)
        if result is True:
            flash(f"Kategori berhasil diperbarui menjadi '{name}'!", "success")
            return redirect(url_for('admin_category_list'))
        else:
            flash(f"Error: {result}", "danger")
    return render_template('admin_kategori_form.html', category=category)

@app.route('/admin/categories/delete/<int:category_id>', methods=['POST'])
@admin_required
def admin_delete_category(category_id):
    result = hapus_kategori(category_id)
    if result is True:
        flash("Kategori berhasil dihapus.", "success")
    else:
        flash(f"Error: {result}", "danger")
    return redirect(url_for('admin_category_list'))

@app.route('/admin/categories/<int:category_id>/books')
@admin_required
def admin_books_by_category(category_id):
    category = get_category_by_id(category_id)
    if not category:
        flash("Kategori tidak ditemukan.", "danger")
        return redirect(url_for('admin_category_list'))
    
    books = get_books_by_category(category_id)
    return render_template('admin_books_by_category.html', books=books, category_name=category['category_name'])

# -- Laporan & Tren --
@app.route('/admin/reports')
@admin_required
def admin_reports_hub():
    return render_template('admin_laporan_hub.html')

@app.route('/admin/reports/borrowals')
@admin_required
def admin_borrowal_report():
    all_borrowals = lihat_semua_peminjaman(limit=50)
    return render_template('admin_laporan_peminjaman.html', peminjaman=all_borrowals)

@app.route('/admin/reports/trends')
@admin_required
def admin_trends_report():
    trends = get_book_trends()
    return render_template('admin_laporan_tren.html', trends=trends)

@app.route('/admin/update-trends', methods=['POST'])
@admin_required
def admin_update_trends():
    hasil = update_book_trends()
    if hasil is True:
        flash("Data tren buku populer berhasil diperbarui!", "success")
    else:
        flash(f"Info: {hasil}", "danger")
    return redirect(url_for('admin_trends_report'))

# -- Aktivitas Pengguna --
@app.route('/admin/activity')
@admin_required
def admin_activity_hub():
    return render_template('admin_aktivitas_hub.html')

@app.route('/admin/activity/logs')
@admin_required
def admin_activity_log():
    logs = lihat_log_aktivitas(limit=25)
    return render_template('admin_aktivitas_log.html', logs=logs)

@app.route('/admin/reviews')
@admin_required
def admin_review_list():
    reviews = lihat_semua_review(limit=50)
    return render_template('admin_ulasan_list.html', reviews=reviews)

@app.route('/admin/profiles')
@admin_required
def admin_user_profiles():
    profiles = get_all_user_profiles()
    return render_template('admin_profil_list.html', profiles=profiles)


# == Rute Pengguna ===============================================
@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/books')
@login_required
def daftar_buku_user():
    semua_buku = lihat_semua_buku()
    return render_template('books.html', books=semua_buku)

@app.route('/buku-untuk-direview')
@login_required
def daftar_buku_review():
    semua_buku = lihat_semua_buku()
    return render_template('daftar_buku_review.html', books=semua_buku)

@app.route('/book/<int:book_id>')
@login_required
def book_detail(book_id):
    book_info = get_book_by_id(book_id)
    reviews = lihat_review_buku(book_id)
    return render_template('book_detail.html', book=book_info, reviews=reviews)

@app.route('/review/tambah/<int:book_id>', methods=['POST'])
@login_required
def tambah_review_proses(book_id):
    user_id = session['user_id']
    username = session['full_name']
    rating = int(request.form['rating'])
    komentar = request.form['komentar']
    hasil = tambah_review(book_id, user_id, username, rating, komentar)
    if hasil is True:
        flash("Terima kasih, review Anda berhasil disimpan!", "success")
    else:
        flash(f"Gagal menyimpan review. Pesan: {hasil}", "danger")
    return redirect(url_for('book_detail', book_id=book_id))

@app.route('/reviews')
@login_required
def semua_review():
    all_reviews = lihat_semua_review()
    return render_template('semua_review.html', reviews=all_reviews)

@app.route('/pinjam/<int:book_id>', methods=['POST'])
@login_required
def proses_pinjam_buku(book_id):
    user_id = session['user_id']
    username = session['full_name']
    hasil = pinjam_buku(user_id, username, book_id)
    if hasil is True:
        flash("Buku berhasil dipinjam!", "success")
    else:
        flash(f"Gagal meminjam buku. Pesan: {hasil}", "danger")
    return redirect(url_for('daftar_buku_user'))

@app.route('/riwayat-peminjaman')
@login_required
def riwayat_peminjaman():
    daftar_pinjaman = lihat_pinjaman_user(session['user_id'])
    return render_template('riwayat_peminjaman.html', pinjaman=daftar_pinjaman)

@app.route('/kembalikan/<int:borrowal_id>', methods=['POST'])
@login_required
def proses_kembalikan_buku(borrowal_id):
    hasil = kembalikan_buku(session['user_id'], session['full_name'], borrowal_id)
    if hasil is True:
        flash("Buku berhasil dikembalikan.", "success")
    else:
        flash(f"Gagal mengembalikan buku. Pesan: {hasil}", "danger")
    return redirect(url_for('riwayat_peminjaman'))

@app.route('/wishlist')
@login_required
def wishlist():
    items = lihat_wishlist_user(session['user_id'])
    return render_template('wishlist.html', wishlist_items=items)

@app.route('/wishlist/tambah/<int:book_id>', methods=['POST'])
@login_required
def proses_tambah_wishlist(book_id):
    user_id = session['user_id']
    username = session['full_name']
    hasil = tambah_ke_wishlist(user_id, username, book_id)
    if hasil is True:
        flash("Buku berhasil ditambahkan ke wishlist!", "success")
    else:
        flash(f"Gagal menambahkan ke wishlist. Pesan: {hasil}", "danger")
    return redirect(request.referrer or url_for('daftar_buku_user'))

@app.route('/wishlist/hapus/<int:wishlist_id>', methods=['POST'])
@login_required
def proses_hapus_wishlist(wishlist_id):
    user_id = session['user_id']
    username = session['full_name']
    hasil = hapus_dari_wishlist(user_id, username, wishlist_id)
    if hasil is True:
        flash("Item berhasil dihapus dari wishlist.", "success")
    else:
        flash(f"Gagal menghapus. Pesan: {hasil}", "danger")
    return redirect(url_for('wishlist'))

@app.route('/buku-populer')
@login_required
def buku_populer():
    trends = get_book_trends()
    return render_template('buku_populer.html', trends=trends)

@app.route('/update-trends', methods=['POST'])
@login_required
def update_trends():
    hasil = update_book_trends()
    if hasil is True:
        flash("Data tren buku populer berhasil diperbarui!", "success")
    else:
        flash(f"Info: {hasil}", "danger")
    return redirect(url_for('buku_populer'))

@app.route('/rekomendasi')
@login_required
def rekomendasi():
    rekomendasi_data = dapatkan_rekomendasi_buku(session['user_id'])
    return render_template('rekomendasi.html', rekomendasi=rekomendasi_data)

@app.route('/profil')
@login_required
def profil():
    user_id = session['user_id']
    username = session['full_name']
    update_user_preference_profile(user_id, username)
    profile_data = get_user_preference(user_id)
    return render_template('profil.html', profile=profile_data)

# == Rute Autentikasi ==
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('index'))
    if request.method == 'POST':
        user = user_login(request.form['email'], request.form['password'])
        if user:
            session['user_id'] = user['user_id']
            session['full_name'] = user['full_name']
            session['role'] = 'user'
            flash('Login berhasil!', 'success')
            return redirect(url_for('dashboard')) 
        else:
            flash('Login Gagal. Cek kembali email dan password Anda.', 'danger')
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('index'))
    if request.method == 'POST':
        hasil = register_user(request.form['full_name'], request.form['email'], request.form['password'])
        if hasil is True:
            flash('Akun berhasil dibuat! Silakan login.', 'success')
            return redirect(url_for('login'))
        else:
            flash(hasil, 'danger')
            return redirect(url_for('register'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Anda telah berhasil logout.', 'success')
    return redirect(url_for('index'))

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login_proses():
    if request.method == 'POST':
        admin_user = admin_login(request.form['username'], request.form['password'])
        if admin_user:
            session['user_id'] = admin_user['username'] 
            session['full_name'] = admin_user['username'].capitalize()
            session['role'] = 'admin'
            flash('Login sebagai admin berhasil!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Username atau Password Admin salah.', 'danger')
            return redirect(url_for('admin_login_proses'))
    return render_template('admin_login.html')

if __name__ == '__main__':
    app.run(debug=True)
