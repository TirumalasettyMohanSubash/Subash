from flask import Flask, render_template, request, redirect, url_for, session, jsonify, Response, send_file
import numpy as np
import pickle
import sqlite3
import os
from tensorflow.keras.models import load_model
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "super_secret_key"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")

ADMIN_EMAIL = "admin@gmail.com"
ADMIN_PASSWORD = "123"

model = load_model("disease_model.h5")
scaler = pickle.load(open("scaler.pkl", "rb"))
label_encoder = pickle.load(open("label_encoder.pkl", "rb"))

# ================= DATABASE =================
def init_db():
    conn = sqlite3.connect(DB_PATH)

    conn.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT UNIQUE,
        password TEXT
    )
    ''')

    try:
        conn.execute("ALTER TABLE users ADD COLUMN photo TEXT DEFAULT 'default.png'")
    except:
        pass

    try:
        conn.execute("ALTER TABLE users ADD COLUMN status TEXT DEFAULT 'Active'")
    except:
        pass

    conn.execute('''
    CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_email TEXT,
        disease TEXT,
        confidence REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    conn.commit()
    conn.close()

init_db()

# ================= USER REGISTER =================
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])

        try:
            conn = sqlite3.connect(DB_PATH)
            conn.execute("INSERT INTO users(name,email,password,photo,status) VALUES(?,?,?,?,?)",
                         (name, email, password, "default.png", "Active"))
            conn.commit()
            conn.close()
            return redirect(url_for('user_login'))
        except:
            return render_template("register.html", error="User already exists")

    return render_template("register.html")

# ================= USER LOGIN =================
@app.route('/user_login', methods=['GET', 'POST'])
def user_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = sqlite3.connect(DB_PATH)
        user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        conn.close()

        if user and check_password_hash(user[3], password):

            if user[5] == "Blocked":
                return render_template("user_login.html", error="Your account has been blocked by admin")

            session.clear()
            session['user'] = email
            return redirect(url_for('home'))
        else:
            return render_template("user_login.html", error="Invalid Email or Password")

    return render_template("user_login.html")

# ================= USER LOGOUT =================
@app.route('/user_logout')
def user_logout():
    session.pop('user', None)
    return redirect(url_for('user_login'))

# ================= USER HOME =================
@app.route('/')
def home():
    if 'user' not in session:
        return redirect(url_for('user_login'))
    return render_template("index.html")

# ================= PROFILE =================
@app.route('/profile')
def profile():
    if 'user' not in session:
        return redirect(url_for('user_login'))

    conn = sqlite3.connect(DB_PATH)
    user = conn.execute("SELECT * FROM users WHERE email=?", (session['user'],)).fetchone()

    total_predictions = conn.execute(
        "SELECT COUNT(*) FROM history WHERE user_email=?",
        (session['user'],)
    ).fetchone()[0]

    last_record = conn.execute(
        "SELECT disease, confidence FROM history WHERE user_email=? ORDER BY id DESC LIMIT 1",
        (session['user'],)
    ).fetchone()

    conn.close()

    return render_template("profile.html",
                           user=user,
                           total_predictions=total_predictions,
                           last_record=last_record)

@app.route('/upload_photo', methods=['POST'])
def upload_photo():
    if 'user' not in session:
        return redirect(url_for('user_login'))

    file = request.files['photo']

    if file:
        filename = secure_filename(file.filename)
        upload_folder = os.path.join(BASE_DIR, "static", "uploads")

        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)

        file.save(os.path.join(upload_folder, filename))

        conn = sqlite3.connect(DB_PATH)
        conn.execute("UPDATE users SET photo=? WHERE email=?", (filename, session['user']))
        conn.commit()
        conn.close()

    return redirect(url_for('profile'))

@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'user' not in session:
        return redirect(url_for('user_login'))

    new_name = request.form['name']
    new_email = request.form['email']
    new_password = request.form['password']

    conn = sqlite3.connect(DB_PATH)

    if new_password.strip():
        hashed_password = generate_password_hash(new_password)
        conn.execute("UPDATE users SET name=?,email=?,password=? WHERE email=?",
                     (new_name, new_email, hashed_password, session['user']))
    else:
        conn.execute("UPDATE users SET name=?,email=? WHERE email=?",
                     (new_name, new_email, session['user']))

    conn.commit()
    conn.close()

    session['user'] = new_email
    return redirect(url_for('profile'))

# ================= PREDICT =================
@app.route('/predict', methods=['POST'])
def predict():
    if 'user' not in session:
        return redirect(url_for('user_login'))

    data = np.array([[int(request.form['fever']),
                      int(request.form['cough']),
                      int(request.form['headache']),
                      int(request.form['fatigue']),
                      int(request.form['body_pain']),
                      int(request.form['sore_throat']),
                      int(request.form['breathing_issue']),
                      float(request.form['bp_level']),
                      float(request.form['sugar_level']),
                      float(request.form['heart_rate'])]])

    data = scaler.transform(data)
    prediction = model.predict(data)[0]

    top3 = prediction.argsort()[-3:][::-1]
    diseases = label_encoder.inverse_transform(top3)
    confidences = prediction[top3] * 100

    main_disease = diseases[0]

    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT INTO history(user_email,disease,confidence) VALUES(?,?,?)",
                 (session['user'], main_disease, float(confidences[0])))
    conn.commit()
    conn.close()

    return render_template("result.html",
                           diseases=zip(diseases, confidences),
                           disease=main_disease,
                           confidence=round(confidences[0], 2))

# ================= HISTORY =================
@app.route('/history')
def history():
    if 'user' not in session:
        return redirect(url_for('user_login'))

    conn = sqlite3.connect(DB_PATH)
    data = conn.execute("SELECT * FROM history WHERE user_email=?", (session['user'],)).fetchall()
    conn.close()

    return render_template("history.html", data=data)

# ================= DOWNLOAD PDF =================
@app.route('/download')
def download():
    if 'user' not in session:
        return redirect(url_for('user_login'))

    disease = request.args.get('disease')
    confidence = request.args.get('confidence')
    precautions = request.args.get('precautions')

    conn = sqlite3.connect(DB_PATH)
    user = conn.execute("SELECT * FROM users WHERE email=?", (session['user'],)).fetchone()
    conn.close()

    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors

    filename = "medical_report.pdf"
    pdf = SimpleDocTemplate(filename, pagesize=A4)
    styles = getSampleStyleSheet()

    elements = []
    elements.append(Paragraph("AI MEDICAL DIAGNOSIS REPORT", styles['Title']))
    elements.append(Spacer(1,20))
    elements.append(Paragraph(f"Patient Name: {user[1]}", styles['Normal']))
    elements.append(Paragraph(f"Patient Email: {user[2]}", styles['Normal']))
    elements.append(Spacer(1,20))

    report_data = [
        ["Predicted Disease", disease],
        ["Confidence", confidence + "%"],
        ["Precautions", precautions]
    ]

    table = Table(report_data, colWidths=[150,300])
    table.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),colors.lightblue),
        ('GRID',(0,0),(-1,-1),1,colors.black),
        ('FONTNAME',(0,0),(-1,-1),'Helvetica-Bold')
    ]))

    elements.append(table)
    pdf.build(elements)

    return send_file(filename, as_attachment=True)

# ================= CHATBOT =================
@app.route('/chat', methods=['POST'])
def chat():
    msg = request.json['message'].lower()

    if "fever" in msg:
        ans = "Fever may indicate infection. Drink fluids."
    elif "cough" in msg:
        ans = "Persistent cough may indicate throat infection."
    elif "headache" in msg:
        ans = "Headache can occur due to stress or dehydration."
    else:
        ans = "Please consult doctor for better medical guidance."

    return jsonify({"response": ans})

# ================= ADMIN =================
@app.route('/admin', methods=['GET','POST'])
def admin():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
            session.clear()
            session['admin'] = ADMIN_EMAIL
            return redirect(url_for('dashboard'))
        else:
            return render_template("admin_login.html", error="Invalid Admin Credentials")

    return render_template("admin_login.html")

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('admin'))

@app.route('/admin/dashboard')
def dashboard():
    if 'admin' not in session:
        return redirect(url_for('admin'))

    conn = sqlite3.connect(DB_PATH)

    total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    total_reports = conn.execute("SELECT COUNT(*) FROM history").fetchone()[0]

    today_reports = conn.execute("""
        SELECT COUNT(*) FROM history
        WHERE date(created_at)=date('now','localtime')
    """).fetchone()[0]

    recent_reports = conn.execute("""
        SELECT user_email,disease,confidence,created_at
        FROM history
        ORDER BY id DESC LIMIT 5
    """).fetchall()

    disease_data = conn.execute("""
        SELECT disease, COUNT(*) FROM history
        GROUP BY disease
        ORDER BY COUNT(*) DESC
        LIMIT 5
    """).fetchall()

    conn.close()

    disease_labels = [x[0] for x in disease_data]
    disease_counts = [x[1] for x in disease_data]

    return render_template("dashboard.html",
                           total_users=total_users,
                           total_reports=total_reports,
                           today_reports=today_reports,
                           recent_reports=recent_reports,
                           disease_labels=disease_labels,
                           disease_counts=disease_counts)

@app.route('/admin/users')
def users():
    if 'admin' not in session:
        return redirect(url_for('admin'))

    conn = sqlite3.connect(DB_PATH)
    users = conn.execute("SELECT * FROM users").fetchall()
    conn.close()

    return render_template("users.html", users=users)

@app.route('/admin/delete_user/<int:id>')
def delete_user(id):
    if 'admin' not in session:
        return redirect(url_for('admin'))

    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM users WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return redirect(url_for('users'))

@app.route('/admin/block_user/<int:id>')
def block_user(id):
    if 'admin' not in session:
        return redirect(url_for('admin'))

    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE users SET status='Blocked' WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return redirect(url_for('users'))

@app.route('/admin/unblock_user/<int:id>')
def unblock_user(id):
    if 'admin' not in session:
        return redirect(url_for('admin'))

    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE users SET status='Active' WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return redirect(url_for('users'))

@app.route('/admin/reports')
def reports():
    if 'admin' not in session:
        return redirect(url_for('admin'))

    conn = sqlite3.connect(DB_PATH)
    reports = conn.execute("SELECT * FROM history").fetchall()
    conn.close()

    return render_template("reports.html", reports=reports)

@app.route('/admin/delete_report/<int:id>')
def delete_report(id):
    if 'admin' not in session:
        return redirect(url_for('admin'))

    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM history WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return redirect(url_for('reports'))

@app.route('/admin/download_reports')
def download_reports():
    if 'admin' not in session:
        return redirect(url_for('admin'))

    conn = sqlite3.connect(DB_PATH)
    reports = conn.execute("SELECT * FROM history").fetchall()
    conn.close()

    def generate():
        data = [['ID','User Email','Disease','Confidence','Date']]
        for row in reports:
            data.append(row)
        for row in data:
            yield ','.join(map(str,row)) + '\n'

    return Response(generate(),
                    mimetype='text/csv',
                    headers={"Content-Disposition":"attachment;filename=medical_reports.csv"})

if __name__ == "__main__":
    app.run(debug=True)