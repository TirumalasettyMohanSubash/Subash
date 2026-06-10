from flask import Flask, render_template, request, redirect, session
import sqlite3
import joblib
from train_model import train_model
app = Flask(__name__)
app.secret_key = 'secret123'

# Create table
conn = sqlite3.connect("user.db")
conn.execute('''
CREATE TABLE IF NOT EXISTS TWO(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    password TEXT,
    role TEXT
)
''')

# Default admin
admin = conn.execute(
    "SELECT * FROM TWO WHERE username=?",
    ("admin",)
).fetchone()
if not admin:
    conn.execute(
        "INSERT INTO TWO(username,password,role) VALUES(?,?,?)",
        ("admin", "admin123", "admin")
    )
conn.commit()
conn.close()

# Home
@app.route('/')
def home():
    return render_template('index.html')

# Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect("user.db")
        conn.execute(
            "INSERT INTO TWO(username,password,role) VALUES(?,?,?)",
            (username, password, "user")
        )
        conn.commit()
        conn.close()
        return redirect('/login')
    return render_template('register.html')

# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect("user.db")
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM TWO WHERE username=? AND password=?",
            (username, password)
        )
        user = cursor.fetchone()
        conn.close()
        if user:
            session['user'] = username
            session['role'] = user[3]
            if user[3] == 'admin':
                return redirect('/admin')
            else:
                return redirect('/user')
    return render_template('login.html')

# Admin Dashboard
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if 'user' not in session:
        return redirect('/login')
    accuracy = None
    if request.method == 'POST':
        accuracy = train_model()
    return render_template('admin.html', accuracy=accuracy)

# User Dashboard
@app.route('/user', methods=['GET', 'POST'])
def user_dashboard():
    if 'user' not in session:
        return redirect('/login')
    result = None
    if request.method == 'POST':
        area = float(request.form['area'])
        bedrooms = int(request.form['bedrooms'])
        model = joblib.load('model.pkl')
        prediction = model.predict([[area, bedrooms]])
        result = round(prediction[0], 2)

    return render_template('user.html', result=result)

# Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)