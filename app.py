from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os

app = Flask(__name__)
# RẤT QUAN TRỌNG: Thay đổi khóa bí mật này bằng một chuỗi ngẫu nhiên, mạnh mẽ trong môi trường thực tế!
app.secret_key = 'day_la_khoa_bi_mat_rat_manh_me_cua_ban_123abcXYZ!@#'

# --- Cấu hình Database ---
DATABASE = 'database.db'

# ... (Giữ nguyên tất cả các code khác ở phía trên) ...

def get_db():
    db = getattr(app, '_database', None)
    if db is None:
        # THAY ĐỔI DÒNG NÀY: Thêm check_same_thread=False
        db = app._database = sqlite3.connect(DATABASE, check_same_thread=False)
        db.row_factory = sqlite3.Row # Cho phép truy cập cột như dictionary
    return db

# ... (Giữ nguyên tất cả các code khác ở phía dưới) ...

@app.teardown_appcontext
def close_connection(exception):
    # Hàm này đảm bảo kết nối database được đóng khi ngữ cảnh ứng dụng kết thúc
    # Ngăn chặn rò rỉ tài nguyên
    db = getattr(app, '_database', None)
    if db is not None:
        db.close()

def init_db():
    # Hàm này tạo các bảng trong cơ sở dữ liệu nếu chúng chưa tồn tại
    # Không cần 'with app.app_context():' ở đây vì nó sẽ được gọi trong một ngữ cảnh chung
    db = get_db()
    db.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            description TEXT,
            image_url TEXT
        )
    ''')
    db.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            total_amount REAL NOT NULL,
            order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    db.execute('''
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            price REAL NOT NULL,
            quantity INTEGER NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders (id),
            FOREIGN KEY (product_id) REFERENCES products (id)
        )
    ''')
    db.commit() # Lưu các thay đổi (tạo bảng) vào database

# --- Chèn dữ liệu mẫu (chỉ chạy lần đầu nếu bảng trống) ---
def seed_db():
    # Hàm này chèn dữ liệu mẫu vào bảng products nếu bảng đang trống
    # Không cần 'with app.app_context():' ở đây vì nó sẽ được gọi trong một ngữ cảnh chung
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT COUNT(*) FROM products")
    if cursor.fetchone()[0] == 0: # Chỉ thêm nếu bảng rỗng
        products_data = [
            ('Áo phông nam', 150000.0, 'Áo phông cotton 100% thoải mái.', 'https://via.placeholder.com/150/0000FF/FFFFFF?text=Ao+Phong'),
            ('Quần Jeans nữ', 350000.0, 'Quần Jeans co giãn, thời trang.', 'https://via.placeholder.com/150/FF0000/FFFFFF?text=Quan+Jeans'),
            ('Giày Sneaker', 700000.0, 'Giày thể thao năng động, êm ái.', 'https://via.placeholder.com/150/00FF00/FFFFFF?text=Giay+Sneaker'),
            ('Túi xách da', 500000.0, 'Túi xách da cao cấp, sang trọng.', 'https://via.placeholder.com/150/FFFF00/000000?text=Tui+Xach')
        ]
        db.executemany("INSERT INTO products (name, price, description, image_url) VALUES (?, ?, ?, ?)", products_data)
        db.commit() # Lưu dữ liệu mẫu vào database
        print("Đã thêm dữ liệu mẫu vào database.")

# --- Routes (Định tuyến URL cho các trang web) ---

@app.before_request
def before_request():
    # Chạy trước mỗi yêu cầu để đảm bảo giỏ hàng tồn tại trong session
    if 'cart' not in session:
        session['cart'] = {} # Khởi tạo giỏ hàng rỗng nếu chưa có

@app.route('/')
def index():
    # Hiển thị danh sách sản phẩm trên trang chủ
    db = get_db()
    cursor = db.execute('SELECT * FROM products')
    products = cursor.fetchall() # Lấy tất cả sản phẩm
    return render_template('index.html', products=products)

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    # Hiển thị chi tiết một sản phẩm cụ thể
    db = get_db()
    cursor = db.execute('SELECT * FROM products WHERE id = ?', (product_id,))
    product = cursor.fetchone() # Lấy một sản phẩm theo ID
    if product is None:
        flash('Sản phẩm không tồn tại.', 'error')
        return redirect(url_for('index'))
    return render_template('product_detail.html', product=product)

@app.route('/add_to_cart/<int:product_id>')
def add_to_cart(product_id):
    # Thêm sản phẩm vào giỏ hàng
    db = get_db()
    cursor = db.execute('SELECT id, name, price FROM products WHERE id = ?', (product_id,))
    product = cursor.fetchone()

    if product is None:
        flash('Sản phẩm không tồn tại để thêm vào giỏ hàng.', 'error')
        return redirect(url_for('index'))

    product_id_str = str(product['id'])
    if product_id_str in session['cart']:
        session['cart'][product_id_str]['quantity'] += 1 # Tăng số lượng nếu sản phẩm đã có
    else:
        session['cart'][product_id_str] = {
            'name': product['name'],
            'price': product['price'],
            'quantity': 1 # Thêm mới với số lượng 1
        }
    session.modified = True # Đánh dấu session đã thay đổi để Flask lưu lại
    flash(f"Đã thêm '{product['name']}' vào giỏ hàng.", 'success')
    return redirect(url_for('index'))

@app.route('/cart')
def view_cart():
    # Hiển thị nội dung giỏ hàng
    cart_items = []
    total_cart_price = 0
    for product_id_str, item_data in session['cart'].items():
        item_price = item_data['price'] * item_data['quantity']
        cart_items.append({
            'id': int(product_id_str),
            'name': item_data['name'],
            'price': item_data['price'],
            'quantity': item_data['quantity'],
            'total_item_price': item_price
        })
        total_cart_price += item_price
    return render_template('cart.html', cart_items=cart_items, total_cart_price=total_cart_price)

@app.route('/update_cart_quantity/<int:product_id>', methods=['POST'])
def update_cart_quantity(product_id):
    # Cập nhật số lượng sản phẩm trong giỏ hàng hoặc xóa
    quantity = int(request.form.get('quantity', 0))
    product_id_str = str(product_id)

    if product_id_str in session['cart']:
        if quantity > 0:
            session['cart'][product_id_str]['quantity'] = quantity
            flash('Đã cập nhật số lượng.', 'success')
        else:
            del session['cart'][product_id_str] # Xóa khỏi giỏ nếu số lượng <= 0
            flash('Đã xóa sản phẩm khỏi giỏ hàng.', 'success')
        session.modified = True
    else:
        flash('Sản phẩm không có trong giỏ hàng.', 'error')
    return redirect(url_for('view_cart'))

@app.route('/checkout')
def checkout():
    # Trang xác nhận đơn hàng trước khi đặt
    cart_items = []
    total_cart_price = 0
    for product_id_str, item_data in session['cart'].items():
        item_price = item_data['price'] * item_data['quantity']
        cart_items.append({
            'id': int(product_id_str),
            'name': item_data['name'],
            'price': item_data['price'],
            'quantity': item_data['quantity'],
            'total_item_price': item_price
        })
        total_cart_price += item_price
    if not cart_items:
        flash('Giỏ hàng của bạn đang trống!', 'info')
        return redirect(url_for('index'))
    return render_template('checkout.html', cart_items=cart_items, total_cart_price=total_cart_price)

@app.route('/place_order', methods=['POST'])
def place_order():
    # Xử lý việc đặt hàng và lưu vào database
    if not session['cart']:
        flash('Không có sản phẩm trong giỏ hàng để đặt.', 'error')
        return redirect(url_for('index'))

    db = get_db()
    total_amount = 0
    order_items_to_save = []

    for product_id_str, item_data in session['cart'].items():
        item_price = item_data['price'] * item_data['quantity']
        total_amount += item_price
        order_items_to_save.append({
            'product_id': int(product_id_str),
            'product_name': item_data['name'],
            'price': item_data['price'],
            'quantity': item_data['quantity']
        })

    try:
        # Bắt đầu giao dịch (transaction) để đảm bảo tính toàn vẹn dữ liệu
        cursor = db.cursor()
        cursor.execute("INSERT INTO orders (total_amount) VALUES (?)", (total_amount,))
        order_id = cursor.lastrowid # Lấy ID của đơn hàng vừa tạo

        for item in order_items_to_save:
            cursor.execute(
                "INSERT INTO order_items (order_id, product_id, product_name, price, quantity) VALUES (?, ?, ?, ?, ?)",
                (order_id, item['product_id'], item['product_name'], item['price'], item['quantity'])
            )
        db.commit() # Lưu thay đổi vào database

        session.pop('cart', None) # Xóa giỏ hàng sau khi đặt hàng thành công
        flash('Đơn hàng của bạn đã được đặt thành công!', 'success')
        return redirect(url_for('order_confirmation', order_id=order_id))
    except sqlite3.Error as e:
        db.rollback() # Hoàn tác nếu có lỗi trong quá trình ghi database
        flash(f'Có lỗi xảy ra khi đặt hàng: {e}', 'error')
        return redirect(url_for('checkout'))

@app.route('/order_confirmation/<int:order_id>')
def order_confirmation(order_id):
    # Hiển thị trang xác nhận đơn hàng sau khi đặt thành công
    db = get_db()
    order_cursor = db.execute('SELECT * FROM orders WHERE id = ?', (order_id,))
    order = order_cursor.fetchone()
    if order is None:
        flash('Đơn hàng không tồn tại.', 'error')
        return redirect(url_for('index'))

    items_cursor = db.execute('SELECT * FROM order_items WHERE order_id = ?', (order_id,))
    order_items = items_cursor.fetchall()

    return render_template('order_confirmation.html', order=order, order_items=order_items)

# Phần này chỉ chạy khi file app.py được chạy trực tiếp (không phải khi import)
if __name__ == '__main__':
    # Đảm bảo database và dữ liệu mẫu được khởi tạo khi chạy ứng dụng lần đầu
    # Sử dụng app.app_context() để chạy code liên quan đến database bên ngoài một yêu cầu web
    with app.app_context():
        init_db() # Khởi tạo các bảng database
        seed_db() # Chèn dữ liệu mẫu nếu database trống
    app.run(debug=True) # Chạy ứng dụng Flask. debug=True giúp tự động reload khi sửa code và hiển thị lỗi chi tiết.