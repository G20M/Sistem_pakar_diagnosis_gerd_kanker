import sqlite3
from datetime import datetime

DATABASE = 'users.db'

def init_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    # Buat tabel jika belum ada
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS riwayat (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        diagnosa TEXT,
        saran TEXT,
        pengobatan TEXT,
        pantangan TEXT,
        jumlah_ya INTEGER,
        jumlah_tidak INTEGER,
        tanggal TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    conn.commit()
    conn.close()

def simpan_riwayat(diagnosa, saran, pengobatan, pantangan, jumlah_ya, jumlah_tidak, user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO riwayat (user_id, diagnosa, saran, pengobatan, pantangan, jumlah_ya, jumlah_tidak, tanggal)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, diagnosa, saran, pengobatan, pantangan, jumlah_ya, jumlah_tidak, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()