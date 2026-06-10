from flask import Flask, render_template, request, redirect, session, url_for
import sqlite3
import os
import joblib
import time
import pandas as pd
from contextlib import contextmanager
from datetime import datetime

app = Flask(__name__)
app.secret_key = "secret123"

# -----------------------------
# Database helper with retry mechanism
# -----------------------------
@contextmanager
def get_db_connection():
    """Get database connection with retry mechanism"""
    max_retries = 3
    retry_delay = 0.1
    
    for attempt in range(max_retries):
        try:
            conn = sqlite3.connect("users.db", timeout=10)
            conn.row_factory = sqlite3.Row
            yield conn
            conn.close()
            break
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e) and attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
            else:
                raise
        finally:
            if 'conn' in locals():
                conn.close()

# -----------------------------
# Load ML Model with Feature Names
# -----------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
model_path = os.path.join(BASE_DIR, "heart_knn_model.pkl")

# Define feature names (matching your training data)
feature_names = ['age', 'sex', 'cp', 'trestbps', 'chol', 'fbs', 'restecg', 
                 'thalach', 'exang', 'oldpeak', 'slope', 'ca', 'thal']

if os.path.exists(model_path):
    model = joblib.load(model_path)
    print("✅ Model loaded successfully")
else:
    model = None
    print("❌ Model file not found!")

# -----------------------------
# Initialize and Update Database
# -----------------------------
def init_db():
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            
            # Check if users table exists
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
            table_exists = cur.fetchone()
            
            if not table_exists:
                # Create fresh table with all columns
                cur.execute("""
                CREATE TABLE users(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE,
                    password TEXT,
                    register_date TIMESTAMP,
                    last_login TIMESTAMP
                )
                """)
                print("✅ New users table created with all columns")
            else:
                # Check existing columns
                cur.execute("PRAGMA table_info(users)")
                columns = [column[1] for column in cur.fetchall()]
                
                # Add register_date if it doesn't exist
                if 'register_date' not in columns:
                    print("📅 Adding register_date column...")
                    cur.execute("ALTER TABLE users ADD COLUMN register_date TIMESTAMP")
                    print("✅ register_date column added successfully")
                
                # Add last_login if it doesn't exist
                if 'last_login' not in columns:
                    print("🔐 Adding last_login column...")
                    cur.execute("ALTER TABLE users ADD COLUMN last_login TIMESTAMP")
                    print("✅ last_login column added successfully")
            
            conn.commit()
            print("✅ Database initialized successfully")
    except Exception as e:
        print(f"❌ Database initialization error: {e}")

# Run database initialization
init_db()

# -----------------------------
# Root Route - Show Register Page First
# -----------------------------
@app.route('/')
def root():
    if 'user' in session:
        return redirect('/home')
    return redirect('/register')

# -----------------------------
# Home Page (Protected) - Prediction Page
# -----------------------------
@app.route('/home')
def home():
    if 'user' in session:
        return render_template("index.html", user=session['user'])
    return redirect('/login')

# -----------------------------
# Register Page - First Page Users See
# -----------------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user' in session:
        return redirect('/home')
        
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        try:
            with get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO users(username, password, register_date) VALUES (?, ?, ?)",
                    (username, password, current_time)
                )
                conn.commit()
            return redirect('/login')
        except sqlite3.IntegrityError:
            return "⚠️ Username already exists!"
        except Exception as e:
            return f"❌ Registration error: {str(e)}"

    return render_template("register.html")

# -----------------------------
# Login Page
# -----------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user' in session:
        return redirect('/home')
        
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        try:
            with get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT * FROM users WHERE username=? AND password=?",
                    (username, password)
                )
                user = cur.fetchone()
                
            if user:
                try:
                    with get_db_connection() as conn:
                        cur = conn.cursor()
                        cur.execute(
                            "UPDATE users SET last_login = ? WHERE username = ?",
                            (current_time, username)
                        )
                        conn.commit()
                except:
                    pass
                
                session['user'] = username
                return redirect('/home')
            else:
                return "❌ Invalid username or password!"
        except Exception as e:
            return f"❌ Login error: {str(e)}"

    return render_template("login.html")

# -----------------------------
# Logout
# -----------------------------
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/register')

# -----------------------------
# Members Page - Show all registered users
# -----------------------------
@app.route('/members')
def members():
    if 'user' not in session:
        return redirect('/login')
    
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            
            cur.execute("SELECT COUNT(*) as count FROM users")
            result = cur.fetchone()
            total_count = result['count'] if result else 0
            
            today_date = datetime.now().strftime('%Y-%m-%d')
            cur.execute("""
                SELECT COUNT(*) as count FROM users 
                WHERE date(register_date) = ?
            """, (today_date,))
            result = cur.fetchone()
            today_registrations = result['count'] if result else 0
            
            try:
                cur.execute("""
                    SELECT id, username, register_date, last_login 
                    FROM users 
                    ORDER BY id DESC
                """)
                users = cur.fetchall()
            except:
                cur.execute("SELECT id, username FROM users ORDER BY id DESC")
                users = cur.fetchall()
            
        return render_template(
            "members.html", 
            users=users, 
            total_count=total_count,
            today_registrations=today_registrations,
            current_user=session['user']
        )
    except Exception as e:
        return f"❌ Error fetching members: {str(e)}"

# -----------------------------
# Matrix Page - Show Confusion Matrix and Classification Report
# -----------------------------
@app.route('/matrix')
def matrix():
    if 'user' not in session:
        return redirect('/login')
    
    # Model performance metrics (replace with your actual model metrics)
    metrics = {
        'tn': 85,
        'fp': 15,
        'fn': 10,
        'tp': 90,
        'accuracy': 0.875,
        'precision_0': 0.895,
        'precision_1': 0.857,
        'recall_0': 0.850,
        'recall_1': 0.900,
        'f1_0': 0.872,
        'f1_1': 0.878,
        'support_0': 100,
        'support_1': 100,
        'training_date': datetime.now().strftime('%Y-%m-%d')
    }
    
    return render_template(
        "matrix.html",
        current_user=session['user'],
        **metrics
    )

# -----------------------------
# Prediction (Protected) - Fixed feature names warning
# -----------------------------
@app.route('/predict', methods=['POST'])
def predict():
    if 'user' not in session:
        return redirect('/login')

    if model is None:
        return "❌ Model not loaded!"

    try:
        # Create DataFrame with feature names to avoid warning
        data = pd.DataFrame([[
            float(request.form['age']),
            float(request.form['sex']),
            float(request.form['cp']),
            float(request.form['trestbps']),
            float(request.form['chol']),
            float(request.form['fbs']),
            float(request.form['restecg']),
            float(request.form['thalach']),
            float(request.form['exang']),
            float(request.form['oldpeak']),
            float(request.form['slope']),
            float(request.form['ca']),
            float(request.form['thal'])
        ]], columns=feature_names)

        prediction = model.predict(data)[0]

        if prediction == 1:
            result = "⚠️ High Risk of Heart Disease"
        else:
            result = "✅ Low Risk of Heart Disease"

        return render_template(
            "index.html",
            user=session['user'],
            prediction_text=result
        )

    except Exception as e:
        return f"❌ Error: {str(e)}"

# -----------------------------
# Run App
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)