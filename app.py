from flask import Flask, render_template, request, redirect, session, url_for, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from database import init_db, simpan_riwayat
from collections import Counter
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'secretkey'  # Ganti dengan key rahasia yang lebih kuat

DATABASE = 'users.db'

@app.route('/')
def root_redirect():
    # Mengarahkan pengguna langsung ke halaman login saat mengakses root URL
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        # Validasi konfirmasi password
        if password != confirm_password:
            flash("Password dan konfirmasi password tidak cocok.", "error")
            return render_template('register.html')

        hashed_password = generate_password_hash(password)

        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)", (name, email, hashed_password))
            conn.commit()
            flash("Registrasi berhasil. Silakan login.", "success")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("Email sudah terdaftar.", "error")
        finally:
            conn.close()

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = c.fetchone()
        conn.close()

        if user and check_password_hash(user[3], password):
            session['user_id'] = user[0]
            session['user_name'] = user[1]
            return redirect(url_for('home'))
        else:
            flash("Email atau password salah.", "error")
    return render_template('login.html')

@app.route('/home')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    # Ambil diagnosa terakhir user berdasarkan tanggal terbaru
    c.execute('SELECT * FROM riwayat WHERE user_id = ? ORDER BY tanggal DESC LIMIT 1', (user_id,))
    last_diagnosis = c.fetchone()
    conn.close()
    return render_template('home.html', name=session['user_name'], last_diagnosis=last_diagnosis)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/diagnosa')
def diagnosa():
    return render_template('diagnosa.html')

@app.route('/diagnosa/<type>')
def diagnosa_tipe(type):
    if type == 'kanker':
        return redirect(url_for('diagnosa_kanker'))
    elif type == 'gerd':
        return redirect(url_for('diagnosa_gerd_form'))
    else:
        return "Jenis diagnosa tidak dikenal.", 404

@app.route('/diagnosa/kanker')
def diagnosa_kanker():
    return render_template('diagnosa-kanker.html')

@app.route('/diagnosa/kanker/hasil', methods=['POST'])
def hasil_diagnosa_kanker():
    if 'user_id' not in session:
        return jsonify({"message": "Unauthorized"}), 401
    jawaban = request.json.get('jawaban', [])
    jumlah_ya = jawaban.count("ya")
    jumlah_tidak = jawaban.count("tidak")

    # Logika diagnosa
    hasil = ""
    saran = ""
    pengobatan = ""
    pantangan = ""

    if jumlah_ya >= 6:
        hasil = "Anda terindikasi mengidap kanker. Segera konsultasikan ke dokter."
        saran = "Konsultasi dengan Dokter Spesialis Onkologi."
        pengobatan = "Kemoterapi, radioterapi, operasi, dan imunoterapi , lakukan sesuai petunjuk dokter.."
        pantangan = "Hindari makanan tinggi lemak, daging merah, dan alkohol."
    elif jumlah_ya >= 4:
        hasil = "Gejala kanker perlu diwaspadai, risiko moderat."
        saran = "Disarankan untuk konsultasi dengan dokter."
        pengobatan = "Perubahan gaya hidup dan observasi mandiri."
        pantangan = "Kurangi makanan olahan, perbanyak sayur dan buah."
    else:
        hasil = "Anda tidak terindikasi kanker berdasarkan gejala yang diberikan."
        saran = "Tetap lakukan medical check-up secara berkala."
        pengobatan = "Tidak perlu pengobatan, lakukan gaya hidup sehat."
        pantangan = "Tidak ada pantangan khusus."

    # Simpan riwayat diagnosa
    simpan_riwayat(hasil, saran, pengobatan, pantangan, jumlah_ya, jumlah_tidak, session['user_id'])

    return jsonify({
        "hasil": hasil,
        "saran": saran,
        "pengobatan": pengobatan,
        "pantangan": pantangan,
        "jumlah_ya": jumlah_ya,
        "jumlah_tidak": jumlah_tidak
    })

@app.route('/diagnosa/kanker/hasil/view')
def tampil_hasil_kanker():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    hasil = request.args.get('hasil', '')
    saran = request.args.get('saran', '')
    pengobatan = request.args.get('pengobatan', '')
    pantangan = request.args.get('pantangan', '')
    jumlah_ya = int(request.args.get('jumlah_ya', 0))
    jumlah_tidak = int(request.args.get('jumlah_tidak', 0))

    return render_template('hasil-diagnosa-kanker.html',
        hasil=hasil,
        saran=saran,
        pengobatan=pengobatan,
        pantangan=pantangan,
        jumlah_ya=jumlah_ya,
        jumlah_tidak=jumlah_tidak)

@app.route('/diagnosa/gerd')
def diagnosa_gerd_form():
    return render_template('diagnosa_gerd.html')

@app.route('/diagnosa/gerd/hasil', methods=['POST'])
def hasil_diagnosa_gerd():
    if 'user_id' not in session:
        return jsonify({"message": "Unauthorized"}), 401
    jawaban = request.json.get('jawaban')

    EXPECTED_QUESTION_COUNT = 11
    if not isinstance(jawaban, list) or len(jawaban) != EXPECTED_QUESTION_COUNT:
        return jsonify({"message": "Data jawaban tidak valid atau tidak lengkap."}), 400

    jumlah_ya = jawaban.count("ya")
    jumlah_tidak = len(jawaban) - jumlah_ya

    # 6 pertanyaan pertama untuk Maag, 5 sisanya untuk Asam Lambung
    ya_maag = jawaban[0:6].count('ya')
    ya_asam = jawaban[6:11].count('ya')

    persen_maag = (ya_maag / 6) * 100
    persen_asam = (ya_asam / 5) * 100

    total_persen = persen_maag + persen_asam

    hasil = ""
    saran = ""
    pengobatan = ""
    pantangan = ""

    if total_persen >= 80:
        hasil = "Anda kemungkinan mengalami GERD."
        saran = "Segera periksakan diri ke dokter."
        pengobatan = "Obat-obatan seperti PPI (Proton Pump Inhibitors) atau H2 Blocker, Sebaiknya digunakan berdasarkan anjuran dan pengawasan dokter."
        pantangan = "Hindari makanan pedas, asam, berlemak, dan kafein."

    elif persen_maag == 0 and persen_asam == 0:
        hasil = "Tidak ada indikasi kuat terhadap GERD, maag, atau asam lambung."
        saran = "Lakukan pemeriksaan kesehatan rutin."
        pengobatan = "Tidak perlu pengobatan khusus."
        pantangan = "Jaga pola makan teratur."

    elif persen_maag > persen_asam:
        hasil = "Anda kemungkinan mengalami Maag."
        saran = "Hindari kopi, alkohol, dan makanan pedas."
        pengobatan = "Antasida atau obat pelindung mukosa , sebaiknya digunakan sesuai anjuran dokter."
        pantangan = "Hindari kopi, alkohol, makanan pedas."

    else:
        hasil = "Anda kemungkinan mengalami Asam Lambung."
        saran = "Cobalah menghindari makanan asam dan pedas."
        pengobatan = "Obat Antasida, sebaiknya digunakan sesuai anjuran dokter."
        pantangan = "Hindari makanan asam, pedas, dan berlemak."

    simpan_riwayat(hasil, saran, pengobatan, pantangan, jumlah_ya, jumlah_tidak, session['user_id'])

    return jsonify({
        "hasil": hasil,
        "saran": saran,
        "pengobatan": pengobatan,
        "pantangan": pantangan,
        "jumlah_ya": jumlah_ya,
        "jumlah_tidak": jumlah_tidak,
        "persen_maag": persen_maag,
        "persen_asam": persen_asam,
        "total_persen": total_persen
    })


@app.route('/diagnosa/gerd/hasil/view')
def tampil_hasil_gerd():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    hasil = request.args.get('hasil', '')
    saran = request.args.get('saran', '')
    pengobatan = request.args.get('pengobatan', '')
    pantangan = request.args.get('pantangan', '')
    jumlah_ya = int(request.args.get('jumlah_ya', 0))
    jumlah_tidak = int(request.args.get('jumlah_tidak', 0))

    return render_template('hasil_gerd.html',
        hasil=hasil,
        saran=saran,
        pengobatan=pengobatan,
        pantangan=pantangan,
        jumlah_ya=jumlah_ya,
        jumlah_tidak=jumlah_tidak)
    
@app.route('/riwayat')
def lihat_riwayat():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT id, diagnosa, saran, pengobatan, pantangan, jumlah_ya, jumlah_tidak, tanggal FROM riwayat WHERE user_id = ? ORDER BY tanggal DESC', (session['user_id'],))
    riwayat_list = c.fetchall()
    conn.close()

    return render_template('riwayat.html', riwayat_list=riwayat_list)


@app.route('/riwayat/<int:riwayat_id>')
def detail_riwayat(riwayat_id):
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM riwayat WHERE id = ?', (riwayat_id,))
    riwayat = c.fetchone()
    conn.close()

    if not riwayat:
        return "Riwayat tidak ditemukan.", 404
    
    return render_template('detail_riwayat.html', riwayat=riwayat)

@app.route('/informasi-penyakit')
def informasi_penyakit():
    return render_template('informasi_penyakit.html')

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def simpan_diagnosa(penyakit, tanggal, gejala):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('INSERT INTO diagnosis (penyakit, tanggal, gejala_dipilih) VALUES (?, ?, ?)',
    (penyakit, tanggal, gejala))
    conn.commit()
    conn.close()

@app.route('/statistik')
def statistik():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    # [DIUBAH] Mengambil semua data yang diperlukan dari riwayat dalam satu query
    cursor.execute("SELECT diagnosa, tanggal, jumlah_ya, jumlah_tidak FROM riwayat")
    data = cursor.fetchall()
    
    # Inisialisasi variabel dengan nilai default
    pie_labels, pie_series = [], []
    bar_categories, bar_series = [], []
    line_categories = ['Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu', 'Minggu']
    line_series = [0] * 7

    # Hanya proses jika 'data' tidak kosong
    if data:
        # --- Pie Chart: Distribusi Diagnosa (sesuai keinginan Anda) ---
        pie_data = Counter(row[0] for row in data if row[0]) # Menghitung hanya jika diagnosa tidak kosong
        pie_labels = list(pie_data.keys())
        pie_series = list(pie_data.values())

        # --- Line Chart: Jumlah Diagnosa per Hari ---
        weekly_data = {hari: 0 for hari in line_categories}
        for row in data:
            try:
                tanggal = datetime.strptime(row[1], '%Y-%m-%d %H:%M:%S')
                hari_inggris = tanggal.strftime('%A')
                # Mapping hari inggris ke indonesia
                map_hari = {'Monday': 'Senin', 'Tuesday': 'Selasa', 'Wednesday': 'Rabu', 'Thursday': 'Kamis', 'Friday': 'Jumat', 'Saturday': 'Sabtu', 'Sunday': 'Minggu'}
                hari_indonesia = map_hari.get(hari_inggris, 'Senin')
                if hari_indonesia in weekly_data:
                    weekly_data[hari_indonesia] += 1
            except (ValueError, TypeError):
                continue
        line_series = list(weekly_data.values())

        # --- Bar Chart: Jumlah Total Jawaban Ya dan Tidak ---
        total_ya = sum(row[2] for row in data)
        total_tidak = sum(row[3] for row in data)
        bar_categories = ['Jawaban Ya', 'Jawaban Tidak']
        bar_series = [total_ya, total_tidak]

    conn.close()

    return render_template('statistik.html',
    pie_labels=pie_labels,
    pie_series=pie_series,
    line_categories=line_categories,
    line_series=line_series,
    bar_categories=bar_categories,
    bar_series=bar_series
    )

if __name__ == '__main__':
    init_db()  # Inisialisasi database saat aplikasi dimulai
    app.run(debug=True)  # Jalankan aplikasi dalam mode debug
