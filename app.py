from flask import Flask, render_template, request, redirect, url_for, session, flash
import pymysql.cursors
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta, date

app = Flask(__name__)
app.secret_key = "replace_with_a_random_secret_key"

# ---------- MySQL Configuration ----------
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',         # change as per your setup
    'password': 'root123',  # change as per your setup
    'database': 'laundrydb',
    'cursorclass': pymysql.cursors.DictCursor
}

def get_db():
    return pymysql.connect(**DB_CONFIG)

# ---------- Helper Functions ----------
def get_user_by_email(email):
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM users WHERE email=%s", (email,))
    user = cur.fetchone()
    cur.close()
    db.close()
    return user

def get_user_by_id(uid):
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM users WHERE id=%s", (uid,))
    user = cur.fetchone()
    cur.close()
    db.close()
    return user

# ---------- Routes ----------

@app.route('/')
def index():
    return render_template('index.html')

# ---------- Register ----------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name'].strip()
        email = request.form['email'].strip().lower()
        phone = request.form.get('phone', '').strip()
        password = request.form['password']

        if get_user_by_email(email):
            flash("Email already registered.", "danger")
            return redirect(url_for('register'))

        pw_hash = generate_password_hash(password)
        db = get_db()
        cur = db.cursor()
        cur.execute("""
            INSERT INTO users (name, email, password_hash, phone, role)
            VALUES (%s, %s, %s, %s, %s)
        """, (name, email, pw_hash, phone, 'user'))
        db.commit()
        cur.close()
        db.close()

        flash("Registered successfully. Please log in.", "success")
        return redirect(url_for('login'))

    return render_template('register.html')

# ---------- Login ----------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password']
        user = get_user_by_email(email)

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['role'] = user['role']
            session['user_name'] = user['name']
            flash("Login successful.", "success")
            return redirect(url_for('dashboard'))

        flash("Invalid credentials.", "danger")
    return render_template('login.html')

# ---------- Logout ----------
@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for('index'))

# ---------- Dashboard ----------
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    role = session.get('role', 'user')

    if role == 'admin':
        return redirect(url_for('admin_dashboard'))

    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT b.id AS booking_id, b.status, s.slot_date, s.slot_start, s.slot_end,
               m.name AS machine_name
        FROM bookings b
        JOIN slots s ON b.slot_id = s.id
        JOIN machines m ON s.machine_id = m.id
        WHERE b.user_id = %s
        ORDER BY s.slot_date DESC, s.slot_start DESC
    """, (session['user_id'],))
    bookings = cur.fetchall()
    cur.close()
    db.close()

    return render_template('dashboard.html', bookings=bookings)

# ---------- View Slots ----------
@app.route('/slots')
def view_slots():
    if 'user_id' not in session:
        flash("Please login to view slots.", "warning")
        return redirect(url_for('login'))

    db = get_db()
    cur = db.cursor()
    today = date.today()
    cur.execute("""
        SELECT s.*, m.name AS machine_name,
            (SELECT COUNT(*) FROM bookings b WHERE b.slot_id = s.id AND b.status = 'booked') AS booked_count
        FROM slots s
        JOIN machines m ON s.machine_id = m.id
        WHERE s.slot_date >= %s
        ORDER BY s.slot_date, s.slot_start
    """, (today,))
    slots = cur.fetchall()
    cur.close()
    db.close()

    return render_template('view_slots.html', slots=slots)

# ---------- demo Slots ----------
@app.route('/create_demo_slots', methods=['GET', 'POST'])
def create_demo_slots():
    db = get_db()
    cur = db.cursor()

    if request.method == 'POST':
        machine_id = request.form['machine_id']
        slot_date = request.form['slot_date']
        slot_start = request.form['slot_start']
        slot_end = request.form['slot_end']

        cur.execute("""
            INSERT INTO slots (machine_id, slot_date, slot_start, slot_end)
            VALUES (%s, %s, %s, %s)
        """, (machine_id, slot_date, slot_start, slot_end))
        db.commit()
        cur.close()
        db.close()
        flash("New slot created successfully!", "success")
        return redirect(url_for('view_slots'))

    cur.execute("SELECT * FROM machines")
    machines = cur.fetchall()
    cur.close()
    db.close()

    return render_template('create_demo_slots.html', machines=machines)

# ---------- Book Slot ----------
@app.route('/book/<int:slot_id>', methods=['GET', 'POST'])
def book_slot(slot_id):
    if 'user_id' not in session:
        flash("Login required.", "warning")
        return redirect(url_for('login'))

    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT s.*, m.name AS machine_name
        FROM slots s
        JOIN machines m ON s.machine_id = m.id
        WHERE s.id = %s
    """, (slot_id,))
    slot = cur.fetchone()

    if not slot:
        flash("Slot not found.", "danger")
        cur.close()
        db.close()
        return redirect(url_for('view_slots'))

    cur.execute("SELECT * FROM bookings WHERE slot_id = %s AND status = 'booked'", (slot_id,))
    existing = cur.fetchone()

    if request.method == 'POST':
        if existing:
            flash("Slot already booked.", "danger")
        else:
            cur.execute("INSERT INTO bookings (user_id, slot_id) VALUES (%s, %s)",
                        (session['user_id'], slot_id))
            db.commit()
            flash("Slot booked successfully!", "success")

        cur.close()
        db.close()
        return redirect(url_for('dashboard'))

    cur.close()
    db.close()
    return render_template('book_slot.html', slot=slot, existing=existing)

# ---------- Cancel Booking ----------
@app.route('/cancel/<int:booking_id>')
def cancel_booking(booking_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM bookings WHERE id = %s", (booking_id,))
    booking = cur.fetchone()

    if not booking:
        flash("Booking not found.", "danger")
        cur.close()
        db.close()
        return redirect(url_for('dashboard'))

    cur.execute("UPDATE bookings SET status = 'cancelled' WHERE id = %s", (booking_id,))
    db.commit()
    cur.close()
    db.close()

    flash("Booking cancelled successfully.", "info")
    return redirect(url_for('dashboard'))

# ---------- Admin Dashboard ----------
@app.route('/admin')
def admin_dashboard():
    if session.get('role') != 'admin':
        flash("Admin access required.", "danger")
        return redirect(url_for('dashboard'))

    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT COUNT(*) AS users FROM users")
    users_count = cur.fetchone()['users']
    cur.execute("SELECT COUNT(*) AS bookings FROM bookings WHERE status='booked'")
    bookings_count = cur.fetchone()['bookings']
    cur.execute("SELECT * FROM machines")
    machines = cur.fetchall()
    cur.close()
    db.close()

    return render_template('admin_dashboard.html', users_count=users_count,
                           bookings_count=bookings_count, machines=machines)

# ---------- Manage Machines ----------
@app.route('/machines', methods=['GET', 'POST'])
def manage_machines():
    if session.get('role') not in ('admin', 'operator'):
        flash("Operator/Admin access required.", "danger")
        return redirect(url_for('dashboard'))

    db = get_db()
    cur = db.cursor()
    if request.method == 'POST':
        name = request.form['name']
        location = request.form['location']
        cur.execute("INSERT INTO machines (name, location) VALUES (%s, %s)", (name, location))
        db.commit()
        flash("Machine added successfully.", "success")

    cur.execute("SELECT * FROM machines")
    machines = cur.fetchall()
    cur.close()
    db.close()

    return render_template('manage_machines.html', machines=machines)

# ---------- Feedback ----------
@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    if 'user_id' not in session:
        flash("Login to send feedback.", "warning")
        return redirect(url_for('login'))

    if request.method == 'POST':
        message = request.form['message']
        db = get_db()
        cur = db.cursor()
        cur.execute("INSERT INTO feedback (user_id, message) VALUES (%s, %s)",
                    (session['user_id'], message))
        db.commit()
        cur.close()
        db.close()
        flash("Thank you for your feedback!", "success")
        return redirect(url_for('dashboard'))

    return render_template('feedback.html')

# ---------- Run App ----------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

