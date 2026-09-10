from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from datetime import datetime, timedelta
from functools import wraps

app = Flask(__name__)
app.secret_key = "farmfresh-secret-key"
DB = "farmfresh.db"

CATEGORIES = ["Vegetables", "Fruits", "Greens", "Organic", "Combo Packs"]

IMAGE_POOL = {
    "Vegetables": [
        "https://images.unsplash.com/photo-1546094096-0df4bcaaa337?auto=format&fit=crop&w=900&q=85",
        "https://images.unsplash.com/photo-1445282768818-728615cc910a?auto=format&fit=crop&w=900&q=85",
        "https://images.unsplash.com/photo-1459411621453-7b03977f4bfc?auto=format&fit=crop&w=900&q=85",
    ],
    "Fruits": [
        "https://images.unsplash.com/photo-1560806887-1e4cd0b6cbd6?auto=format&fit=crop&w=900&q=85",
        "https://images.unsplash.com/photo-1464965911861-746a04b4bca6?auto=format&fit=crop&w=900&q=85",
        "https://images.unsplash.com/photo-1571771894821-ce9b6c11b08e?auto=format&fit=crop&w=900&q=85",
    ],
    "Greens": [
        "https://images.unsplash.com/photo-1576045057995-568f588f82fb?auto=format&fit=crop&w=900&q=85",
        "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?auto=format&fit=crop&w=900&q=85",
    ],
    "Organic": [
        "https://images.unsplash.com/photo-1498837167922-ddd27525d352?auto=format&fit=crop&w=900&q=85",
        "https://images.unsplash.com/photo-1542838132-92c53300491e?auto=format&fit=crop&w=900&q=85",
    ],
    "Combo Packs": [
        "https://images.unsplash.com/photo-1518843875459-f738682238a6?auto=format&fit=crop&w=900&q=85",
        "https://images.unsplash.com/photo-1542838132-92c53300491e?auto=format&fit=crop&w=900&q=85",
    ],
}

PRODUCT_NAMES = {
    "Vegetables": ["Tomato", "Carrot", "Potato", "Cucumber", "Onion", "Beetroot",
                   "Brinjal", "Capsicum", "Beans", "Cauliflower", "Broccoli",
                   "Radish", "Pumpkin", "Bottle Gourd", "Lady Finger"],
    "Fruits": ["Apple", "Banana", "Mango", "Orange", "Grapes", "Papaya",
               "Pomegranate", "Guava", "Pineapple", "Watermelon", "Muskmelon",
               "Kiwi", "Pear", "Dragon Fruit"],
    "Greens": ["Spinach", "Coriander", "Mint Leaves", "Drumstick Leaves",
               "Curry Leaves", "Amaranth", "Fenugreek Leaves", "Lettuce",
               "Moringa Greens", "Palak"],
    "Organic": ["Organic Tomato", "Organic Carrot", "Organic Potato",
                "Organic Banana", "Organic Spinach", "Organic Mango",
                "Organic Beans", "Organic Greens"],
    "Combo Packs": ["Daily Veggie Combo", "Family Fruit Combo",
                    "Healthy Greens Combo", "Kitchen Essentials Combo",
                    "Salad Combo", "Organic Starter Combo"],
}

FARMERS = [
    "Kumar Organic Farm", "Green Valley Farm", "Sunrise Farm",
    "Fresh Leaf Farm", "Selvam Farm", "Hill Fresh Farm",
    "Anbu Naturals", "Cauvery Agro"
]


def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        price REAL NOT NULL,
        unit TEXT NOT NULL,
        farmer TEXT NOT NULL,
        rating REAL NOT NULL,
        image_url TEXT NOT NULL,
        stock INTEGER NOT NULL,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS wishlist (
        user_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        PRIMARY KEY (user_id, product_id)
    );

    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER NOT NULL,
        address TEXT NOT NULL,
        amount REAL NOT NULL,
        status TEXT NOT NULL,
        eta TEXT NOT NULL,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        product_name TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        price REAL NOT NULL
    );

    CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        customer_id INTEGER NOT NULL,
        rating INTEGER NOT NULL,
        quality INTEGER NOT NULL,
        delivery_rating INTEGER NOT NULL,
        comment TEXT,
        created_at TEXT NOT NULL
    );
    """)

    owner = cur.execute(
        "SELECT id FROM users WHERE username=?",
        ("owner@farmfresh.com",)
    ).fetchone()

    if not owner:
        cur.execute(
            """INSERT INTO users(name, username, password, role, created_at)
               VALUES(?,?,?,?,?)""",
            ("FarmFresh Owner", "owner@farmfresh.com", "owner123",
             "owner", datetime.now().isoformat())
        )

    product_count = cur.execute(
        "SELECT COUNT(*) AS c FROM products"
    ).fetchone()["c"]

    if product_count < 1000:
        cur.execute("DELETE FROM products")
        rows = []
        now = datetime.now().isoformat()

        for category in CATEGORIES:
            for i in range(1, 201):
                base = PRODUCT_NAMES[category][
                    (i - 1) % len(PRODUCT_NAMES[category])
                ]
                batch = "" if i <= len(PRODUCT_NAMES[category]) else " Farm Batch {}".format(i)
                name = base + batch
                price = 20 + ((i * 7 + len(category) * 5) % 180)
                unit = "1 kg" if category != "Combo Packs" else "1 pack"
                farmer = FARMERS[(i + len(category)) % len(FARMERS)]
                rating = min(4.9, 4.2 + ((i % 8) * 0.1))
                image_url = IMAGE_POOL[category][
                    (i - 1) % len(IMAGE_POOL[category])
                ]
                stock = 50 + (i % 100)
                rows.append(
                    (name, category, price, unit, farmer, rating,
                     image_url, stock, now)
                )

        cur.executemany(
            """INSERT INTO products
               (name, category, price, unit, farmer, rating, image_url, stock, created_at)
               VALUES(?,?,?,?,?,?,?,?,?)""",
            rows
        )

    conn.commit()
    conn.close()


def get_current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None

    conn = get_db()
    user = conn.execute(
        "SELECT * FROM users WHERE id=?", (user_id,)
    ).fetchone()
    conn.close()
    return user


@app.context_processor
def add_globals():
    return {
        "current_user": get_current_user(),
        "categories": CATEGORIES
    }


def role_required(role):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            user = get_current_user()
            if not user:
                flash("Please login first.", "warning")
                return redirect(url_for("login", role=role))
            if user["role"] != role:
                flash("You do not have access to this page.", "danger")
                return redirect(url_for("home"))
            return view(*args, **kwargs)
        return wrapped
    return decorator


@app.route("/")
def home():
    conn = get_db()
    featured = conn.execute(
        "SELECT * FROM products ORDER BY id LIMIT 16"
    ).fetchall()
    conn.close()
    return render_template("home.html", featured=featured)


@app.route("/login/<role>", methods=["GET", "POST"])
def login(role):
    if role not in ["customer", "seller", "owner"]:
        return redirect(url_for("home"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        conn = get_db()
        user = conn.execute(
            """SELECT * FROM users
               WHERE username=? AND password=? AND role=?""",
            (username, password, role)
        ).fetchone()
        conn.close()

        if user:
            session.clear()
            session["user_id"] = user["id"]
            flash("Login successful.", "success")

            if role == "seller":
                return redirect(url_for("seller_dashboard"))
            if role == "owner":
                return redirect(url_for("owner_dashboard"))
            return redirect(url_for("shop"))

        flash("Invalid username or password.", "danger")

    return render_template("login.html", role=role)


@app.route("/register/<role>", methods=["GET", "POST"])
def register(role):
    if role not in ["customer", "seller"]:
        return redirect(url_for("home"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not name or not username or not password:
            flash("Please fill every field.", "warning")
            return redirect(request.url)

        conn = get_db()
        try:
            cur = conn.execute(
                """INSERT INTO users(name, username, password, role, created_at)
                   VALUES(?,?,?,?,?)""",
                (name, username, password, role, datetime.now().isoformat())
            )
            conn.commit()
            session.clear()
            session["user_id"] = cur.lastrowid
            flash("Account created successfully.", "success")

            if role == "seller":
                return redirect(url_for("seller_dashboard"))
            return redirect(url_for("shop"))

        except sqlite3.IntegrityError:
            flash("That username already exists.", "danger")
        finally:
            conn.close()

    return render_template("register.html", role=role)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


@app.route("/shop")
def shop():
    q = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()

    try:
        page = max(1, int(request.args.get("page", 1)))
    except ValueError:
        page = 1

    per_page = 24
    offset = (page - 1) * per_page

    conn = get_db()
    conditions = []
    params = []

    if q:
        conditions.append("(name LIKE ? OR farmer LIKE ?)")
        params.extend(["%{}%".format(q), "%{}%".format(q)])

    if category:
        conditions.append("category=?")
        params.append(category)

    where = ""
    if conditions:
        where = " WHERE " + " AND ".join(conditions)

    total = conn.execute(
        "SELECT COUNT(*) AS c FROM products" + where, params
    ).fetchone()["c"]

    products = conn.execute(
        "SELECT * FROM products" + where +
        " ORDER BY id DESC LIMIT ? OFFSET ?",
        params + [per_page, offset]
    ).fetchall()

    wishlist_ids = set()
    user = get_current_user()
    if user and user["role"] == "customer":
        rows = conn.execute(
            "SELECT product_id FROM wishlist WHERE user_id=?",
            (user["id"],)
        ).fetchall()
        wishlist_ids = set(row["product_id"] for row in rows)

    conn.close()

    pages = max(1, (total + per_page - 1) // per_page)

    return render_template(
        "shop.html",
        products=products,
        q=q,
        selected_category=category,
        wishlist_ids=wishlist_ids,
        page=page,
        pages=pages,
        total=total
    )


@app.route("/product/<int:product_id>")
def product_detail(product_id):
    conn = get_db()
    product = conn.execute(
        "SELECT * FROM products WHERE id=?", (product_id,)
    ).fetchone()
    conn.close()

    if not product:
        flash("Product not found.", "danger")
        return redirect(url_for("shop"))

    return render_template("product_detail.html", product=product)


@app.route("/wishlist/toggle/<int:product_id>")
@role_required("customer")
def wishlist_toggle(product_id):
    user = get_current_user()
    conn = get_db()

    exists = conn.execute(
        """SELECT 1 FROM wishlist
           WHERE user_id=? AND product_id=?""",
        (user["id"], product_id)
    ).fetchone()

    if exists:
        conn.execute(
            "DELETE FROM wishlist WHERE user_id=? AND product_id=?",
            (user["id"], product_id)
        )
    else:
        conn.execute(
            "INSERT OR IGNORE INTO wishlist(user_id, product_id) VALUES(?,?)",
            (user["id"], product_id)
        )

    conn.commit()
    conn.close()
    return redirect(request.referrer or url_for("shop"))


@app.route("/wishlist")
@role_required("customer")
def wishlist():
    user = get_current_user()
    conn = get_db()
    products = conn.execute(
        """SELECT p.* FROM products p
           JOIN wishlist w ON w.product_id=p.id
           WHERE w.user_id=?
           ORDER BY p.id DESC""",
        (user["id"],)
    ).fetchall()
    conn.close()
    return render_template("wishlist.html", products=products)


def get_cart_items():
    cart = session.get("cart", {})
    if not cart:
        return [], 0

    ids = [int(x) for x in cart.keys()]
    marks = ",".join(["?"] * len(ids))

    conn = get_db()
    products = conn.execute(
        "SELECT * FROM products WHERE id IN ({})".format(marks),
        ids
    ).fetchall()
    conn.close()

    by_id = {str(p["id"]): p for p in products}
    items = []
    subtotal = 0

    for product_id, qty in cart.items():
        product = by_id.get(str(product_id))
        if product:
            line_total = product["price"] * qty
            subtotal += line_total
            items.append({
                "product": product,
                "quantity": qty,
                "line_total": line_total
            })

    return items, subtotal


@app.route("/cart")
@role_required("customer")
def cart():
    items, subtotal = get_cart_items()
    delivery = 40 if items else 0
    total = subtotal + delivery

    return render_template(
        "cart.html",
        items=items,
        subtotal=subtotal,
        delivery=delivery,
        total=total
    )


@app.route("/cart/add/<int:product_id>")
@role_required("customer")
def cart_add(product_id):
    cart = session.get("cart", {})
    key = str(product_id)
    cart[key] = cart.get(key, 0) + 1
    session["cart"] = cart
    flash("Added to cart.", "success")
    return redirect(request.referrer or url_for("shop"))


@app.route("/cart/update/<int:product_id>/<action>")
@role_required("customer")
def cart_update(product_id, action):
    cart = session.get("cart", {})
    key = str(product_id)

    if key in cart:
        if action == "plus":
            cart[key] += 1
        elif action == "minus":
            cart[key] -= 1
            if cart[key] <= 0:
                cart.pop(key, None)
        elif action == "remove":
            cart.pop(key, None)

    session["cart"] = cart
    return redirect(url_for("cart"))


@app.route("/checkout", methods=["GET", "POST"])
@role_required("customer")
def checkout():
    items, subtotal = get_cart_items()
    delivery = 40 if items else 0
    total = subtotal + delivery

    if not items:
        flash("Your cart is empty.", "warning")
        return redirect(url_for("shop"))

    if request.method == "POST":
        address = request.form.get("address", "").strip()
        amount_text = request.form.get("amount", "").strip()

        if not address or not amount_text:
            flash("Address and amount are required.", "warning")
            return redirect(request.url)

        try:
            amount = float(amount_text)
        except ValueError:
            flash("Enter a valid amount.", "danger")
            return redirect(request.url)

        user = get_current_user()
        eta = (
            datetime.now() + timedelta(minutes=35)
        ).strftime("%d %b %Y, %I:%M %p")

        conn = get_db()

        cur = conn.execute(
            """INSERT INTO orders
               (customer_id, address, amount, status, eta, created_at)
               VALUES(?,?,?,?,?,?)""",
            (
                user["id"],
                address,
                amount,
                "On the way",
                eta,
                datetime.now().isoformat()
            )
        )

        order_id = cur.lastrowid

        for item in items:
            conn.execute(
                """INSERT INTO order_items
                   (order_id, product_id, product_name, quantity, price)
                   VALUES(?,?,?,?,?)""",
                (
                    order_id,
                    item["product"]["id"],
                    item["product"]["name"],
                    item["quantity"],
                    item["product"]["price"]
                )
            )

        conn.commit()
        conn.close()

        session["cart"] = {}
        return redirect(url_for("tracking", order_id=order_id))

    return render_template(
        "checkout.html",
        subtotal=subtotal,
        delivery=delivery,
        total=total
    )


@app.route("/orders")
@role_required("customer")
def orders():
    user = get_current_user()
    conn = get_db()
    orders_list = conn.execute(
        "SELECT * FROM orders WHERE customer_id=? ORDER BY id DESC",
        (user["id"],)
    ).fetchall()
    conn.close()
    return render_template("orders.html", orders=orders_list)


@app.route("/tracking/<int:order_id>")
@role_required("customer")
def tracking(order_id):
    user = get_current_user()
    conn = get_db()

    order = conn.execute(
        """SELECT * FROM orders
           WHERE id=? AND customer_id=?""",
        (order_id, user["id"])
    ).fetchone()

    items = conn.execute(
        "SELECT * FROM order_items WHERE order_id=?",
        (order_id,)
    ).fetchall()

    review = conn.execute(
        "SELECT * FROM reviews WHERE order_id=?",
        (order_id,)
    ).fetchone()

    conn.close()

    if not order:
        flash("Order not found.", "danger")
        return redirect(url_for("orders"))

    return render_template(
        "tracking.html",
        order=order,
        items=items,
        review=review
    )


@app.route("/order/<int:order_id>/delivered", methods=["POST"])
@role_required("customer")
def mark_delivered(order_id):
    user = get_current_user()
    conn = get_db()

    conn.execute(
        """UPDATE orders SET status='Delivered'
           WHERE id=? AND customer_id=?""",
        (order_id, user["id"])
    )

    conn.commit()
    conn.close()

    return redirect(url_for("tracking", order_id=order_id))


@app.route("/review/<int:order_id>", methods=["GET", "POST"])
@role_required("customer")
def review(order_id):
    user = get_current_user()
    conn = get_db()

    order = conn.execute(
        """SELECT * FROM orders
           WHERE id=? AND customer_id=?""",
        (order_id, user["id"])
    ).fetchone()

    existing = conn.execute(
        "SELECT * FROM reviews WHERE order_id=?",
        (order_id,)
    ).fetchone()

    conn.close()

    if not order:
        flash("Order not found.", "danger")
        return redirect(url_for("orders"))

    if request.method == "POST" and not existing:
        rating = int(request.form.get("rating", 5))
        quality = int(request.form.get("quality", 5))
        delivery_rating = int(request.form.get("delivery_rating", 5))
        comment = request.form.get("comment", "").strip()

        conn = get_db()
        conn.execute(
            """INSERT INTO reviews
               (order_id, customer_id, rating, quality, delivery_rating, comment, created_at)
               VALUES(?,?,?,?,?,?,?)""",
            (
                order_id,
                user["id"],
                rating,
                quality,
                delivery_rating,
                comment,
                datetime.now().isoformat()
            )
        )
        conn.commit()
        conn.close()

        flash("Review submitted. Thank you!", "success")
        return redirect(url_for("tracking", order_id=order_id))

    return render_template(
        "review.html",
        order=order,
        existing=existing
    )


@app.route("/seller")
@role_required("seller")
def seller_dashboard():
    user = get_current_user()
    conn = get_db()

    my_products = conn.execute(
        "SELECT * FROM products WHERE farmer=? ORDER BY id DESC LIMIT 100",
        (user["name"],)
    ).fetchall()

    recent_orders = conn.execute(
        """SELECT o.*, oi.product_name, oi.quantity
           FROM orders o
           JOIN order_items oi ON oi.order_id=o.id
           ORDER BY o.id DESC LIMIT 50"""
    ).fetchall()

    conn.close()

    return render_template(
        "seller_dashboard.html",
        products=my_products,
        orders=recent_orders
    )


@app.route("/seller/product/add", methods=["POST"])
@role_required("seller")
def seller_add_product():
    user = get_current_user()

    name = request.form.get("name", "").strip()
    category = request.form.get("category", "Vegetables")
    unit = request.form.get("unit", "1 kg")
    image_url = request.form.get("image_url", "").strip()
    price_text = request.form.get("price", "0")
    stock_text = request.form.get("stock", "50")

    try:
        price = float(price_text)
        stock = int(stock_text)
    except ValueError:
        flash("Price and stock must be numbers.", "danger")
        return redirect(url_for("seller_dashboard"))

    if not image_url:
        image_url = IMAGE_POOL[category][0]

    conn = get_db()
    conn.execute(
        """INSERT INTO products
           (name, category, price, unit, farmer, rating, image_url, stock, created_at)
           VALUES(?,?,?,?,?,?,?,?,?)""",
        (
            name, category, price, unit, user["name"], 4.5,
            image_url, stock, datetime.now().isoformat()
        )
    )
    conn.commit()
    conn.close()

    flash("Product added successfully.", "success")
    return redirect(url_for("seller_dashboard"))


@app.route("/owner")
@role_required("owner")
def owner_dashboard():
    conn = get_db()

    user_count = conn.execute(
        "SELECT COUNT(*) AS c FROM users"
    ).fetchone()["c"]

    product_count = conn.execute(
        "SELECT COUNT(*) AS c FROM products"
    ).fetchone()["c"]

    order_count = conn.execute(
        "SELECT COUNT(*) AS c FROM orders"
    ).fetchone()["c"]

    users = conn.execute(
        "SELECT * FROM users ORDER BY id DESC LIMIT 50"
    ).fetchall()

    recent_orders = conn.execute(
        "SELECT * FROM orders ORDER BY id DESC LIMIT 50"
    ).fetchall()

    conn.close()

    return render_template(
        "owner_dashboard.html",
        user_count=user_count,
        product_count=product_count,
        order_count=order_count,
        users=users,
        orders=recent_orders
    )


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
