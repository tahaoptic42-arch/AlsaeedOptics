import os
import sqlite3
from pathlib import Path
from functools import wraps
from urllib.parse import quote

from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "products.db"
UPLOAD_DIR = BASE_DIR / "static" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-before-online-hosting")
app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

def db():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection

def init_db():
    with db() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS admin (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )""")
        con.execute("""CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name_en TEXT NOT NULL,
            name_ur TEXT NOT NULL,
            price TEXT NOT NULL,
            description_en TEXT DEFAULT '',
            description_ur TEXT DEFAULT '',
            symbol TEXT DEFAULT '👓',
            image TEXT DEFAULT ''
        )""")
        count = con.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        if count == 0:
            con.executemany("""INSERT INTO products
                (name_en,name_ur,price,description_en,description_ur,symbol)
                VALUES (?,?,?,?,?,?)""", [
                ("Classic Frame", "کلاسک فریم", "Rs. 1,500", "A simple everyday frame.", "روزمرہ استعمال کے لیے سادہ فریم۔", "👓"),
                ("Sun Glasses", "سن گلاسز", "Rs. 2,000", "Stylish sunglasses for outdoor use.", "باہر استعمال کے لیے خوبصورت سن گلاسز۔", "🕶️"),
                ("Kids Frame", "بچوں کے فریم", "Rs. 1,200", "Comfortable frame for kids.", "بچوں کے لیے آرام دہ فریم۔", "🤓"),
            ])

def admin_exists():
    with db() as con:
        return con.execute("SELECT 1 FROM admin LIMIT 1").fetchone() is not None

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin_id"):
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/")
def home():
    with db() as con:
        products = con.execute("SELECT * FROM products ORDER BY id DESC").fetchall()
    return render_template("index.html", products=products,
                           whatsapp_number=os.environ.get("SHOP_WHATSAPP", "923001234567"))

@app.route("/admin/setup", methods=["GET", "POST"])
def setup():
    if admin_exists():
        return redirect(url_for("login"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if len(username) < 3 or len(password) < 10:
            flash("Username must be 3+ characters and password at least 10 characters.")
        else:
            try:
                with db() as con:
                    con.execute("INSERT INTO admin(username,password_hash) VALUES (?,?)",
                                (username, generate_password_hash(password)))
                flash("Admin account created. Please sign in.")
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                flash("That username is already in use.")
    return render_template("admin_setup.html")

@app.route("/admin/login", methods=["GET", "POST"])
def login():
    if not admin_exists():
        return redirect(url_for("setup"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        with db() as con:
            admin = con.execute("SELECT * FROM admin WHERE username=?", (username,)).fetchone()
        if admin and check_password_hash(admin["password_hash"], password):
            session.clear()
            session["admin_id"] = admin["id"]
            session["admin_name"] = admin["username"]
            return redirect(url_for("dashboard"))
        flash("Incorrect username or password.")
    return render_template("login.html")

@app.route("/admin/logout", methods=["POST"])
@login_required
def logout():
    session.clear()
    return redirect(url_for("home"))

@app.route("/admin")
@login_required
def dashboard():
    with db() as con:
        products = con.execute("SELECT * FROM products ORDER BY id DESC").fetchall()
    return render_template("dashboard.html", products=products)

@app.route("/admin/product/new", methods=["GET", "POST"])
@app.route("/admin/product/<int:product_id>/edit", methods=["GET", "POST"])
@login_required
def product_form(product_id=None):
    product = None
    if product_id is not None:
        with db() as con:
            product = con.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
        if product is None:
            abort(404)
    if request.method == "POST":
        fields = {
            "name_en": request.form.get("name_en", "").strip(),
            "name_ur": request.form.get("name_ur", "").strip(),
            "price": request.form.get("price", "").strip(),
            "description_en": request.form.get("description_en", "").strip(),
            "description_ur": request.form.get("description_ur", "").strip(),
            "symbol": request.form.get("symbol", "👓").strip() or "👓",
        }
        if not fields["name_en"] or not fields["name_ur"] or not fields["price"]:
            flash("Please fill in both product names and the price.")
            return render_template("product_form.html", product=product)
        image_name = product["image"] if product else ""
        upload = request.files.get("image")
        if upload and upload.filename:
            if not allowed_file(upload.filename):
                flash("Image must be PNG, JPG, JPEG, or WEBP.")
                return render_template("product_form.html", product=product)
            safe_name = secure_filename(upload.filename)
            unique_name = f"{os.urandom(8).hex()}_{safe_name}"
            upload.save(UPLOAD_DIR / unique_name)
            image_name = unique_name
        with db() as con:
            if product:
                con.execute("""UPDATE products SET name_en=?,name_ur=?,price=?,
                    description_en=?,description_ur=?,symbol=?,image=? WHERE id=?""",
                    (*fields.values(), image_name, product_id))
            else:
                con.execute("""INSERT INTO products
                    (name_en,name_ur,price,description_en,description_ur,symbol,image)
                    VALUES (?,?,?,?,?,?,?)""", (*fields.values(), image_name))
        flash("Product saved.")
        return redirect(url_for("dashboard"))
    return render_template("product_form.html", product=product)

@app.route("/admin/product/<int:product_id>/delete", methods=["POST"])
@login_required
def delete_product(product_id):
    with db() as con:
        product = con.execute("SELECT image FROM products WHERE id=?", (product_id,)).fetchone()
        if product is None:
            abort(404)
        con.execute("DELETE FROM products WHERE id=?", (product_id,))
    if product["image"]:
        try:
            (UPLOAD_DIR / product["image"]).unlink(missing_ok=True)
        except OSError:
            pass
    flash("Product deleted.")
    return redirect(url_for("dashboard"))

init_db()

if __name__ == "__main__":
    # Local development only. Deploy with a production WSGI server for public hosting.
    app.run(host="127.0.0.1", port=5000, debug=True)
