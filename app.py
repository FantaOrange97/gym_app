from flask import Flask, render_template, request, redirect, session, url_for
import sqlite3
import os
import bcrypt

app = Flask(__name__)
app.secret_key = 'password'  # this should be better
USER_DB = 'users.db'
WINS_DB = 'wins.db'

# make users db if it dont exist
def init_user_db():
    with sqlite3.connect(USER_DB) as db:
        cur = db.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password_hash BLOB,
                is_admin INTEGER DEFAULT 0
            )
        ''')
        db.commit()

# same thing but for win data stuff
def init_wins_db():
    with sqlite3.connect(WINS_DB) as db:
        cur = db.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS wins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                title TEXT,
                description TEXT,
                image TEXT,
                auction_date TEXT,
                final_bid REAL
            )
        ''')
        db.commit()

@app.route('/')
def index():
    if 'user_id' in session:
        if session.get('username') == 'admin':
            return redirect('/admin')
        return redirect('/dashboard')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['username']
        pw = request.form['password'].encode('utf-8')
        admin = 1 if name.lower() == 'admin' else 0
        hashed = bcrypt.hashpw(pw, bcrypt.gensalt())
        try:
            with sqlite3.connect(USER_DB) as db:
                db.cursor().execute(
                    'INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, ?)',
                    (name, hashed, admin)
                )
                db.commit()
            return redirect('/')
        except:
            return 'name in use bruh', 400
    return render_template('register.html')

@app.route('/login', methods=['POST'])
def login():
    name = request.form['username']
    pw = request.form['password'].encode('utf-8')

    with sqlite3.connect(USER_DB) as db:
        cur = db.cursor()
        cur.execute('SELECT id, password_hash, is_admin FROM users WHERE username=?', (name,))
        usr = cur.fetchone()

        if usr and bcrypt.checkpw(pw, usr[1]):
            session['user_id'] = usr[0]
            session['username'] = name
            session['is_admin'] = bool(usr[2])
            if name == 'admin':
                return redirect('/admin')
            return redirect('/dashboard')
    return 'bad login', 401

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session or 'username' not in session:
        return redirect('/')
    with sqlite3.connect(WINS_DB) as db:
        cur = db.cursor()
        cur.execute('SELECT title, description, image, auction_date, final_bid FROM wins WHERE username=?',
                    (session['username'],))
        data = cur.fetchall()
    return render_template('dashboard.html', auctions=data)

@app.route('/admin', methods=['GET', 'POST'])
def admin_panel():
    if session.get('username') != 'admin':
        return redirect('/')

    with sqlite3.connect(USER_DB) as db:
        cur = db.cursor()
        cur.execute('SELECT username FROM users WHERE username != "admin"')
        users = [u[0] for u in cur.fetchall()]

    if request.method == 'POST':
        uname = request.form['username']
        title = request.form['title']
        desc = request.form['description']
        img = request.form['image']
        date = request.form['auction_date']
        bid = float(request.form['final_bid'])

        with sqlite3.connect(WINS_DB) as db:
            db.cursor().execute(
                'INSERT INTO wins (username, title, description, image, auction_date, final_bid) VALUES (?, ?, ?, ?, ?, ?)',
                (uname, title, desc, img, date, bid)
            )
            db.commit()
        return redirect('/admin')

    with sqlite3.connect(WINS_DB) as db:
        cur = db.cursor()
        cur.execute('SELECT * FROM wins')
        wins = [{
            'id': r[0],
            'username': r[1],
            'title': r[2],
            'description': r[3],
            'image': r[4],
            'auction_date': r[5],
            'final_bid': r[6]
        } for r in cur.fetchall()]

    return render_template('admin_panel.html', users=users, wins=wins)

@app.route('/edit_win/<int:win_id>', methods=['POST'])
def edit_win(win_id):
    if session.get('username') != 'admin':
        return redirect('/')
    new_title = request.form['title']
    new_desc = request.form['description']
    new_img = request.form['image']
    new_date = request.form['auction_date']
    new_bid = float(request.form['final_bid'])

    with sqlite3.connect(WINS_DB) as db:
        db.cursor().execute('''
            UPDATE wins SET title=?, description=?, image=?, auction_date=?, final_bid=? WHERE id=?
        ''', (new_title, new_desc, new_img, new_date, new_bid, win_id))
        db.commit()
    return redirect('/admin')

@app.route('/delete_win/<int:win_id>')
def delete_win(win_id):
    if session.get('username') != 'admin':
        return redirect('/')
    with sqlite3.connect(WINS_DB) as db:
        db.cursor().execute('DELETE FROM wins WHERE id=?', (win_id,))
        db.commit()
    return redirect('/admin')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    if not os.path.isfile(USER_DB):
        init_user_db()
    if not os.path.isfile(WINS_DB):
        init_wins_db()
    app.run(host='0.0.0.0', port=10000, debug=True)
