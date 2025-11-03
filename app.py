from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3, os
from werkzeug.utils import secure_filename

app = Flask(__name__, template_folder='templates')
app.secret_key = "supersecretkey"

# ----------------------------- UPLOAD FOLDERS -----------------------------
UPLOAD_FOLDER = "static/uploads"
GALLERY_FOLDER = "static/gallery"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(GALLERY_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["GALLERY_FOLDER"] = GALLERY_FOLDER

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# ----------------------------- DATABASE INIT -----------------------------
def init_db():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    # Users Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            phone TEXT NOT NULL,
            gmail TEXT NOT NULL,
            roll TEXT NOT NULL,
            registration_no TEXT NOT NULL,
            profile_picture TEXT
        )
    ''')

    # Reviews Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            rating INTEGER NOT NULL,
            review TEXT NOT NULL,
            user_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Rooms Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_number TEXT NOT NULL,
            room_type TEXT NOT NULL,
            price TEXT NOT NULL,
            capacity TEXT NOT NULL,
            description TEXT NOT NULL,
            image TEXT
        )
    ''')

    # Room Applications Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS room_applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            father_name TEXT,
            mother_name TEXT,
            present_address TEXT,
            permanent_address TEXT,
            birth_date TEXT,
            session_name TEXT,
            semester TEXT,
            shift TEXT,
            blood_group TEXT,
            department TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    #  Apply for save
    c.execute('''
CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    father_name TEXT,
    mother_name TEXT,
    present_address TEXT,
    permanent_address TEXT,
    birth_date TEXT,
    session TEXT,
    semester TEXT,
    shift TEXT,
    blood_group TEXT,
    department TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')


    conn.commit()
    conn.close()

init_db()

# ----------------------------- UTILS -----------------------------
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ----------------------------- HOME -----------------------------
@app.route('/')
def home():
    return render_template("index.html")

# ----------------------------- REGISTER -----------------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        phone = request.form['phone']
        gmail = request.form['gmail']
        roll = request.form['roll']
        registration_no = request.form['registration_no']

        profile_picture = request.files['profile_picture']
        image_filename = None
        if profile_picture and profile_picture.filename != '':
            image_filename = username + "_" + secure_filename(profile_picture.filename)
            profile_picture.save(os.path.join(app.config["UPLOAD_FOLDER"], image_filename))

        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        try:
            c.execute('''
                INSERT INTO users (username, password, phone, gmail, roll, registration_no, profile_picture)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (username, password, phone, gmail, roll, registration_no, image_filename))
            conn.commit()
            flash("✅ Account created successfully!", "success")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("⚠️ Username already exists!", "danger")
        finally:
            conn.close()
    return render_template("register.html")

# ----------------------------- LOGIN -----------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        user = c.fetchone()
        conn.close()

        if user:
            session['username'] = username
            flash("Welcome back!", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("❌ Invalid username or password", "danger")
    return render_template("login.html")

# ----------------------------- DASHBOARD -----------------------------
@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))

    search_query = request.args.get('search', '').strip().lower()
    page = int(request.args.get('page', 1))
    per_page = 8

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    if search_query:
        c.execute("""
            SELECT * FROM users 
            WHERE LOWER(username) LIKE ? OR roll LIKE ?
            ORDER BY id DESC
        """, (f"%{search_query}%", f"%{search_query}%"))
    else:
        c.execute("SELECT * FROM users ORDER BY id DESC")

    users_all = c.fetchall()
    conn.close()

    total_pages = (len(users_all) + per_page - 1) // per_page
    start = (page - 1) * per_page
    users = users_all[start:start + per_page]

    return render_template(
        'dashboard.html',
        users=users,
        page=page,
        total_pages=total_pages if total_pages > 0 else 1,
        username=session.get('username')
    )

# ----------------------------- PROFILE -----------------------------
@app.route('/profile/<int:user_id>')
def profile(user_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id=?", (user_id,))
    user = c.fetchone()
    c.execute("SELECT * FROM reviews WHERE user_id=? ORDER BY id DESC", (user_id,))
    user_reviews = c.fetchall()
    conn.close()

    if not user:
        flash("User not found!", "danger")
        return redirect(url_for('dashboard'))

    return render_template("profile.html", user=user, user_reviews=user_reviews)

# ----------------------------- GALLERY -----------------------------
@app.route('/gallery', methods=['GET', 'POST'])
def gallery():
    if 'username' not in session:
        flash("⚠️ লগইন করুন প্রথমে!", "danger")
        return redirect(url_for('login'))

    if request.method == 'POST':
        file = request.files.get('photo')
        if not file or file.filename == '':
            flash("⚠️ কোন ফাইল নির্বাচিত হয়নি!", "danger")
            return redirect(request.url)
        
        if allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['GALLERY_FOLDER'], filename))
            flash("✅ ছবি সফলভাবে আপলোড হয়েছে!", "success")
            return redirect(url_for('gallery'))
        else:
            flash("⚠️ শুধুমাত্র PNG, JPG, JPEG, GIF ফাইল অনুমোদিত!", "danger")
            return redirect(request.url)

    photos = os.listdir(app.config['GALLERY_FOLDER'])
    photos = [photo for photo in photos if allowed_file(photo)]
    return render_template("gallery.html", photos=photos, username=session.get('username'))

# ----------------------------- REVIEWS -----------------------------
@app.route('/reviews', methods=['GET', 'POST'])
def reviews():
    if 'username' not in session:
        flash("⚠️ আগে লগইন করুন রিভিউ দিতে!", "danger")
        return redirect(url_for('login'))

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE username=?", (session['username'],))
    user_data = c.fetchone()
    user_id = user_data['id'] if user_data else None

    if request.method == 'POST':
        rating = int(request.form['rating'])
        review_text = request.form['review']
        c.execute('''INSERT INTO reviews (user_id, name, rating, review) VALUES (?, ?, ?, ?)''',
                  (user_id, session['username'], rating, review_text))
        conn.commit()
        flash("✅ তোমার রিভিউ সফলভাবে যুক্ত হয়েছে!", "success")
        return redirect(url_for('reviews'))

    c.execute('''SELECT reviews.*, users.profile_picture 
                 FROM reviews LEFT JOIN users ON reviews.user_id = users.id
                 ORDER BY reviews.id DESC''')
    reviews_data = c.fetchall()
    c.execute("SELECT AVG(rating) FROM reviews")
    avg_rating = c.fetchone()[0] or 0
    conn.close()

    return render_template("reviews.html", reviews=reviews_data, avg_rating=avg_rating)



# ----------------------------- ROOMS -----------------------------
@app.route('/rooms')
def room_details():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM rooms ORDER BY id DESC")
    rooms = c.fetchall()
    conn.close()
    return render_template("rooms.html", rooms=rooms, username=session.get('username'))

# ----------------------------- APPLY -----------------------------
@app.route('/apply', methods=['GET', 'POST'])
def apply():
    if 'username' not in session:
        flash("⚠️ প্রথমে লগইন করুন!", "warning")
        return redirect(url_for('login'))

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=?", (session['username'],))
    user = c.fetchone()

    if request.method == 'POST':
        father_name = request.form['father_name']
        mother_name = request.form['mother_name']
        present_address = request.form['present_address']
        permanent_address = request.form['permanent_address']
        birth_date = request.form['birth_date']
        session_name = request.form['session']
        semester = request.form['semester']
        shift = request.form['shift']
        blood_group = request.form['blood_group']
        department = request.form['department']

        c.execute('''INSERT INTO room_applications 
                     (user_id, father_name, mother_name, present_address, permanent_address, birth_date, session_name, semester, shift, blood_group, department)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (user['id'], father_name, mother_name, present_address, permanent_address, birth_date, session_name, semester, shift, blood_group, department))
        conn.commit()
        conn.close()
        flash("✅ তোমার আবেদন সফলভাবে জমা হয়েছে!", "success")
        return redirect(url_for('apply'))

    conn.close()
    return render_template("apply.html", user=user)


# ----------------------------- ABOUT -----------------------------
@app.route('/about')
def about():
    return render_template("about.html", username=session.get('username'))

# ----------------------------- ADMIN PANEL -----------------------------
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "12345"

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin'] = True
            flash("✅ Admin logged in successfully!", "success")
            return redirect(url_for('admin_dashboard'))
        else:
            flash("❌ Invalid admin credentials!", "danger")
    return render_template('admin_login.html')

#-----------------------------admin dashboard-------------------------

@app.route('/admin_dashboard')
def admin_dashboard():
    if not session.get('admin'):
        flash("⚠️ Please login as admin first!", "danger")
        return redirect(url_for('admin_login'))

    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # সব রুম
    c.execute("SELECT * FROM rooms ORDER BY id DESC")
    rooms = c.fetchall()

    # সব রুম আবেদন (user name সহ)
    c.execute('''
        SELECT ra.*, u.username
        FROM room_applications ra
        LEFT JOIN users u ON ra.user_id = u.id
        ORDER BY ra.id DESC
    ''')
    applications = c.fetchall()

    # সব ইউজার
    c.execute("SELECT * FROM users ORDER BY id DESC")
    users = c.fetchall()

    # সব রিভিউ
    c.execute("SELECT * FROM reviews ORDER BY id DESC")
    reviews = c.fetchall()

    conn.close()

    return render_template('admin_dashboard.html',
                           rooms=rooms,
                           applications=applications,
                           users=users,
                           reviews=reviews)

#------------------------------Add room------------------------------

@app.route('/add_room', methods=['POST'])
def add_room():
    if not session.get('admin'):
        flash("⚠️ Please login as admin first!", "danger")
        return redirect(url_for('admin_login'))

    room_number = request.form.get('room_number')
    room_type = request.form.get('room_type')
    price = request.form.get('price')
    capacity = request.form.get('capacity')
    description = request.form.get('description')

    # Image upload
    image_file = request.files.get('image')
    image_filename = None
    if image_file and image_file.filename != '':
        image_filename = secure_filename(image_file.filename)
        image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO rooms (room_number, room_type, price, capacity, description, image)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (room_number, room_type, price, capacity, description, image_filename))
    conn.commit()
    conn.close()

    flash("✅ Room added successfully!", "success")
    return redirect(url_for('admin_dashboard'))


#----------------------------delete room------------------------

# রুম মুছুন
@app.route('/delete_room/<int:room_id>')
def delete_room(room_id):
    if not session.get('admin'):
        flash("⚠️ Please login as admin first!", "danger")
        return redirect(url_for('admin_login'))

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("DELETE FROM rooms WHERE id=?", (room_id,))
    conn.commit()
    conn.close()
    flash("✅ Room deleted successfully!", "success")
    return redirect(url_for('admin_dashboard'))

# আবেদন মুছুন
@app.route('/delete_application/<int:app_id>')
def delete_application(app_id):
    if not session.get('admin'):
        flash("⚠️ Please login as admin first!", "danger")
        return redirect(url_for('admin_login'))

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("DELETE FROM room_applications WHERE id=?", (app_id,))
    conn.commit()
    conn.close()
    flash("✅ Application deleted successfully!", "success")
    return redirect(url_for('admin_dashboard'))

#--------------------------delete user------------------

@app.route('/admin_delete_user/<int:user_id>')
def admin_delete_user(user_id):
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    flash("🗑️ User deleted successfully!", "info")
    return redirect(url_for('admin_dashboard'))
#---------------------------delete review-------------------------------

@app.route('/admin_delete_review/<int:review_id>')
def admin_delete_review(review_id):
    if not session.get('admin'):
        flash("⚠️ Please login as admin first!", "danger")
        return redirect(url_for('admin_login'))

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("DELETE FROM reviews WHERE id=?", (review_id,))
    conn.commit()
    conn.close()
    flash("🗑️ Review deleted successfully!", "info")
    return redirect(url_for('admin_dashboard'))


#----------------------------admin------------------------------------

@app.route('/admin')
def admin_panel():
    rooms = Room.query.all()
    applications = Application.query.all()
    return render_template('admin_dashboard.html', rooms=rooms, applications=applications)

#--------------------------admin logout-------------------------


@app.route('/admin_logout')
def admin_logout():
    session.pop('admin', None)
    flash("Admin logged out successfully!", "info")
    return redirect(url_for('home'))
#---------------------logout-----------------------

@app.route('/logout')
def logout():
    session.pop('username', None)  # Remove the user session
    flash("✅ Successfully logged out!", "info")
    return redirect(url_for('login'))  # Redirect to login page

# ----------------------------- RUN -----------------------------
if __name__ == '__main__':
    app.run(debug=True)
