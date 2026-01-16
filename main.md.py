# app.py
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_mysqldb import MySQL
import MySQLdb.cursors
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import os

app = Flask(__name__)
app.secret_key = 'secret123'  # TODO: move to env var in production

# ---------------- MySQL configuration ----------------
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'user_signup'
mysql = MySQL(app)

# ---------------- Upload folders ----------------
BASE_UPLOAD = 'static/uploads'
app.config['UPLOAD_FOLDER'] = BASE_UPLOAD

# Ensure folders exist
os.makedirs(os.path.join(BASE_UPLOAD, 'images'), exist_ok=True)
os.makedirs(os.path.join(BASE_UPLOAD, 'videos'), exist_ok=True)
os.makedirs(os.path.join(BASE_UPLOAD, 'team'), exist_ok=True)
os.makedirs(os.path.join('static', 'images', 'winners'), exist_ok=True)

# ---------------- Helpers ----------------
def verify_password(stored: str, provided: str) -> bool:
    """
    Accept both hashed (preferred) and legacy plaintext (fallback).
    """
    try:
        # If stored is a hash, this returns True/False correctly
        if stored and stored.startswith(('pbkdf2:', 'scrypt:', 'bcrypt:')):
            return check_password_hash(stored, provided)
    except Exception:
        pass
    # Legacy fallback: direct compare (plaintext in DB)
    return stored == provided

def login_required_user(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in first.", "warning")
            return redirect(url_for('login'))
        return fn(*args, **kwargs)
    return wrapper

def login_required_admin(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if 'admin' not in session:
            flash("Please login first!", "warning")
            return redirect(url_for('admin_login'))
        return fn(*args, **kwargs)
    return wrapper

# ---------------- Home & Public Pages ----------------
@app.route('/')
def home():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM events ORDER BY date ASC")
    events_list = cursor.fetchall()
    cursor.close()
    return render_template('home.html', events_list=events_list)

# ----- Admin About List -----
@app.route('/admin/about')
@login_required_admin
def admin_about():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM about")
    about_sections = cursor.fetchall()
    cursor.close()
    return render_template('admin_about.html', about_sections=about_sections)


# ----- Admin Edit About -----
@app.route('/admin/edit_about/<int:id>', methods=['GET', 'POST'])
def edit_about(id):
    if 'admin' not in session:
        flash("Please login first!", "warning")
        return redirect(url_for('admin_login'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == 'POST':
        vision = request.form['vision']
        mission = request.form['mission']
        what_we_do = request.form['what_we_do']
        who_can_join = request.form['who_can_join']

        cursor.execute("""
            UPDATE about 
            SET vision=%s, mission=%s, what_we_do=%s, who_can_join=%s
            WHERE id=%s
        """, (vision, mission, what_we_do, who_can_join, id))

        mysql.connection.commit()
        cursor.close()
        flash("About Us section updated successfully!", "success")
        return redirect(url_for('admin_about'))

    cursor.execute("SELECT * FROM about WHERE id=%s", (id,))
    section = cursor.fetchone()
    cursor.close()
    return render_template('admin_edit_about.html', section=section)


# ----- User-Facing About Page -----
@app.route('/about')
def about():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM about")
    about_data = cursor.fetchall()
    cursor.close()

    section = about_data[0] if about_data else None
    return render_template('aboutus.html', section=section)

@app.route('/media')
def media():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM media ORDER BY uploaded_at DESC")
    media_items = cursor.fetchall()
    cursor.close()
    return render_template('Media.html', media_items=media_items)

@app.route('/media_g')
def media_g():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM media ORDER BY uploaded_at DESC")
    media_items = cursor.fetchall()
    cursor.close()
    return render_template('Media_g.html', media_items=media_items)

# Contact page
@app.route('/contact')
def contact_page():
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Contact info
    cur.execute("SELECT * FROM contact_info WHERE id=1")
    contact = cur.fetchone()

    # Core team info - only main 4 posts in proper order
    cur.execute("""
        SELECT * FROM team 
        WHERE role IN ('President','Co-President','Secretary','Treasurer')
        ORDER BY FIELD(role, 'President','Co-President','Secretary','Treasurer')
    """)
    core_team_members = cur.fetchall()

    cur.close()
    return render_template('contactus.html', contact=contact, team_members=core_team_members)



# Send message route
@app.route('/send_message', methods=['POST'])
def send_message():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        message = request.form['message']

        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO contact_messages (name, email, message) VALUES (%s, %s, %s)",
                    (name, email, message))
        mysql.connection.commit()
        cur.close()

        flash('Message sent successfully!', 'success')
        return redirect(url_for('contact_page'))

@app.route('/faq')
def faq():
    cur = mysql.connection.cursor()
    cur.execute("SELECT id, question, answer FROM faq")
    faqs = cur.fetchall()  # list of tuples
    cur.close()
    return render_template('faq.html', faqs=faqs)
# Admin dashboard - list all FAQs
@app.route('/admin/faqs')
def admin_faqs():
    cur = mysql.connection.cursor()
    cur.execute("SELECT id, question, answer FROM faq")
    faqs = cur.fetchall()
    cur.close()
    return render_template('admin_faqs.html', faqs=faqs)

# Admin - Add new FAQ
@app.route('/admin/add_faq', methods=['GET', 'POST'])
def add_faq():
    if request.method == 'POST':
        question = request.form['question']
        answer = request.form['answer']
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO faq (question, answer) VALUES (%s, %s)", (question, answer))
        mysql.connection.commit()
        cur.close()
        flash("FAQ added successfully!", "success")
        return redirect(url_for('admin_faqs'))
    return render_template('add_faq.html')

# Admin - Edit FAQ
@app.route('/admin/edit_faq/<int:id>', methods=['GET', 'POST'])
def edit_faq(id):
    cur = mysql.connection.cursor()
    if request.method == 'POST':
        question = request.form['question']
        answer = request.form['answer']
        cur.execute("UPDATE faq SET question=%s, answer=%s WHERE id=%s", (question, answer, id))
        mysql.connection.commit()
        cur.close()
        flash("FAQ updated successfully!", "success")
        return redirect(url_for('admin_faqs'))
    cur.execute("SELECT question, answer FROM faq WHERE id=%s", (id,))
    faq = cur.fetchone()
    cur.close()
    return render_template('edit_faq.html', faq=faq, faq_id=id)

# Admin - Delete FAQ
@app.route('/admin/delete_faq/<int:id>', methods=['POST'])
def delete_faq(id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM faq WHERE id=%s", (id,))
    mysql.connection.commit()
    cur.close()
    flash("FAQ deleted successfully!", "success")
    return redirect(url_for('admin_faqs'))
# ---------------- Admin Auth ----------------
@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM admin WHERE username=%s", (username,))
        admin = cursor.fetchone()
        cursor.close()

        if admin and verify_password(admin['password'], password):
            session['admin'] = admin['username']
            flash(f"Welcome {admin['username']}!", "success")
            return redirect(url_for('admin_dashboard'))
        else:
            flash("Invalid admin credentials!", "danger")

    return render_template('admin-login.html')

@app.route('/admin-logout')
def admin_logout():
    session.pop('admin', None)
    flash("You have been logged out!", "info")
    return redirect(url_for('admin_login'))

# ---------------- Admin Dashboard ----------------
@app.route('/admin_dashboard')
@login_required_admin
def admin_dashboard():
    return render_template('admin-dashboard.html', username=session['admin'])

# ---------------- Admin: Events Management ----------------
@app.route('/manage-events')
@login_required_admin
def manage_events():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM events ORDER BY date ASC")
    events = cursor.fetchall()
    cursor.close()
    return render_template('events-management.html', events=events)

@app.route('/add-event', methods=['GET', 'POST'])
@login_required_admin
def add_event():
    if request.method == 'POST':
        name = request.form['name'].strip()
        date = request.form['date']
        venue = request.form['venue'].strip()
        category = request.form['category'].strip()
        description = request.form.get('description', '').strip()
        fee = request.form.get('fee', '0').strip()

        cursor = mysql.connection.cursor()
        cursor.execute(
            "INSERT INTO events(name, date, venue, category, description, fee) VALUES (%s,%s,%s,%s,%s,%s)",
            (name, date, venue, category, description, fee)
        )
        mysql.connection.commit()
        cursor.close()
        flash("Event added successfully!", "success")
        return redirect(url_for('manage_events'))

    return render_template('add-event.html')

@app.route('/edit-event/<int:id>', methods=['GET', 'POST'])
@login_required_admin
def edit_event(id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM events WHERE id=%s", (id,))
    event = cursor.fetchone()

    if not event:
        cursor.close()
        flash("Event not found.", "danger")
        return redirect(url_for('manage_events'))

    if request.method == 'POST':
        name = request.form['name'].strip()
        date = request.form['date']
        venue = request.form['venue'].strip()
        category = request.form['category'].strip()
        description = request.form.get('description', '').strip()
        fee = request.form.get('fee', '0').strip()

        cursor.execute(
            "UPDATE events SET name=%s, date=%s, venue=%s, category=%s, description=%s, fee=%s WHERE id=%s",
            (name, date, venue, category, description, fee, id)
        )
        mysql.connection.commit()
        cursor.close()
        flash("Event updated successfully!", "success")
        return redirect(url_for('manage_events'))

    cursor.close()
    return render_template('edit-event.html', event=event)

@app.route('/delete-event/<int:id>')
@login_required_admin
def delete_event(id):
    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM events WHERE id=%s", (id,))
    mysql.connection.commit()
    cursor.close()
    flash("Event deleted successfully!", "success")
    return redirect(url_for('manage_events'))

# ---------------- Admin: Participants & Transactions ----------------
@app.route('/participants', methods=['GET', 'POST'])
@login_required_admin
def participants():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    base_query = """
        SELECT p.id, p.name, p.email, p.phone_number, p.selected_events,
               p.payment_method, p.payment_status
        FROM participants p
    """
    params = []
    where = []

    if request.method == 'POST':
        search_name = request.form.get('search_name', '').strip()
        filter_event = request.form.get('filter_event', '').strip()

        if search_name:
            where.append("(p.name LIKE %s OR p.email LIKE %s)")
            like = f"%{search_name}%"
            params.extend([like, like])
        if filter_event:
            where.append("FIND_IN_SET(%s, p.selected_events)")
            params.append(filter_event)

    if where:
        base_query += " WHERE " + " AND ".join(where)

    base_query += " ORDER BY p.id ASC"

    cursor.execute(base_query, tuple(params))
    participants_list = cursor.fetchall()

    # Fetch events for filter dropdown
    cursor.execute("SELECT DISTINCT name FROM events ORDER BY name ASC")
    events_list = [e['name'] for e in cursor.fetchall()]

    cursor.close()
    return render_template('participants.html', participants=participants_list, events_list=events_list)

@app.route('/delete-participant/<int:id>')
@login_required_admin
def delete_participant(id):
    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM participants WHERE id=%s", (id,))
    mysql.connection.commit()
    cursor.close()
    flash("Participant removed successfully!", "success")
    return redirect(url_for('participants'))


#----------------Transactions---------------
@app.route('/transactions', methods=['GET', 'POST'])
@login_required_admin
def transactions():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == 'POST' and 'update_status' in request.form:
        participant_id = request.form['participant_id']
        new_method = request.form['payment_method']
        new_status = request.form['payment_status']

        cursor.execute("""
            UPDATE participants 
            SET payment_method=%s, payment_status=%s 
            WHERE id=%s
        """, (new_method, new_status, participant_id))

        mysql.connection.commit()
        flash("Payment method and status updated!", "success")

    search_name = request.args.get('search_name', '').strip()
    filter_event = request.args.get('filter_event', '').strip()

    query = """
        SELECT p.id, p.name, p.email, p.phone_number, p.selected_events,
               p.payment_method, p.payment_status
        FROM participants p
    """
    conditions, params = [], []
    if search_name:
        conditions.append("(p.name LIKE %s OR p.email LIKE %s)")
        like = f"%{search_name}%"
        params.extend([like, like])
    if filter_event:
        conditions.append("FIND_IN_SET(%s, p.selected_events)")
        params.append(filter_event)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY p.id ASC"

    cursor.execute(query, tuple(params))
    transactions_list = cursor.fetchall()

    # Fetch events for filter dropdown
    cursor.execute("SELECT DISTINCT name FROM events ORDER BY name ASC")
    events_list = [e['name'] for e in cursor.fetchall()]

    cursor.close()
    return render_template('transactions.html',
                           transactions=transactions_list,
                           events_list=events_list,
                           search_name=search_name,
                           filter_event=filter_event)

# ---------------- Admin: QR Manager ----------------
@app.route('/upload-qr', methods=['GET', 'POST'])
@login_required_admin
def upload_qr():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == 'POST':
        file = request.files.get('qr_code')
        if file and file.filename:
            filename = secure_filename(file.filename)
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(save_path)

            cursor.execute("UPDATE settings SET qr_code_path=%s WHERE id=1", (filename,))
            mysql.connection.commit()
            flash("QR Code uploaded successfully!", "success")
        else:
            flash("No file selected!", "danger")
        return redirect(url_for('upload_qr'))

    cursor.execute("SELECT qr_code_path FROM settings WHERE id=1")
    qr = cursor.fetchone()
    qr_code = url_for('static', filename='uploads/' + qr['qr_code_path']) if qr and qr['qr_code_path'] else None
    cursor.close()

    return render_template('upload-qr.html', qr_code=qr_code)

# ---------------- Admin: Media Manager ----------------
@app.route('/media_manager')
@login_required_admin
def media_manager():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM media ORDER BY uploaded_at DESC")
    media_list = cursor.fetchall()
    cursor.close()
    return render_template('media_manager.html', media_list=media_list)

@app.route('/add_media', methods=['GET', 'POST'])
@login_required_admin
def add_media():
    if request.method == 'POST':
        filename = request.form['filename'].strip()
        filetype = request.form['filetype'].strip()  # 'image' or 'video'
        file = request.files.get('file')

        if file and filename and filetype in ('image', 'video'):
            secure_name = secure_filename(file.filename)
            folder = 'images' if filetype == 'image' else 'videos'
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], folder, secure_name)
            file.save(save_path)

            cursor = mysql.connection.cursor()
            cursor.execute("""
                INSERT INTO media(filename, filetype, filepath, uploaded_by)
                VALUES (%s, %s, %s, %s)
            """, (filename, filetype, f"uploads/{folder}/{secure_name}", session['admin']))
            mysql.connection.commit()
            cursor.close()
            flash("Media uploaded successfully!", "success")
            return redirect(url_for('media_manager'))
        else:
            flash("All fields are required and file type must be image/video.", "danger")

    return render_template('add_media.html')

@app.route('/edit_media/<int:id>', methods=['GET', 'POST'])
@login_required_admin
def edit_media(id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM media WHERE id=%s", (id,))
    media = cursor.fetchone()

    if not media:
        cursor.close()
        flash("Media not found.", "danger")
        return redirect(url_for('media_manager'))

    if request.method == 'POST':
        filename = request.form['filename'].strip()
        filetype = request.form['filetype'].strip()
        file = request.files.get('file')

        if file and file.filename:
            secure_name = secure_filename(file.filename)
            folder = 'images' if filetype == 'image' else 'videos'
            filepath = f'uploads/{folder}/{secure_name}'
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], folder, secure_name))
        else:
            filepath = media['filepath']  # keep old path

        cursor.execute(
            "UPDATE media SET filename=%s, filetype=%s, filepath=%s WHERE id=%s",
            (filename, filetype, filepath, id)
        )
        mysql.connection.commit()
        cursor.close()
        flash("Media updated successfully!", "success")
        return redirect(url_for('media_manager'))

    cursor.close()
    return render_template('edit_media.html', media=media)

@app.route('/delete_media/<int:id>')
@login_required_admin
def delete_media(id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("SELECT filepath FROM media WHERE id=%s", (id,))
    media = cursor.fetchone()

    if media:
        file_path = os.path.join('static', media['filepath'])
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            print("File delete error:", e)

    cursor.execute("DELETE FROM media WHERE id=%s", (id,))
    mysql.connection.commit()
    cursor.close()
    flash("Media deleted successfully!", "success")
    return redirect(url_for('media_manager'))

# ---------------- Coordinators ----------------
@app.route('/coordinators')
def coordinators():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("""
        SELECT c.*, e.name AS event_name
        FROM coordinators c
        JOIN events e ON c.event_id = e.id
    """)
    coordinators = cursor.fetchall()
    cursor.close()
    return render_template('coordinators.html', coordinators=coordinators)

@app.route('/add_coordinator', methods=['GET', 'POST'])
@login_required_admin
def add_coordinator():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM events ORDER BY name ASC")
    events = cursor.fetchall()

    if request.method == 'POST':
        name = request.form['name'].strip()
        email = request.form['email'].strip()
        mobile = request.form['mobile'].strip()
        event_id = request.form['event_id']

        cursor2 = mysql.connection.cursor()
        cursor2.execute(
            "INSERT INTO coordinators (name, email, mobile, event_id) VALUES (%s, %s, %s, %s)",
            (name, email, mobile, event_id)
        )
        mysql.connection.commit()
        cursor2.close()
        flash('Coordinator added successfully!', 'success')
        return redirect(url_for('coordinators'))

    cursor.close()
    return render_template('add-coordinator.html', events=events)

@app.route('/edit_coordinator/<int:id>', methods=['GET', 'POST'])
@login_required_admin
def edit_coordinator(id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM coordinators WHERE id=%s", (id,))
    coord = cursor.fetchone()

    if not coord:
        cursor.close()
        flash("Coordinator not found.", "danger")
        return redirect(url_for('coordinators'))

    cursor.execute("SELECT * FROM events ORDER BY name ASC")
    events = cursor.fetchall()

    if request.method == 'POST':
        name = request.form['name'].strip()
        email = request.form['email'].strip()
        mobile = request.form['mobile'].strip()
        event_id = request.form['event_id']

        cursor.execute("""
            UPDATE coordinators
            SET name=%s, email=%s, mobile=%s, event_id=%s
            WHERE id=%s
        """, (name, email, mobile, event_id, id))
        mysql.connection.commit()
        cursor.close()
        flash('Coordinator updated successfully!', 'success')
        return redirect(url_for('coordinators'))

    cursor.close()
    return render_template('edit-coordinator.html', coord=coord, events=events)

@app.route('/delete_coordinator/<int:id>')
@login_required_admin
def delete_coordinator(id):
    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM coordinators WHERE id=%s", (id,))
    mysql.connection.commit()
    cursor.close()
    flash('Coordinator deleted successfully!', 'success')
    return redirect(url_for('coordinators'))

#-----------------Contactus__________________
@app.route('/admin/contact_edit', methods=['GET', 'POST'])
def admin_contact_edit():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))

    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT * FROM contact_info WHERE id=1")
    contact = cur.fetchone()

    if request.method == 'POST':
        cur.execute("""
            UPDATE contact_info SET
                email=%s, phone=%s, office=%s,
                instagram=%s, linkedin=%s, youtube=%s
            WHERE id=1
        """, (
            request.form.get('email'),
            request.form.get('phone'),
            request.form.get('office'),
            request.form.get('instagram'),
            request.form.get('linkedin'),
            request.form.get('youtube')
        ))
        mysql.connection.commit()
        cur.close()
        flash("Contact info updated successfully!", "success")
        return redirect(url_for('admin_contact_edit'))

    cur.close()
    return render_template('Contact_Messages.html', contact=contact)
@app.route('/admin/contact_messages')
def contact_messages():
    if 'admin' not in session:
        flash("Please login as admin to view messages.", "danger")
        return redirect(url_for('admin_login'))

    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT * FROM contact_messages ORDER BY date_sent DESC")
    messages = cur.fetchall()
    cur.close()
    return render_template('contact_messages_admin.html', messages=messages)
@app.route('/admin/contact_messages')
def contact_messages_view():
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT * FROM contact_messages ORDER BY date_sent DESC")
    messages = cur.fetchall()
    cur.close()
    return render_template('contact_messages_admin.html', messages=messages)

# ---------------- Winners (fixed duplicate routes) ----------------


@app.route('/winners_list_admin')
@login_required_admin
def winners_list_admin():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM winners ORDER BY id ASC")
    winners = cursor.fetchall()
    cursor.close()
    return render_template('Winners.html', winners=winners)

# Public/User view
@app.route('/winners_list')
def winners_list():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM winners ORDER BY id ASC")
    winners = cursor.fetchall()
    cursor.close()
    return render_template('Winners_home.html', winners=winners)

@app.route('/add_winner', methods=['GET', 'POST'])
@login_required_admin
def add_winner():
    if request.method == 'POST':
        name = request.form['name'].strip()
        event_name = request.form['event_name'].strip()
        position = request.form['position'].strip()

        photo_file = request.files.get('photo')
        filename = None
        if photo_file and photo_file.filename:
            filename = secure_filename(photo_file.filename)
            upload_path = os.path.join('static', 'images', 'winners', filename)
            photo_file.save(upload_path)

        cursor = mysql.connection.cursor()
        cursor.execute("""
            INSERT INTO winners (name, photo, event_name, position)
            VALUES (%s, %s, %s, %s)
        """, (name, filename, event_name, position))
        mysql.connection.commit()
        cursor.close()
        flash("Winner added successfully!", "success")
        return redirect(url_for('winners_list_admin'))

    return render_template('add-winner.html')

@app.route('/edit_winner/<int:id>', methods=['GET', 'POST'])
@login_required_admin
def edit_winner(id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM winners WHERE id=%s", (id,))
    winner = cursor.fetchone()

    if not winner:
        cursor.close()
        flash("Winner not found.", "danger")
        return redirect(url_for('winners_list_admin'))

    if request.method == 'POST':
        name = request.form['name'].strip()
        event_name = request.form['event_name'].strip()
        position = request.form['position'].strip()

        photo_file = request.files.get('photo')
        if photo_file and photo_file.filename:
            filename = secure_filename(photo_file.filename)
            upload_path = os.path.join('static', 'images', 'winners', filename)
            photo_file.save(upload_path)
            cursor.execute("""
                UPDATE winners
                SET name=%s, photo=%s, event_name=%s, position=%s
                WHERE id=%s
            """, (name, filename, event_name, position, id))
        else:
            cursor.execute("""
                UPDATE winners
                SET name=%s, event_name=%s, position=%s
                WHERE id=%s
            """, (name, event_name, position, id))

        mysql.connection.commit()
        cursor.close()
        flash("Winner updated successfully!", "success")
        return redirect(url_for('winners_list_admin'))

    cursor.close()
    return render_template('edit-winner.html', winner=winner)

@app.route('/delete_winner/<int:id>')
@login_required_admin
def delete_winner(id):
    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM winners WHERE id=%s", (id,))
    mysql.connection.commit()
    cursor.close()
    flash("Winner deleted successfully!", "success")
    return redirect(url_for('winners_list_admin'))

# ---------------- Teams ----------------
@app.route('/team')
def team_view():
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Core Team
    cur.execute("""
            SELECT * FROM team
            WHERE role IN ('President','Co-President','Secretary','Treasurer')
            ORDER BY FIELD(role,'President','Co-President','Secretary','Treasurer')
        """)
    core_team = cur.fetchall()

    # Other Members (बाकी)
    cur.execute("""
            SELECT * FROM team
            WHERE role NOT IN (
                'President','Co-President','Secretary','Treasurer',
                'Vice Secretary',
                'Resource Management Head',
                'Technical Adviser Head',
                'Marketing & Advertisement Head',
                'Discipline Management Head',
                'Girl Representative Head',
                'Decoration Head'
            )
            ORDER BY name ASC
        """)
    other_members = cur.fetchall()

    # Fixed Special Positions
    fixed_roles = [
        "Vice Secretary",
        "Resource Management Head",
        "Technical Adviser Head",
        "Marketing & Advertisement Head",
        "Discipline Management Head",
        "Girl Representative Head",
        "Decoration Head"
    ]

    members = {}
    for role in fixed_roles:
        cur.execute("SELECT * FROM team WHERE role=%s LIMIT 1", (role,))
        member = cur.fetchone()  # None if not exists
        members[role] = member

    cur.close()
    return render_template(
        'team.html',
        core_team=core_team,
        other_members=other_members,
        fixed_roles=fixed_roles,
        members=members
    )

@app.route('/team_view_home')
def team_view_home():
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Core Team
    cur.execute("""
        SELECT * FROM team
        WHERE role IN ('President','Co-President','Secretary','Treasurer')
        ORDER BY FIELD(role,'President','Co-President','Secretary','Treasurer')
    """)
    core_team = cur.fetchall()

    # Other Members (बाकी)
    cur.execute("""
        SELECT * FROM team
        WHERE role NOT IN (
            'President','Co-President','Secretary','Treasurer',
            'Vice Secretary',
            'Resource Management Head',
            'Technical Adviser Head',
            'Marketing & Advertisement Head',
            'Discipline Management Head',
            'Girl Representative Head',
            'Decoration Head'
        )
        ORDER BY name ASC
    """)
    other_members = cur.fetchall()

    # Fixed Special Positions
    fixed_roles = [
        "Vice Secretary",
        "Resource Management Head",
        "Technical Adviser Head",
        "Marketing & Advertisement Head",
        "Discipline Management Head",
        "Girl Representative Head",
        "Decoration Head"
    ]

    members = {}
    for role in fixed_roles:
        cur.execute("SELECT * FROM team WHERE role=%s LIMIT 1", (role,))
        member = cur.fetchone()  # None if not exists
        members[role] = member

    cur.close()
    return render_template(
        'team_view_home.html',
        core_team=core_team,
        other_members=other_members,
        fixed_roles=fixed_roles,
        members=members
    )




@app.route('/team_admin')
@login_required_admin
def admin_team():
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Core Team (Fixed 4 roles)
    cur.execute("""
        SELECT * FROM team
        WHERE role IN ('President','Co-President','Secretary','Treasurer')
        ORDER BY FIELD(role,'President','Co-President','Secretary','Treasurer')
    """)
    core_team = cur.fetchall()

    # Special Heads (Fixed 7 roles)
    special_heads_list = [
        'Vice Secretary',
        'Resource Management Head',
        'Technical Adviser Head',
        'Marketing & Advertisement Head',
        'Discipline Management Head',
        'Girl Representative Head',
        'Decoration Head'
    ]
    cur.execute("""
        SELECT * FROM team
        WHERE role IN (%s,%s,%s,%s,%s,%s,%s)
        ORDER BY FIELD(role,
            'Vice Secretary',
            'Resource Management Head',
            'Technical Adviser Head',
            'Marketing & Advertisement Head',
            'Discipline Management Head',
            'Girl Representative Head',
            'Decoration Head'
        )
    """, tuple(special_heads_list))
    special_heads = cur.fetchall()

    # Other Members (exclude core + special heads)
    cur.execute("""
        SELECT * FROM team
        WHERE role NOT IN (
            'President','Co-President','Secretary','Treasurer',
            'Vice Secretary',
            'Resource Management Head',
            'Technical Adviser Head',
            'Marketing & Advertisement Head',
            'Discipline Management Head',
            'Girl Representative Head',
            'Decoration Head'
        )
        ORDER BY name ASC
    """)
    other_members = cur.fetchall()

    cur.close()
    return render_template(
        'admin_team.html',
        core_team=core_team,
        special_heads=special_heads,
        other_members=other_members
    )



@app.route('/admin/team/add', methods=['GET', 'POST'])
@login_required_admin
def add_team_member():
    if request.method == 'POST':
        name = request.form['name'].strip()
        role = request.form['role'].strip()
        category = request.form['category']  # core / other
        email = request.form['phone_number'].strip()
        photo_file = request.files.get('photo')

        filename = None
        if photo_file and photo_file.filename:
            filename = secure_filename(photo_file.filename)
            photo_file.save(os.path.join(app.config['UPLOAD_FOLDER'], 'team', filename))

        cursor = mysql.connection.cursor()
        phone_number = request.form['phone_number'].strip()
        cursor.execute(
            "INSERT INTO team (name, role, phone_number, category, photo) VALUES (%s, %s, %s, %s, %s)",
            (name, role, phone_number, category, filename)
        )

        mysql.connection.commit()
        cursor.close()
        flash("Member added successfully!", "success")
        return redirect(url_for('admin_team'))

    return render_template('add_team_member.html')


@app.route('/admin/team/edit/<int:id>', methods=['GET', 'POST'])
@login_required_admin
def edit_team_member(id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM team WHERE id=%s", (id,))
    member = cursor.fetchone()

    if not member:
        cursor.close()
        flash("Member not found.", "danger")
        return redirect(url_for('admin_team'))

    if request.method == 'POST':
        name = request.form['name'].strip()
        role = request.form['role'].strip()
        category = request.form['category']  # core / other
        phone_number = request.form['phone_number'].strip()
        photo_file = request.files.get('photo')

        # Keep old photo if new not uploaded
        filename = member['photo']
        if photo_file and photo_file.filename:
            filename = secure_filename(photo_file.filename)
            photo_path = os.path.join(app.config['UPLOAD_FOLDER'], 'team', filename)
            os.makedirs(os.path.dirname(photo_path), exist_ok=True)  # ensure folder exists
            photo_file.save(photo_path)

        # ✅ UPDATE instead of INSERT
        cursor.execute("""
            UPDATE team
            SET name=%s, role=%s, phone_number=%s, category=%s, photo=%s
            WHERE id=%s
        """, (name, role, phone_number, category, filename, id))

        mysql.connection.commit()
        cursor.close()

        flash("✅ Member updated successfully!", "success")
        return redirect(url_for('admin_team'))

    cursor.close()
    return render_template('edit_team_member.html', member=member)


@app.route('/admin/team/delete/<int:id>')
@login_required_admin
def delete_team_member(id):
    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM team WHERE id=%s", (id,))
    mysql.connection.commit()
    cursor.close()
    flash("Member deleted successfully!", "success")
    return redirect(url_for('admin_team'))

# ---------------- User Auth ----------------

@app.route('/register_event', methods=['GET', 'POST'])
def register_event():
    if request.method == 'POST':
        fullname = request.form['fullname'].strip()
        email = request.form['email'].strip()
        username = request.form['username'].strip()
        branch = request.form['branch'].strip()
        password = request.form['password']

        # Hash the password
        from werkzeug.security import generate_password_hash
        hashed = generate_password_hash(password)

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # Check for existing email
        cursor.execute("SELECT * FROM user_signup WHERE email_address = %s", (email,))
        existing_email = cursor.fetchone()
        if existing_email:
            flash("Email already registered! Try logging in.", "danger")
            cursor.close()
            return redirect(url_for('register_event'))

        # Check for existing username (optional)
        cursor.execute("SELECT * FROM user_signup WHERE user_name = %s", (username,))
        existing_username = cursor.fetchone()
        if existing_username:
            flash("Username already taken! Choose another.", "danger")
            cursor.close()
            return redirect(url_for('register_event'))

        # Insert new user
        cursor.execute("""
            INSERT INTO user_signup(name, email_address, user_name, branch, password)
            VALUES (%s, %s, %s, %s, %s)
        """, (fullname, email, username, branch, hashed))
        mysql.connection.commit()
        cursor.close()

        flash("✅ Registration Successful!", "success")
        return redirect(url_for('user_dashboard'))

    return render_template("register.html")


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login_id = request.form['username'].strip()  # username or email
        password = request.form['password']

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("""
            SELECT * FROM user_signup 
            WHERE (email_address = %s OR user_name = %s)
        """, (login_id, login_id))
        user = cursor.fetchone()
        cursor.close()

        if user and verify_password(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['user_name']
            session['branch'] = user['branch']
            session['email'] = user['email_address']
            session['full_name'] = user['name']
            return redirect(url_for('user_dashboard'))

        flash('Invalid username or password', 'danger')

    return render_template('user-login.html')

@app.route('/logout')
def logout():
    # Optional: mark user logged out in DB if you track that flag
    if 'email' in session:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        try:
            cursor.execute("UPDATE user_signup SET is_logged_in = 0 WHERE email_address = %s", (session['email'],))
            cursor.connection.commit()
        except Exception:
            pass
        finally:
            cursor.close()

    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))

# ---------------- User Dashboard & Profile ----------------
@app.route('/dashboard')
@login_required_user
def user_dashboard():
    user = {
        "username": session['username'],
        "full_name": session['full_name'],
        "email": session['email'],
        "branch": session['branch']
    }
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM events ORDER BY date ASC")
    events_list = cursor.fetchall()
    cursor.close()
    return render_template('user-dashboard.html', user=user, events_list=events_list)

@app.route('/user_edit', methods=['GET'])
@login_required_user
def user_edit():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM user_signup WHERE user_name=%s", (session['username'],))
    user = cursor.fetchone()
    cursor.close()

    if user is None:
        flash("User not found!", "danger")
        return redirect(url_for('user_dashboard'))

    return render_template('edit-profileuser.html', user=user)

@app.route('/update_profile', methods=['POST'])
@login_required_user
def update_profile():
    name = request.form['name'].strip()
    email = request.form['email'].strip()
    branch = request.form['branch'].strip()
    username = request.form['username'].strip()

    cursor = mysql.connection.cursor()
    cursor.execute("""
        UPDATE user_signup
        SET name=%s, email_address=%s, branch=%s, user_name=%s
        WHERE user_name=%s
    """, (name, email, branch, username, session['username']))
    mysql.connection.commit()
    cursor.close()

    session['username'] = username
    session['email'] = email
    session['full_name'] = name
    session['branch'] = branch

    flash("Profile updated successfully!", "success")
    return redirect(url_for('user_dashboard'))

# ---------------- Event Registration (user) ----------------
@app.route('/event-registration', methods=['GET', 'POST'])
@login_required_user
def event_registration():
    full_name = session['full_name']
    email = session['email']

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM events ORDER BY date ASC")
    events_list = cursor.fetchall()

    cursor.execute("SELECT qr_code_path FROM settings WHERE id=1")
    qr = cursor.fetchone()
    qr_code = url_for('static', filename='uploads/' + qr['qr_code_path']) if qr and qr['qr_code_path'] else None

    if request.method == 'POST':
        phone_number = request.form['phone_number'].strip()
        selected_events = request.form.getlist('selected_events')
        payment_method = request.form['payment_method']

        # Convert list to comma separated string
        selected_events_str = ', '.join(selected_events)

        # Insert single row for participant
        cursor.execute("""
            INSERT INTO participants(full_name, email, phone_number, selected_events, payment_method, payment_status)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (full_name, email, phone_number, selected_events_str, payment_method, 'Pending'))

        mysql.connection.commit()
        cursor.close()

        flash("Registered successfully!", "success")
        return redirect(url_for('user_dashboard'))

    cursor.close()
    return render_template('event_registration.html',
                           full_name=full_name,
                           email=email,
                           events_list=events_list,
                           qr_code=qr_code)

# ---------------- Coordinators (user views) ----------------
@app.route('/event_coordinators')
@login_required_user
def event_coordinators():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("""
        SELECT c.name AS coordinator_name,
               c.email AS coordinator_email,
               c.mobile AS coordinator_mobile,
               e.name AS event_name
        FROM coordinators c
        JOIN events e ON c.event_id = e.id
        ORDER BY e.name ASC
    """)
    coordinators = cursor.fetchall()
    cursor.close()
    return render_template('event_coordinators.html', coordinators=coordinators)

@app.route('/u_coordinators')
@login_required_user
def u_coordinators():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("""
        SELECT c.name AS coordinator_name,
               c.email AS coordinator_email,
               c.mobile AS coordinator_mobile,
               e.name AS event_name
        FROM coordinators c
        JOIN events e ON c.event_id = e.id
        ORDER BY e.name ASC
    """)
    coordinators = cursor.fetchall()
    cursor.close()
    return render_template('u_coordinators.html', coordinators=coordinators)

# ---------------- Winners (public lists) ----------------
@app.route('/last_year_winners')
def last_year_winners():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM winners ORDER BY id ASC")
    winners = cursor.fetchall()
    cursor.close()
    return render_template('winner_s.html', winners=winners)

@app.route('/year_winners')
def year_winners():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM winners ORDER BY id ASC")
    winners = cursor.fetchall()
    cursor.close()
    return render_template('winners_home.html', winners=winners)


@app.route('/my-events')
@login_required_user
def my_events():
    user_email = session['email']  # Logged-in user email
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("""
        SELECT selected_events, payment_status, payment_method 
        FROM participants
        WHERE email=%s
    """, (user_email,))

    user_events = cursor.fetchall()
    cursor.close()

    return render_template('my_events.html', user_events=user_events)


# ---------------- App entry ----------------
if __name__ == '__main__':
    app.run(debug=True)
