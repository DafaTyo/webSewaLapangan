from flask import Flask, render_template, redirect, url_for, request, session, flash
from pymongo import MongoClient
from bson import ObjectId
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
import os
import re

app = Flask(__name__)
app.secret_key = os.urandom(24)

client = MongoClient('mongodb://localhost:27017/')

db = client['Database_Nou']
users_collection = db['users']
lapangan_collection = db['lapangan']
pelanggan_collection = db['pelanggan']
pemesanan_collection = db['pemesanan']
riwayat_collection = db['riwayat']

# Kodingan Home
@app.route('/')
def home():
    return render_template('home.html')

# Routes untuk User
@app.route('/register', methods=['GET', 'POST'])
def userRegister():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        # Validasi input kosong
        if not username or not email or not password:
            flash('Semua kolom harus diisi!', 'error')
            return redirect('/register')
        
        # Cek apakah username telah digunakan
        existing_user = users_collection.find_one({'username': username})
        if existing_user:
            flash('Username sudah digunakan!', 'error')
            return redirect('/register')
        
        # Cek format email
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            flash('email tidak valid', 'error')
            return redirect(url_for('register'))
        
        # Cek apakah email telah digunakan
        existing_email = users_collection.find_one({'email': email})
        if existing_email:
            flash('Email sudah digunakan!', 'error')
            return redirect('/register')
        
        # Cek panjang password
        if len(password) < 8:
            flash('Password harus minimal 8 karakter!', 'error')
            return redirect('/register')
        
        # Jika semua validasi berhasil, buat user baru
        hashed_password = generate_password_hash(password)
        
        # Simpan ke database
        new_user = {
            'username': username,
            'email': email,
            'password': hashed_password
        }
        
        try:
            users_collection.insert_one(new_user)
            flash('Registrasi berhasil! Silakan login.', 'success')
            return redirect('/login')
        except Exception as e:
            flash('Terjadi kesalahan. Silakan coba lagi.', 'error')
            return redirect('/register')
            
    # Jika method GET, tampilkan form register
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def userLogin():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = users_collection.find_one({'username': username})
        
        if user and check_password_hash(user['password'], password):
            session['username'] = username
            flash('Login berhasil!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Username atau password salah!', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def userLogout():
    session.pop('username', None)
    flash('Anda telah logout.', 'success')
    return redirect(url_for('home'))


# Kodingan Admin

# Decorator untuk memastikan user sudah login sebagai admin
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session:
            flash('Silakan login terlebih dahulu', 'error')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# Routes untuk Admin

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        admin = db.admin.find_one({'username': username, 'password': password})
        if admin:
            session['admin_logged_in'] = True
            flash('Login berhasil!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Username atau password salah!', 'error')
    
    return render_template('admin/login.html')

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('admin_login'))

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    return render_template('admin/dashboard.html')

# CRUD Lapangan
@app.route('/admin/lapangan')
@admin_required
def kelola_lapangan():
    lapangan = db.lapangan.find()
    return render_template('admin/lapangan/index.html', lapangan=lapangan)

@app.route('/admin/lapangan/tambah', methods=['GET', 'POST'])
@admin_required
def tambah_lapangan():
    if request.method == 'POST':
        lapangan_baru = {
            'nama': request.form['nama'],
            'jenis': request.form['jenis'],
            'harga_per_jam': float(request.form['harga_per_jam']),
            'deskripsi': request.form['deskripsi'],
            'status': 'tersedia'
        }
        
        db.lapangan.insert_one(lapangan_baru)
        flash('Lapangan berhasil ditambahkan!', 'success')
        return redirect(url_for('kelola_lapangan'))
    
    return render_template('admin/lapangan/tambah.html')

@app.route('/admin/lapangan/edit/<id>', methods=['GET', 'POST'])
@admin_required
def edit_lapangan(id):
    lapangan = db.lapangan.find_one({'_id': ObjectId(id)})
    
    if request.method == 'POST':
        update_data = {
            'nama': request.form['nama'],
            'jenis': request.form['jenis'],
            'harga_per_jam': float(request.form['harga_per_jam']),
            'deskripsi': request.form['deskripsi']
        }
        
        db.lapangan.update_one({'_id': ObjectId(id)}, {'$set': update_data})
        flash('Lapangan berhasil diupdate!', 'success')
        return redirect(url_for('kelola_lapangan'))
    
    return render_template('admin/lapangan/edit.html', lapangan=lapangan)

@app.route('/admin/lapangan/hapus/<id>')
@admin_required
def hapus_lapangan(id):
    db.lapangan.delete_one({'_id': ObjectId(id)})
    flash('Lapangan berhasil dihapus!', 'success')
    return redirect(url_for('kelola_lapangan'))

# Kelola Penyewaan
@app.route('/admin/penyewaan')
@admin_required
def kelola_penyewaan():
    penyewaan = db.penyewaan.find()
    return render_template('admin/penyewaan/index.html', penyewaan=penyewaan)

@app.route('/admin/penyewaan/detail/<id>')
@admin_required
def detail_penyewaan(id):
    penyewaan = db.penyewaan.find_one({'_id': ObjectId(id)})
    return render_template('admin/penyewaan/detail.html', penyewaan=penyewaan)

@app.route('/admin/penyewaan/status/<id>', methods=['POST'])
@admin_required
def update_status_penyewaan(id):
    status_baru = request.form['status']
    db.penyewaan.update_one(
        {'_id': ObjectId(id)},
        {'$set': {'status': status_baru}}
    )
    flash('Status penyewaan berhasil diupdate!', 'success')
    return redirect(url_for('kelola_penyewaan'))

# Kelola Pelanggan
@app.route('/admin/pelanggan')
@admin_required
def kelola_pelanggan():
    pelanggan = db.pelanggan.find()
    return render_template('admin/pelanggan/index.html', pelanggan=pelanggan)

@app.route('/admin/pelanggan/detail/<id>')
@admin_required
def detail_pelanggan(id):
    pelanggan = db.pelanggan.find_one({'_id': ObjectId(id)})
    riwayat_penyewaan = db.penyewaan.find({'id_pelanggan': ObjectId(id)})
    return render_template('admin/pelanggan/detail.html', 
                         pelanggan=pelanggan, 
                         riwayat_penyewaan=riwayat_penyewaan)

# Kelola Pemesanan
@app.route('/admin/pemesanan')
@admin_required
def kelola_pemesanan():
    pemesanan = db.penyewaan.find({'status': 'pending'})
    return render_template('admin/pemesanan/index.html', pemesanan=pemesanan)

@app.route('/admin/pemesanan/konfirmasi/<id>')
@admin_required
def konfirmasi_pemesanan(id):
    db.penyewaan.update_one(
        {'_id': ObjectId(id)},
        {'$set': {'status': 'dikonfirmasi'}}
    )
    flash('Pemesanan berhasil dikonfirmasi!', 'success')
    return redirect(url_for('kelola_pemesanan'))

@app.route('/admin/pemesanan/tolak/<id>')
@admin_required
def tolak_pemesanan(id):
    db.penyewaan.update_one(
        {'_id': ObjectId(id)},
        {'$set': {'status': 'ditolak'}}
    )
    flash('Pemesanan berhasil ditolak!', 'success')
    return redirect(url_for('kelola_pemesanan'))

# Riwayat Pesanan
@app.route('/admin/riwayat')
@admin_required
def riwayat_pesanan():
    riwayat = db.penyewaan.find({
        'status': {'$in': ['selesai', 'dibatalkan']}
    }).sort('tanggal_pesanan', -1)
    return render_template('admin/riwayat/index.html', riwayat=riwayat)


if __name__ == '__main__':
    app.run(debug=True) 