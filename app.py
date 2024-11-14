import os
import re
from flask import Flask, render_template, redirect, url_for, request, session, flash
from pymongo import MongoClient
from functools import wraps
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.urandom(24)

client = MongoClient('mongodb://localhost:27017/')

db = client['Database_Nou']
users_collection = db['users']
dataLapangan_collection = db['dataLapangan']
admins_collection = db['admin']


# Kodingan Home
@app.route('/')
def home():
    return render_template('home.html')


# Kodingan User
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
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session:
            flash('Silakan login terlebih dahulu', 'error')
            return redirect(url_for('adminLogin'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/admin/login', methods=['GET', 'POST'])
def adminLogin():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = admins_collection.find_one({'username': username})
        
        if admin and check_password_hash(user['password'], password):
            session['admin_logged_in'] = True
            flash('Login berhasil!', 'success')
            return redirect(url_for('admin'))
        else:
            flash('Username atau password salah!', 'error')    
    return render_template('admin/login.html')

@app.route('/admin')
@admin_required
def admin():
    jumlah_lapangan = dataLapangan_collection.count_documents({})
    return render_template('admin/home.html', jumlahLapangan=jumlah_lapangan)

# kodingan lapangan

@app.route('/admin/lapangan')
@admin_required
def lapangan():
    lapangan1 = dataLapangan_collection.find()
    lapangan2 = dataLapangan_collection.find()
    return render_template('admin/lapangan.html', lapangan1=lapangan1, lapangan2=lapangan2)

@app.route('/admin/lapangan/tambah', methods=['GET', 'POST'])
@admin_required
def tambahLapangan():
    if request.method == 'POST':
        jenis_lapangan = request.form['jenis_lapangan']
        harga_lapangan = request.form['harga_lapangan']
        nama_lapangan = request.form['nama_lapangan']
        foto_lapangan = request.files['foto_lapangan']
        deskripsi_lapangan = request.form['deskripsi_lapangan']
        
        if foto_lapangan:
            nama_file_asli = foto_lapangan.filename
            nama_file_foto = secure_filename(nama_file_asli)
            file_path = f'./static/dist/img/gambarLapangan/{nama_file_foto}'
            foto_lapangan.save(file_path)
        else:
            nama_file_foto = None
            
        dataLapangan_collection.insert_one({
            'jenis': jenis_lapangan,
            'harga': harga_lapangan,
            'nama': nama_lapangan,
            'foto': nama_file_foto,
            'deskripsi': deskripsi_lapangan
        })
        
        return redirect(url_for("lapangan"))
    return redirect(url_for("lapangan"))

@app.route('/admin/lapangan/edit/<string:id>', methods=['GET', 'POST'])
@admin_required
def editLapangan(id):
    if request.method == 'POST':
        jenis_lapangan = request.form['jenis_lapangan']
        harga_lapangan = request.form['harga_lapangan']
        nama_lapangan = request.form['nama_lapangan']
        deskripsi_lapangan = request.form['deskripsi_lapangan']
        foto_lapangan = request.files['foto_lapangan']
        
        if foto_lapangan:
            lapangan = dataLapangan_collection.find_one({'_id': ObjectId(id)})
            file_path = f'./static/dist/img/gambarLapangan/{lapangan["foto"]}'
            if os.path.exists(file_path):
                os.remove(file_path)

            nama_file_asli = foto_lapangan.filename
            nama_file_foto = secure_filename(nama_file_asli)
            file_path = f'./static/dist/img/gambarLapangan/{nama_file_foto}'
            foto_lapangan.save(file_path)
            
            dataLapangan_collection.update_one({'_id': ObjectId(id)}, {'$set': {
                'jenis': jenis_lapangan,
                'harga': harga_lapangan,
                'nama': nama_lapangan,
                'foto': nama_file_foto,
                'deskripsi': deskripsi_lapangan
            }})
        else:
            dataLapangan_collection.update_one({'_id': ObjectId(id)}, {'$set': {
                'jenis': jenis_lapangan,
                'harga': harga_lapangan,
                'nama': nama_lapangan,
                'deskripsi': deskripsi_lapangan
            }})
        
        return redirect(url_for('lapangan'))
    return redirect(url_for('lapangan'))

@app.route('/admin/lapangan/hapus/<string:id>')
@admin_required
def hapusLapangan(id):
    lapangan = dataLapangan_collection.find_one({'_id': ObjectId(id)})
    file_path = f'./static/dist/img/gambarLapangan/{lapangan["foto"]}'
    if os.path.exists(file_path):
        os.remove(file_path)

    dataLapangan_collection.delete_one({'_id': ObjectId(id)})
    return redirect(url_for('lapangan'))

if __name__ == '__main__':
    app.run(debug=True) 