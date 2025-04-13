from flask import Flask, render_template, request, redirect, session, url_for, jsonify
import sqlite3
import os
import bcrypt
from datetime import datetime
import threading, time
from flask import send_file
from io import BytesIO


app = Flask(__name__)
app.secret_key = 'supersecretkey'
DB_NAME = 'gym.db'

#------------- Downloading excel file --------------
@app.route('/download-usage')
def download_usage():
    import pandas as pd
    from datetime import datetime
    output = BytesIO()
    
    try:
        query = """ ... """  # Keep as is

        with sqlite3.connect(DB_NAME) as conn:
            df = pd.read_sql_query(query, conn)

        print("Data fetched:", df.shape)

        def calc_age(dob):
            try:
                birth = datetime.strptime(dob, "%Y-%m-%d")
                today = datetime.today()
                return today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
            except Exception as e:
                print("Error parsing DOB:", dob, str(e))
                return None

        df["age"] = df["dob"].apply(calc_age)

        def age_group(age):
            if age is None: return "Unknown"
            if age < 18: return "Under 18"
            if age < 30: return "18–29"
            if age < 45: return "30–44"
            if age < 60: return "45–59"
            return "60+"

        df["age_group"] = df["age"].apply(age_group)

        print("Processed DataFrame columns:", df.columns)

        df.to_excel(output, index=False, engine='openpyxl')
        output.seek(0)

        return send_file(
            output,
            as_attachment=True,
            download_name="usage_data_detailed.xlsx",
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        print("Download route error:", str(e))
        return "Something went wrong while generating the file", 500


# ------------------ DB INIT ------------------
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        email TEXT UNIQUE NOT NULL,
                        telephone TEXT,
                        dob TEXT,
                        sex TEXT,
                        funds REAL DEFAULT 0.00,
                        password_hash BLOB NOT NULL)''')

        c.execute('''CREATE TABLE IF NOT EXISTS equipment (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        type TEXT,
                        image TEXT)''')

        c.execute('''CREATE TABLE IF NOT EXISTS usage (
                        user_id INTEGER,
                        equipment_id INTEGER,
                        usage_date TEXT,
                        end_usage_date TEXT,
                        hours_used REAL DEFAULT 0,
                        FOREIGN KEY(user_id) REFERENCES users(id),
                        FOREIGN KEY(equipment_id) REFERENCES equipment(id))''')

        # Insert default equipment
        c.execute("SELECT COUNT(*) FROM equipment")
        if c.fetchone()[0] == 0:
            equipment_data = [
                ('Bench Press', 'Strength', None),
                ('Dumbbells', 'Weights', None),
                ('Squat Rack', 'Strength', None),
                ('Cable Machine', 'Machine', None),
                ('Treadmill', 'Cardio', None),
                ('Elliptical', 'Cardio', None),
                ('name_test_updated', 'type_test_updated', '7427712c78997333016a1651e068507e')
            ]
            c.executemany("INSERT INTO equipment (name, type, image) VALUES (?, ?, ?)", equipment_data)

        conn.commit()

# ------------------ Live Balance Updater ------------------
def simulate_usage_increment(user_id):
    for i in range(30):  # 30 loops = ~60 seconds
        time.sleep(2)
        with sqlite3.connect(DB_NAME) as conn:
            c = conn.cursor()
            increment = 1 * (2/3600)  # £1/hour rate
            c.execute("UPDATE users SET funds = funds + ? WHERE id=?", (increment, user_id))
            c.execute("SELECT funds FROM users WHERE id=?", (user_id,))
            balance = c.fetchone()[0]
            print(f"[{i*2}s] LIVE BALANCE: User {user_id} = £{balance:.2f}")
            conn.commit()

# ------------------ ROUTES ------------------
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        telephone = request.form['telephone']
        dob = request.form['dob']
        sex = request.form['sex']
        password = request.form['password'].encode('utf-8')
        password_hash = bcrypt.hashpw(password, bcrypt.gensalt())
        try:
            with sqlite3.connect(DB_NAME) as conn:
                c = conn.cursor()
                c.execute('INSERT INTO users (name, email, telephone, dob, sex, password_hash) VALUES (?, ?, ?, ?, ?, ?)',
                          (name, email, telephone, dob, sex, password_hash))
                conn.commit()
            return redirect(url_for('index'))
        except sqlite3.IntegrityError:
            return 'Email already exists', 400
    return render_template('signup.html')

@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    password = request.form['password'].encode('utf-8')
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute('SELECT id, name, password_hash FROM users WHERE email=?', (email,))
        user = c.fetchone()
        if user and bcrypt.checkpw(password, user[2]):
            session['user_id'] = user[0]
            session['username'] = user[1]
            return redirect(url_for('dashboard'))
    return 'Invalid credentials', 401

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute('SELECT name, funds FROM users WHERE id=?', (session['user_id'],))
        user_info = c.fetchone()
        c.execute('SELECT * FROM equipment')
        equipment = c.fetchall()
    return render_template('dashboard.html', user=user_info, equipment=equipment)

@app.route('/use-equipment', methods=['POST'])
def use_equipment():
    action = request.form['action']
    equipment_id = int(request.form['equipment_id'])
    user_id = session['user_id']
    now = datetime.now().isoformat()

    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        if action == 'start':
            c.execute("INSERT INTO usage (user_id, equipment_id, usage_date) VALUES (?, ?, ?)",
                      (user_id, equipment_id, now))
            threading.Thread(target=simulate_usage_increment, args=(user_id,)).start()
        elif action == 'end':
            c.execute("SELECT usage_date FROM usage WHERE user_id=? AND equipment_id=? AND end_usage_date IS NULL",
                      (user_id, equipment_id))
            row = c.fetchone()
            if row:
                start_time = datetime.fromisoformat(row[0])
                end_time = datetime.fromisoformat(now)
                hours_used = round((end_time - start_time).total_seconds() / 3600, 2)
                c.execute("UPDATE usage SET end_usage_date=?, hours_used=? WHERE user_id=? AND equipment_id=? AND end_usage_date IS NULL",
                          (now, hours_used, user_id, equipment_id))
        conn.commit()
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# ------------------ INIT + RUN ------------------
if __name__ == '__main__':
    if not os.path.exists(DB_NAME):
        init_db()
    app.run(host='0.0.0.0', port=8000)