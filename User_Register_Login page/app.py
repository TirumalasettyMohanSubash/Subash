from flask import Flask, render_template, request, session, redirect
import sqlite3

app = Flask(__name__)
app.secret_key = "secret_key"

# DATABASE CONNECTION
def connect_db():
    conn = sqlite3.connect("user.db")
    conn.row_factory = sqlite3.Row
    return conn

# CREATE TABLE
conn = connect_db()

conn.execute('''
CREATE TABLE IF NOT EXISTS RO (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    password TEXT,
    role TEXT,
    status TEXT
)
''')

# DEFAULT ADMIN
admin = conn.execute(
    "SELECT * FROM RO WHERE username='admin'"
).fetchone()

if not admin:
    conn.execute(
        "INSERT INTO RO (username, password, role, status) VALUES (?, ?, ?, ?)",
        ("admin", "admin123", "admin", "active")
    )

conn.commit()
conn.close()

# HOME
@app.route('/')
def home():
    return redirect('/login')

# REGISTER
@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']

        conn = connect_db()

        conn.execute(
            "INSERT INTO RO (username, password, role, status) VALUES (?, ?, ?, ?)",
            (username, password, "user", "active")
        )

        conn.commit()
        conn.close()

        return redirect('/login')

    return render_template('register.html')

# LOGIN
@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']

        conn = connect_db()

        user = conn.execute(
            "SELECT * FROM RO WHERE username=? AND password=?",
            (username, password)
        ).fetchone()

        conn.close()

        if user:

            # CHECK BLOCK STATUS
            if user['status'] == 'blocked':
                return "Your account is blocked"

            # STORE SESSION
            session['username'] = user['username']
            session['role'] = user['role']

            # ADMIN LOGIN
            if user['role'] == 'admin':
                return redirect('/admin')

            # USER LOGIN
            else:
                return redirect('/user')

        else:
            return "Invalid Username or Password"

    return render_template('login.html')

# ADMIN DASHBOARD
@app.route('/admin')
def admin():

    if session.get('role') != 'admin':
        return redirect('/login')

    conn = connect_db()

    users = conn.execute(
        "SELECT * FROM RO WHERE role='user'"
    ).fetchall()

    conn.close()

    return render_template('admin.html', users=users)

# BLOCK USER
@app.route('/block/<int:id>')
def block(id):

    if session.get('role') != 'admin':
        return redirect('/login')

    conn = connect_db()

    conn.execute(
        "UPDATE RO SET status='blocked' WHERE id=?",
        (id,)
    )

    conn.commit()
    conn.close()

    return redirect('/admin')

# UNBLOCK USER
@app.route('/unblock/<int:id>')
def unblock(id):

    if session.get('role') != 'admin':
        return redirect('/login')

    conn = connect_db()

    conn.execute(
        "UPDATE RO SET status='active' WHERE id=?",
        (id,)
    )

    conn.commit()
    conn.close()

    return redirect('/admin')

# USER DASHBOARD
@app.route('/user')
def user():

    if session.get('role') != 'user':
        return redirect('/login')

    return render_template('user.html')

# LOGOUT
@app.route('/logout')
def logout():

    session.clear()

    return redirect('/login')

# RUN APP
if __name__ == '__main__':
    app.run(debug=True)