from flask import Flask, render_template, request, redirect, session
import random
import smtplib
import sqlite3
import time

app = Flask(__name__)
app.secret_key = "secret123"

# ---------------- DATABASE ----------------
def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        email TEXT,
        password TEXT,
        otp INTEGER,
        created_at REAL,
        verified INTEGER DEFAULT 0
    )
    """)
    conn.commit()
    conn.close()

init_db()

# ---------------- SEND EMAIL ----------------
def send_email(to_email, otp):
    sender_email = "mohansubash9966@gmail.com"
    password = "obwl kzyh kvqa cvar" # 🔥 App password

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.ehlo()
        server.starttls()
        server.ehlo()

        server.login(sender_email, password)

        subject = "OTP Verification"
        body = f"Your OTP is {otp}"
        message = f"Subject: {subject}\n\n{body}"

        server.sendmail(sender_email, to_email, message)
        server.quit()

        print("✅ Email sent")

    except Exception as e:
        print("❌ Error:", e)

# ---------------- HOME ----------------
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        otp = random.randint(100000, 999999)
        created_time = time.time()

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO users (email, password, otp, created_at, verified)
        VALUES (?, ?, ?, ?, 0)
        """, (email, password, otp, created_time))

        conn.commit()
        conn.close()

        send_email(email, otp)

        session["email"] = email
        return redirect("/verify")

    return render_template("index.html")

# ---------------- VERIFY OTP ----------------
@app.route("/verify", methods=["GET", "POST"])
def verify():
    email = session.get("email")

    if not email:
        return redirect("/")

    if request.method == "POST":
        user_otp = request.form["otp"]

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        cursor.execute("SELECT otp, created_at FROM users WHERE email=?", (email,))
        data = cursor.fetchone()

        if data:
            db_otp, created_time = data

            # ⏳ Check expiry (5 mins)
            if time.time() - created_time > 300:
                conn.close()
                return render_template("verify.html", message="OTP Expired ⏳. Click Resend.")

            # ✅ Check OTP
            if int(user_otp) == db_otp:
                cursor.execute("UPDATE users SET verified=1 WHERE email=?", (email,))
                conn.commit()
                conn.close()
                return render_template("success.html")
            else:
                conn.close()
                return render_template("error.html", message="Invalid OTP ❌")

    return render_template("verify.html")

# ---------------- RESEND OTP ----------------
@app.route("/resend")
def resend():
    email = session.get("email")

    if not email:
        return redirect("/")

    new_otp = random.randint(100000, 999999)
    new_time = time.time()

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE users 
    SET otp=?, created_at=? 
    WHERE email=?
    """, (new_otp, new_time, email))

    conn.commit()
    conn.close()

    send_email(email, new_otp)

    return render_template("verify.html", message="New OTP sent ✅")

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)