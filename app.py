from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
from functools import wraps

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
UPLOAD_FOLDER = os.path.join(app.root_path, "static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

db = SQLAlchemy(app)

# ---------- Database Models ----------
class Vendor(db.Model):
    __tablename__ = "vendors"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    business_name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    landmark = db.Column(db.String(255), nullable=True)
    address1 = db.Column(db.String(255), nullable=True)
    address2 = db.Column(db.String(255), nullable=True)
    pincode = db.Column(db.String(20), nullable=True)
    maps_link = db.Column(db.String(500), nullable=True, default="https://maps.google.com")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    products = db.relationship("Product", backref="vendor", lazy=True, cascade="all, delete-orphan")

class Customer(db.Model):
    __tablename__ = "customers"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Product(db.Model):
    __tablename__ = "products"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(255), nullable=True)
    image_filename = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    vendor_id = db.Column(db.Integer, db.ForeignKey("vendors.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ---------- Helpers ----------
def vendor_login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "vendor_id" not in session:
            return redirect(url_for("vendor_login"))
        return f(*args, **kwargs)
    return wrapper

def customer_login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "customer_id" not in session:
            return redirect(url_for("customer_login"))
        return f(*args, **kwargs)
    return wrapper

def init_db():
    with app.app_context():
        db.create_all()
        # Add columns if they do not exist
        from sqlalchemy import text
        with db.engine.connect() as conn:
            try:
                cols_vendor = [row[1] for row in conn.execute(text("PRAGMA table_info(vendors)")).fetchall()]
                if "phone" not in cols_vendor:
                    conn.execute(text("ALTER TABLE vendors ADD COLUMN phone VARCHAR(20)"))
                if "landmark" not in cols_vendor:
                    conn.execute(text("ALTER TABLE vendors ADD COLUMN landmark VARCHAR(255)"))
                if "address1" not in cols_vendor:
                    conn.execute(text("ALTER TABLE vendors ADD COLUMN address1 VARCHAR(255)"))
                if "address2" not in cols_vendor:
                    conn.execute(text("ALTER TABLE vendors ADD COLUMN address2 VARCHAR(255)"))
                if "pincode" not in cols_vendor:
                    conn.execute(text("ALTER TABLE vendors ADD COLUMN pincode VARCHAR(20)"))
                if "maps_link" not in cols_vendor:
                    conn.execute(text("ALTER TABLE vendors ADD COLUMN maps_link VARCHAR(500) DEFAULT 'https://maps.google.com'"))
                
                cols_cust = [row[1] for row in conn.execute(text("PRAGMA table_info(customers)")).fetchall()]
                if "phone" not in cols_cust:
                    conn.execute(text("ALTER TABLE customers ADD COLUMN phone VARCHAR(20)"))
                conn.commit()
            except Exception as e:
                print("DB Migration notice:", e)

        # Pre-seed demo vendor Arjun Mehta & sample products if not already seeded
        try:
            demo_vendor = Vendor.query.filter_by(email="arjun@example.com").first()
            if not demo_vendor:
                demo_vendor = Vendor(
                    name="Arjun Mehta",
                    email="arjun@example.com",
                    business_name="Fresh Farm Groceries",
                    password_hash=generate_password_hash("password123"),
                    phone="9876543210",
                    landmark="Near City Mall",
                    address1="Shop 12, Market Road",
                    pincode="400001",
                    maps_link="https://maps.google.com"
                )
                db.session.add(demo_vendor)
                db.session.commit()

            if Product.query.count() == 0 and demo_vendor:
                p1 = Product(name="Organic Tomatoes", price=45.0, description="Fresh organic tomatoes, 1 kg", vendor_id=demo_vendor.id)
                p2 = Product(name="Green Spinach", price=30.0, description="Fresh green spinach, 500g", vendor_id=demo_vendor.id)
                p3 = Product(name="Carrots", price=50.0, description="Fresh carrots, 1 kg", vendor_id=demo_vendor.id)
                db.session.add_all([p1, p2, p3])
                db.session.commit()

            # Pre-seed Jane Doe customer
            demo_cust = Customer.query.filter_by(email="jane@example.com").first()
            if not demo_cust:
                demo_cust = Customer(
                    name="Jane Doe",
                    email="jane@example.com",
                    password_hash=generate_password_hash("password123"),
                    phone="9123456780"
                )
                db.session.add(demo_cust)
                db.session.commit()
        except Exception as e:
            print("DB Seed notice:", e)

# ---------- Routes ----------
@app.route("/")
def index():
    return render_template("index.html")

# ---------------- Unified Login ----------------
@app.route("/login", methods=["GET", "POST"])
def unified_login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        # Check vendor first
        vendor = Vendor.query.filter_by(email=email).first()
        if vendor and check_password_hash(vendor.password_hash, password):
            session.clear()
            session["vendor_id"] = vendor.id
            return redirect(url_for("vendor_dashboard"))

        # Check customer
        customer = Customer.query.filter_by(email=email).first()
        if customer and check_password_hash(customer.password_hash, password):
            session.clear()
            session["customer_id"] = customer.id
            return redirect(url_for("customer_dashboard"))

        flash("Invalid email or password.", "error")
        return render_template("login.html")

    return render_template("login.html")

# ---------------- Vendor Routes ----------------
@app.route("/vendor")
def vendor_page():
    return render_template("vendor_page.html")

@app.route("/vendor/register", methods=["GET", "POST"])
def vendor_register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        business_name = request.form.get("business_name", "").strip()
        phone = request.form.get("phone", "").strip()
        landmark = request.form.get("landmark", "").strip()
        address1 = request.form.get("address1", "").strip()
        address2 = request.form.get("address2", "").strip()
        pincode = request.form.get("pincode", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if not name or not email or not business_name or not password or not confirm:
            flash("Required fields are missing.", "error")
            return render_template("vendor_register.html")

        if password != confirm:
            flash("Passwords do not match.", "error")
            return render_template("vendor_register.html")

        if Vendor.query.filter_by(email=email).first():
            flash("Email already registered. Please login.", "error")
            return redirect(url_for("vendor_login"))

        vendor = Vendor(
            name=name,
            email=email,
            business_name=business_name,
            phone=phone,
            landmark=landmark,
            address1=address1,
            address2=address2,
            pincode=pincode,
            password_hash=generate_password_hash(password),
        )
        db.session.add(vendor)
        db.session.commit()

        # Seed initial sample products for new vendors to populate dashboard
        p1 = Product(name="Organic Tomatoes", price=45.0, description="Fresh organic tomatoes, 1 kg", vendor_id=vendor.id)
        p2 = Product(name="Green Spinach", price=30.0, description="Fresh green spinach, 500g", vendor_id=vendor.id)
        p3 = Product(name="Carrots", price=50.0, description="Fresh carrots, 1 kg", vendor_id=vendor.id)
        db.session.add_all([p1, p2, p3])
        db.session.commit()

        session.clear()
        session["vendor_id"] = vendor.id
        flash("Vendor account created successfully!", "success")
        return redirect(url_for("vendor_dashboard"))

    return render_template("vendor_register.html")

@app.route("/vendor/login", methods=["GET", "POST"])
def vendor_login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        vendor = Vendor.query.filter_by(email=email).first()
        if not vendor or not check_password_hash(vendor.password_hash, password):
            flash("Invalid email or password.", "error")
            return render_template("login.html")
        session.clear()
        session["vendor_id"] = vendor.id
        return redirect(url_for("vendor_dashboard"))
    return render_template("login.html")

@app.route("/vendor/dashboard")
@vendor_login_required
def vendor_dashboard():
    vendor = Vendor.query.get(session["vendor_id"])
    products = Product.query.filter_by(vendor_id=vendor.id).order_by(Product.id.desc()).all()
    return render_template("vendor_dashboard.html", vendor=vendor, products=products)

@app.route("/vendor/product/add", methods=["POST"])
@vendor_login_required
def add_product():
    vendor_id = session["vendor_id"]
    name = request.form.get("name", "").strip()
    price = request.form.get("price", "0").strip()
    description = request.form.get("description", "").strip()

    if not name or not price:
        flash("Product name and price are required.", "error")
        return redirect(url_for("vendor_dashboard"))

    try:
        price_val = float(price)
    except ValueError:
        price_val = 0.0

    filename = None
    if "image" in request.files:
        file = request.files["image"]
        if file and file.filename:
            filename = secure_filename(f"{int(datetime.utcnow().timestamp())}_{file.filename}")
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

    product = Product(
        name=name,
        price=price_val,
        description=description,
        image_filename=filename,
        vendor_id=vendor_id
    )
    db.session.add(product)
    db.session.commit()

    flash(f"Product '{name}' added successfully!", "success")
    return redirect(url_for("vendor_dashboard"))

@app.route("/vendor/maps-link/update", methods=["POST"])
@vendor_login_required
def update_maps_link():
    vendor = Vendor.query.get(session["vendor_id"])
    link = request.form.get("maps_link", "").strip()
    if link:
        vendor.maps_link = link
        db.session.commit()
        flash("Google Maps link updated successfully!", "success")
    return redirect(url_for("vendor_dashboard"))

@app.route("/vendor/profile")
@vendor_login_required
def vendor_profile():
    vendor = Vendor.query.get(session["vendor_id"])
    return render_template("vendor_profile.html", vendor=vendor)

@app.route("/vendor/logout")
def vendor_logout():
    session.pop("vendor_id", None)
    return redirect(url_for("index"))

# ---------------- Customer Routes ----------------
@app.route("/customer")
def customer_page():
    return render_template("customer_page.html")

@app.route("/customer/register", methods=["GET", "POST"])
def customer_register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if not name or not email or not password or not confirm:
            flash("All fields are required.", "error")
            return render_template("customer_register.html")

        if password != confirm:
            flash("Passwords do not match.", "error")
            return render_template("customer_register.html")

        if Customer.query.filter_by(email=email).first():
            flash("Email already registered. Please login.", "error")
            return redirect(url_for("customer_login"))

        customer = Customer(
            name=name,
            email=email,
            phone=phone,
            password_hash=generate_password_hash(password),
        )
        db.session.add(customer)
        db.session.commit()

        session.clear()
        session["customer_id"] = customer.id
        flash("Customer account created successfully!", "success")
        return redirect(url_for("customer_dashboard"))

    return render_template("customer_register.html")

@app.route("/customer/login", methods=["GET", "POST"])
def customer_login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        customer = Customer.query.filter_by(email=email).first()
        if not customer or not check_password_hash(customer.password_hash, password):
            flash("Invalid email or password.", "error")
            return render_template("login.html")
        session.clear()
        session["customer_id"] = customer.id
        return redirect(url_for("customer_dashboard"))
    return render_template("login.html")

@app.route("/customer/dashboard")
@customer_login_required
def customer_dashboard():
    customer = Customer.query.get(session["customer_id"])
    vendors = Vendor.query.all()
    products = Product.query.filter_by(is_active=True).order_by(Product.id.desc()).limit(8).all()
    return render_template("customer_dashboard.html", customer=customer, vendors=vendors, products=products)

@app.route("/customer/profile")
@customer_login_required
def customer_profile():
    customer = Customer.query.get(session["customer_id"])
    return render_template("customer_profile.html", customer=customer)

@app.route("/customer/logout")
def customer_logout():
    session.pop("customer_id", None)
    return redirect(url_for("index"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

with app.app_context():
    init_db()

if __name__ == "__main__":
    app.run(debug=True)

