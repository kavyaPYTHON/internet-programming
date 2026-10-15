from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory, abort
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
from datetime import date, timedelta
from pathlib import Path
import sqlite3
import os

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-development-secret")
app.config["UPLOAD_FOLDER"] = str(UPLOAD_DIR)
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024
ALLOWED_EXTENSIONS = {"pdf", "doc", "docx", "ppt", "pptx", "txt"}

def get_db():
    conn = sqlite3.connect(BASE_DIR / "library.db")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    with get_db() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'student',
            phone TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            isbn TEXT DEFAULT '',
            category TEXT DEFAULT '',
            year INTEGER,
            total_copies INTEGER NOT NULL DEFAULT 1,
            available_copies INTEGER NOT NULL DEFAULT 1,
            description TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS borrowings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            book_id INTEGER NOT NULL REFERENCES books(id),
            issue_date TEXT NOT NULL,
            due_date TEXT NOT NULL,
            return_date TEXT,
            fine REAL NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'issued'
        );
        CREATE TABLE IF NOT EXISTS materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            subject TEXT DEFAULT '',
            year TEXT NOT NULL,
            semester TEXT NOT NULL,
            filename TEXT NOT NULL,
            uploaded_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """)
        # Demo admin is created only if no account with this email exists.
        if not db.execute("SELECT id FROM users WHERE email=?", ("admin@library.local",)).fetchone():
            db.execute(
                "INSERT INTO users (name,email,password_hash,role) VALUES (?,?,?,?)",
                ("Library Admin", "admin@library.local",
                 generate_password_hash("Admin@123"), "admin")
            )

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in first.", "warning")
            return redirect(url_for("login"))
        if session.get("role") != "admin":
            abort(403)
        return fn(*args, **kwargs)
    return wrapper

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@app.context_processor
def inject_user():
    return {"current_user": session.get("user_name"), "current_role": session.get("role")}

@app.route("/")
def index():
    q = request.args.get("q", "").strip()
    with get_db() as db:
        if q:
            books = db.execute("""SELECT * FROM books WHERE title LIKE ? OR author LIKE ?
                OR isbn LIKE ? OR category LIKE ? ORDER BY title""",
                tuple([f"%{q}%"] * 4)).fetchall()
        else:
            books = db.execute("SELECT * FROM books ORDER BY title LIMIT 30").fetchall()
    return render_template("index.html", books=books, q=q)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        phone = request.form.get("phone", "").strip()
        if not name or not email or len(password) < 8:
            flash("Enter your name/email and a password of at least 8 characters.", "danger")
            return render_template("register.html")
        try:
            with get_db() as db:
                db.execute("INSERT INTO users (name,email,password_hash,phone) VALUES (?,?,?,?)",
                           (name, email, generate_password_hash(password), phone))
            flash("Registration successful. You can now log in.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("That email address is already registered.", "danger")
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        with get_db() as db:
            user = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["role"] = user["role"]
            flash(f"Welcome, {user['name']}!", "success")
            return redirect(url_for("admin_dashboard" if user["role"] == "admin" else "student_dashboard"))
        flash("Invalid email or password.", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))

@app.route("/book/<int:book_id>")
def book_detail(book_id):
    with get_db() as db:
        book = db.execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone()
    if not book:
        abort(404)
    return render_template("book_detail.html", book=book)

@app.route("/student")
@login_required
def student_dashboard():
    if session.get("role") == "admin":
        return redirect(url_for("admin_dashboard"))
    with get_db() as db:
        borrowings = db.execute("""SELECT br.*, b.title, b.author FROM borrowings br
            JOIN books b ON b.id=br.book_id WHERE br.user_id=? ORDER BY br.id DESC""",
            (session["user_id"],)).fetchall()
        user = db.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
        materials = db.execute("SELECT * FROM materials ORDER BY year, semester, title").fetchall()
    today = date.today().isoformat()
    current_fine = sum(float(b["fine"]) for b in borrowings if b["status"] == "issued")
    return render_template("student.html", borrowings=borrowings, user=user, materials=materials,
                           today=today, current_fine=current_fine)

@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    with get_db() as db:
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            phone = request.form.get("phone", "").strip()
            if not name:
                flash("Name cannot be empty.", "danger")
            else:
                db.execute("UPDATE users SET name=?, phone=? WHERE id=?",
                           (name, phone, session["user_id"]))
                session["user_name"] = name
                flash("Profile updated.", "success")
                return redirect(url_for("profile"))
        user = db.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
    return render_template("profile.html", user=user)

@app.route("/admin")
@admin_required
def admin_dashboard():
    with get_db() as db:
        counts = {
            "books": db.execute("SELECT COUNT(*) FROM books").fetchone()[0],
            "students": db.execute("SELECT COUNT(*) FROM users WHERE role='student'").fetchone()[0],
            "issued": db.execute("SELECT COUNT(*) FROM borrowings WHERE status='issued'").fetchone()[0],
            "materials": db.execute("SELECT COUNT(*) FROM materials").fetchone()[0],
        }
        borrowings = db.execute("""SELECT br.*, u.name AS student_name, b.title AS book_title
            FROM borrowings br JOIN users u ON u.id=br.user_id JOIN books b ON b.id=br.book_id
            ORDER BY br.id DESC LIMIT 12""").fetchall()
    return render_template("admin.html", counts=counts, borrowings=borrowings)

@app.route("/admin/books")
@admin_required
def manage_books():
    q = request.args.get("q", "").strip()
    with get_db() as db:
        if q:
            books = db.execute("SELECT * FROM books WHERE title LIKE ? OR author LIKE ? ORDER BY title",
                               (f"%{q}%", f"%{q}%")).fetchall()
        else:
            books = db.execute("SELECT * FROM books ORDER BY title").fetchall()
    return render_template("manage_books.html", books=books, q=q)

@app.route("/admin/books/add", methods=["GET", "POST"])
@admin_required
def add_book():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        author = request.form.get("author", "").strip()
        try:
            copies = max(1, int(request.form.get("total_copies", "1")))
            year = int(request.form.get("year")) if request.form.get("year") else None
        except ValueError:
            flash("Year and copies must be valid numbers.", "danger")
            return render_template("book_form.html", book=None)
        if not title or not author:
            flash("Title and author are required.", "danger")
            return render_template("book_form.html", book=None)
        with get_db() as db:
            db.execute("""INSERT INTO books (title,author,isbn,category,year,total_copies,available_copies,description)
                VALUES (?,?,?,?,?,?,?,?)""",
                (title, author, request.form.get("isbn","").strip(),
                 request.form.get("category","").strip(), year, copies, copies,
                 request.form.get("description","").strip()))
        flash("Book added.", "success")
        return redirect(url_for("manage_books"))
    return render_template("book_form.html", book=None)

@app.route("/admin/books/<int:book_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_book(book_id):
    with get_db() as db:
        book = db.execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone()
        if not book:
            abort(404)
        if request.method == "POST":
            title = request.form.get("title", "").strip()
            author = request.form.get("author", "").strip()
            try:
                total = max(1, int(request.form.get("total_copies", "1")))
                year = int(request.form.get("year")) if request.form.get("year") else None
            except ValueError:
                flash("Year and copies must be valid numbers.", "danger")
                return render_template("book_form.html", book=book)
            if total < book["total_copies"] - book["available_copies"]:
                flash("Total copies cannot be lower than the number currently issued.", "danger")
                return render_template("book_form.html", book=book)
            available = total - (book["total_copies"] - book["available_copies"])
            db.execute("""UPDATE books SET title=?,author=?,isbn=?,category=?,year=?,total_copies=?,
                available_copies=?,description=? WHERE id=?""",
                (title, author, request.form.get("isbn","").strip(), request.form.get("category","").strip(),
                 year, total, available, request.form.get("description","").strip(), book_id))
        else:
            return render_template("book_form.html", book=book)
    flash("Book updated.", "success")
    return redirect(url_for("manage_books"))

@app.route("/admin/books/<int:book_id>/delete", methods=["POST"])
@admin_required
def delete_book(book_id):
    with get_db() as db:
        active = db.execute("SELECT COUNT(*) FROM borrowings WHERE book_id=? AND status='issued'", (book_id,)).fetchone()[0]
        if active:
            flash("Cannot delete a book while copies are issued.", "danger")
        else:
            db.execute("DELETE FROM books WHERE id=?", (book_id,))
            flash("Book deleted.", "success")
    return redirect(url_for("manage_books"))

@app.route("/admin/issue", methods=["GET", "POST"])
@admin_required
def issue_book():
    with get_db() as db:
        students = db.execute("SELECT id,name,email FROM users WHERE role='student' ORDER BY name").fetchall()
        books = db.execute("SELECT id,title,available_copies FROM books WHERE available_copies>0 ORDER BY title").fetchall()
        if request.method == "POST":
            try:
                user_id = int(request.form.get("user_id", "0"))
                book_id = int(request.form.get("book_id", "0"))
            except ValueError:
                flash("Select a student and book.", "danger")
                return redirect(url_for("issue_book"))
            student = db.execute("SELECT id FROM users WHERE id=? AND role='student'", (user_id,)).fetchone()
            book = db.execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone()
            active_count = db.execute("SELECT COUNT(*) FROM borrowings WHERE user_id=? AND status='issued'", (user_id,)).fetchone()[0]
            if not student or not book or book["available_copies"] < 1:
                flash("Student or available book is invalid.", "danger")
            elif active_count >= 5:
                flash("This student already has 5 active loans.", "danger")
            else:
                issue = date.today()
                due = issue + timedelta(days=14)
                db.execute("INSERT INTO borrowings (user_id,book_id,issue_date,due_date) VALUES (?,?,?,?)",
                           (user_id, book_id, issue.isoformat(), due.isoformat()))
                db.execute("UPDATE books SET available_copies=available_copies-1 WHERE id=?", (book_id,))
                flash(f"Book issued. Due date: {due.isoformat()}", "success")
                return redirect(url_for("admin_dashboard"))
    return render_template("issue_book.html", students=students, books=books)

@app.route("/admin/return/<int:borrowing_id>", methods=["POST"])
@admin_required
def return_book(borrowing_id):
    with get_db() as db:
        loan = db.execute("SELECT * FROM borrowings WHERE id=? AND status='issued'", (borrowing_id,)).fetchone()
        if not loan:
            flash("Active borrowing record not found.", "danger")
        else:
            today = date.today()
            due = date.fromisoformat(loan["due_date"])
            fine = max(0, (today - due).days) * 5.0  # ₹5 per overdue day
            db.execute("UPDATE borrowings SET return_date=?, status='returned', fine=? WHERE id=?",
                       (today.isoformat(), fine, borrowing_id))
            db.execute("UPDATE books SET available_copies=available_copies+1 WHERE id=?", (loan["book_id"],))
            flash(f"Book returned. Fine calculated: ₹{fine:.2f}", "success")
    return redirect(request.referrer or url_for("admin_dashboard"))

@app.route("/admin/materials", methods=["GET", "POST"])
@admin_required
def manage_materials():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        subject = request.form.get("subject", "").strip()
        year = request.form.get("year", "").strip()
        semester = request.form.get("semester", "").strip()
        upload = request.files.get("file")
        if not title or not year or not semester or not upload or not upload.filename:
            flash("Complete all required fields and choose a file.", "danger")
        elif not allowed_file(upload.filename):
            flash("Allowed files: PDF, DOC, DOCX, PPT, PPTX, TXT.", "danger")
        else:
            filename = secure_filename(upload.filename)
            stored = f"{date.today().strftime('%Y%m%d')}_{os.urandom(4).hex()}_{filename}"
            upload.save(UPLOAD_DIR / stored)
            with get_db() as db:
                db.execute("INSERT INTO materials (title,subject,year,semester,filename) VALUES (?,?,?,?,?)",
                           (title, subject, year, semester, stored))
            flash("Study material uploaded.", "success")
            return redirect(url_for("manage_materials"))
    with get_db() as db:
        materials = db.execute("SELECT * FROM materials ORDER BY year,semester,title").fetchall()
    return render_template("manage_materials.html", materials=materials)

@app.route("/materials/<int:material_id>/download")
@login_required
def download_material(material_id):
    with get_db() as db:
        material = db.execute("SELECT * FROM materials WHERE id=?", (material_id,)).fetchone()
    if not material:
        abort(404)
    return send_from_directory(app.config["UPLOAD_FOLDER"], material["filename"], as_attachment=True)

@app.route("/admin/materials/<int:material_id>/delete", methods=["POST"])
@admin_required
def delete_material(material_id):
    with get_db() as db:
        material = db.execute("SELECT * FROM materials WHERE id=?", (material_id,)).fetchone()
        if material:
            (UPLOAD_DIR / material["filename"]).unlink(missing_ok=True)
            db.execute("DELETE FROM materials WHERE id=?", (material_id,))
            flash("Material deleted.", "success")
    return redirect(url_for("manage_materials"))

@app.route("/admin/students")
@admin_required
def students():
    with get_db() as db:
        users = db.execute("""SELECT u.*, (SELECT COUNT(*) FROM borrowings br
            WHERE br.user_id=u.id AND br.status='issued') AS active_loans
            FROM users u WHERE role='student' ORDER BY name""").fetchall()
    return render_template("students.html", users=users)

@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        message = request.form.get("message", "").strip()
        if name and email and message:
            with get_db() as db:
                db.execute("INSERT INTO messages (name,email,message) VALUES (?,?,?)", (name,email,message))
            flash("Your message has been sent to the library team.", "success")
            return redirect(url_for("contact"))
        flash("Please complete all fields.", "danger")
    return render_template("contact.html")

@app.errorhandler(403)
def forbidden(_):
    return render_template("error.html", code=403, message="You do not have permission to view this page."), 403

@app.errorhandler(404)
def not_found(_):
    return render_template("error.html", code=404, message="The page or record was not found."), 404

init_db()

if __name__ == "__main__":
    app.run(debug=True)
