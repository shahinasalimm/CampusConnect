from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime
from config import Config

app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)

# -------------------
# Models
# -------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    regno = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(512), nullable=False)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text, nullable=False)
    image = db.Column(db.String(100), nullable=False)
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    seller_email = db.Column(db.String(150), nullable=False)

class LostItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    date_reported = db.Column(db.Date, default=datetime.utcnow)
    contact_email = db.Column(db.String(150), nullable=False)
    image = db.Column(db.String(100), nullable=True)

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    location = db.Column(db.String(150), nullable=False)
    organizer_email = db.Column(db.String(150), nullable=False)

class Doubt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    author_email = db.Column(db.String(150), nullable=False)
    date_posted = db.Column(db.DateTime, default=datetime.utcnow)

# -------------------
# Routes
# -------------------
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    email = session.get('user_email', '')
    username = email.split('@')[0] if email else 'User'
    return render_template('dashboard.html', username=username)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        regno = request.form['regno'].strip()
        email = request.form['email'].strip()
        password = generate_password_hash(request.form['password'])

        if not regno.upper().startswith('LBT'):
            flash('Registration number must start with "LBT".')
            return redirect(url_for('register'))

        existing = User.query.filter((User.regno == regno) | (User.email == email)).first()
        if existing:
            flash('User with same regno or email already exists.')
            return redirect(url_for('register'))

        new_user = User(regno=regno, email=email, password=password)
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful! Please login.')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        regno = request.form['regno'].strip()
        password = request.form['password']
        user = User.query.filter_by(regno=regno).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['user_email'] = user.email
            flash('Login successful.')
            return redirect(url_for('dashboard'))

        flash('Invalid regno or password.')
        return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.')
    return redirect(url_for('index'))

# -------------------
# CampusCart (Marketplace)
# -------------------
@app.route('/home')
def home():
    products = Product.query.order_by(Product.id.desc()).all()
    return render_template('home.html', products=products)

@app.route('/post', methods=['GET', 'POST'])
def post_product():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        title = request.form['title']
        category = request.form['category']
        price = float(request.form['price'])
        description = request.form['description']
        image_file = request.files['image']

        filename = secure_filename(image_file.filename)
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image_file.save(image_path)

        new_product = Product(
            title=title,
            category=category,
            price=price,
            description=description,
            image=filename,
            seller_id=session['user_id'],
            seller_email=session['user_email']
        )
        db.session.add(new_product)
        db.session.commit()
        flash('Product posted successfully!')
        return redirect(url_for('home'))

    return render_template('post_product.html')

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template('product_detail.html', product=product)

# -------------------
# Lost & Found
# -------------------
@app.route('/lostfound')
def lostfound():
    items = LostItem.query.order_by(LostItem.date_reported.desc()).all()
    return render_template('lostfound.html', items=items)

@app.route('/lostfound/report', methods=['GET', 'POST'])
def report_lostfound():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        item_name = request.form['item_name']
        description = request.form['description']
        status = request.form['status']
        location = request.form['location']
        contact_email = request.form['contact_email']
        image_file = request.files['image']

        filename = secure_filename(image_file.filename) if image_file else ''
        if filename:
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image_file.save(image_path)

        item = LostItem(
            item_name=item_name,
            description=description,
            status=status,
            location=location,
            contact_email=contact_email,
            image=filename
        )
        db.session.add(item)
        db.session.commit()
        flash('Lost/Found report submitted.')
        return redirect(url_for('lostfound'))

    return render_template('report_lostfound.html')

@app.route('/lostfound/<int:item_id>')
def lostfound_detail(item_id):
    item = LostItem.query.get_or_404(item_id)
    return render_template('lostfound_detail.html', item=item)

# -------------------
# Events
# -------------------
@app.route('/events')
def events():
    all_events = Event.query.order_by(Event.date.asc()).all()
    return render_template('events.html', events=all_events)

@app.route('/events/post', methods=['GET', 'POST'])
def post_event():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        date = datetime.strptime(request.form['date'], '%Y-%m-%dT%H:%M')
        location = request.form['location']
        organizer_email = request.form['organizer_email']

        event = Event(
            title=title,
            description=description,
            date=date,
            location=location,
            organizer_email=organizer_email
        )
        db.session.add(event)
        db.session.commit()
        flash('Event posted successfully.')
        return redirect(url_for('events'))

    return render_template('post_event.html')

@app.route('/events/<int:event_id>')
def event_detail(event_id):
    event = Event.query.get_or_404(event_id)
    return render_template('event_detail.html', event=event)

# -------------------
# Doubts & Queries
# -------------------
@app.route('/doubts')
def doubts():
    all_doubts = Doubt.query.order_by(Doubt.date_posted.desc()).all()
    return render_template('doubts.html', doubts=all_doubts)

@app.route('/doubts/ask', methods=['GET', 'POST'])
def ask_doubt():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        author_email = session['user_email']

        doubt = Doubt(title=title, description=description, author_email=author_email)
        db.session.add(doubt)
        db.session.commit()
        flash('Your doubt has been posted.')
        return redirect(url_for('doubts'))

    return render_template('ask_doubt.html')

@app.route('/doubts/<int:doubt_id>')
def doubt_detail(doubt_id):
    doubt = Doubt.query.get_or_404(doubt_id)
    return render_template('doubt_detail.html', doubt=doubt)





# -------------------
# Run App
# -------------------
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)

