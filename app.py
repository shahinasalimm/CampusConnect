from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
import hashlib
import secrets
from datetime import datetime

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# Database initialization
def init_db():
    conn = sqlite3.connect('campus_connect.db')
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            reg_no TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Marketplace items table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS marketplace_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            price DECIMAL(10,2) NOT NULL,
            category TEXT NOT NULL,
            contact_info TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Events table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            event_date DATE NOT NULL,
            location TEXT NOT NULL,
            registration_link TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Forum tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS forum_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            tags TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS forum_answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (question_id) REFERENCES forum_questions (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()

# Helper functions
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def get_db_connection():
    conn = sqlite3.connect('campus_connect.db')
    conn.row_factory = sqlite3.Row
    return conn

# Routes
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/go/<string:page>')
def go_page(page):
    if 'user_id' not in session:
        flash('Please log in to access this page', 'info')
        return redirect(url_for('login'))
    if page == 'marketplace':
        return redirect(url_for('marketplace'))
    elif page == 'events':
        return redirect(url_for('events'))
    elif page == 'forum':
        return redirect(url_for('forum'))
    else:
        return redirect(url_for('dashboard'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        reg_no = request.form['reg_no']
        password_hash = hash_password(password)
        
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO users (name, email, password_hash, reg_no)
                VALUES (?, ?, ?, ?)
            ''', (name, email, password_hash, reg_no))
            conn.commit()
            flash('Account created successfully! Please log in.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Email or registration number already exists!', 'error')
        finally:
            conn.close()
    
    return render_template('auth/signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        password_hash = hash_password(password)
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ? AND password_hash = ?', (email, password_hash)).fetchone()
        conn.close()
        
        if user:
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials!', 'error')
    
    return render_template('auth/login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html')

# Marketplace routes
@app.route('/marketplace')
def marketplace():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    category = request.args.get('category', '')
    conn = get_db_connection()
    
    if category:
        items = conn.execute('''
            SELECT m.*, u.name as seller_name FROM marketplace_items m
            JOIN users u ON m.user_id = u.id
            WHERE m.category = ?
            ORDER BY m.created_at DESC
        ''', (category,)).fetchall()
    else:
        items = conn.execute('''
            SELECT m.*, u.name as seller_name FROM marketplace_items m
            JOIN users u ON m.user_id = u.id
            ORDER BY m.created_at DESC
        ''').fetchall()
    
    categories = conn.execute('SELECT DISTINCT category FROM marketplace_items ORDER BY category').fetchall()
    conn.close()
    
    return render_template('marketplace/marketplace.html', items=items, categories=categories, selected_category=category)

@app.route('/marketplace/add', methods=['POST'])
def add_marketplace_item():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    title = request.form['title']
    description = request.form['description']
    price = request.form['price']
    category = request.form['category']
    contact_info = request.form['contact_info']
    
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO marketplace_items (user_id, title, description, price, category, contact_info)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (session['user_id'], title, description, price, category, contact_info))
    conn.commit()
    conn.close()
    
    flash('Item posted successfully!', 'success')
    return redirect(url_for('marketplace'))

@app.route('/api/reveal-contact/<int:item_id>')
def reveal_contact(item_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    conn = get_db_connection()
    item = conn.execute('SELECT contact_info FROM marketplace_items WHERE id = ?', (item_id,)).fetchone()
    conn.close()
    
    if item:
        return jsonify({'contact_info': item['contact_info']})
    else:
        return jsonify({'error': 'Item not found'}), 404

# Events routes
@app.route('/events')
def events():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    events = conn.execute('''
        SELECT e.*, u.name as organizer_name FROM events e
        JOIN users u ON e.user_id = u.id
        ORDER BY e.event_date ASC
    ''').fetchall()
    conn.close()
    
    return render_template('events/events.html', events=events)

@app.route('/events/add', methods=['POST'])
def add_event():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    title = request.form['title']
    description = request.form['description']
    event_date = request.form['event_date']
    location = request.form['location']
    registration_link = request.form['registration_link']
    
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO events (user_id, title, description, event_date, location, registration_link)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (session['user_id'], title, description, event_date, location, registration_link))
    conn.commit()
    conn.close()
    
    flash('Event posted successfully!', 'success')
    return redirect(url_for('events'))

# Forum routes
@app.route('/forum')
def forum():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    questions = conn.execute('''
        SELECT q.*, u.name as author_name,
               COUNT(a.id) as answer_count
        FROM forum_questions q
        JOIN users u ON q.user_id = u.id
        LEFT JOIN forum_answers a ON q.id = a.question_id
        GROUP BY q.id
        ORDER BY q.created_at DESC
    ''').fetchall()
    conn.close()
    
    return render_template('forum/forum.html', questions=questions)

@app.route('/forum/question/<int:question_id>')
def question_detail(question_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    question = conn.execute('SELECT q.*, u.name as author_name FROM forum_questions q JOIN users u ON q.user_id = u.id WHERE q.id = ?', (question_id,)).fetchone()
    answers = conn.execute('SELECT a.*, u.name as author_name FROM forum_answers a JOIN users u ON a.user_id = u.id WHERE a.question_id = ? ORDER BY a.created_at ASC', (question_id,)).fetchall()
    conn.close()
    
    if not question:
        flash('Question not found!', 'error')
        return redirect(url_for('forum'))
    
    return render_template('forum/question_detail.html', question=question, answers=answers)

@app.route('/forum/add_question', methods=['POST'])
def add_question():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    title = request.form['title']
    description = request.form['description']
    tags = request.form['tags']
    
    conn = get_db_connection()
    conn.execute('INSERT INTO forum_questions (user_id, title, description, tags) VALUES (?, ?, ?, ?)',
                 (session['user_id'], title, description, tags))
    conn.commit()
    conn.close()
    
    flash('Question posted successfully!', 'success')
    return redirect(url_for('forum'))

@app.route('/forum/add_answer', methods=['POST'])
def add_answer():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    question_id = request.form['question_id']
    content = request.form['content']
    
    conn = get_db_connection()
    conn.execute('INSERT INTO forum_answers (question_id, user_id, content) VALUES (?, ?, ?)',
                 (question_id, session['user_id'], content))
    conn.commit()
    conn.close()
    
    flash('Answer added successfully!', 'success')
    return redirect(url_for('question_detail', question_id=question_id))

if __name__ == '__main__':
    init_db()  # Optional: creates tables if not exist
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)), debug=False)

