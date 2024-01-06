from flask import Flask, render_template, request, session, redirect, url_for, flash
import secrets
from flask_mysqldb import MySQL
import os
from passlib.hash import sha256_crypt  # Added for password hashing
from database_management import *
from asos_scraper import *
from flask import jsonify

app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(16)
# MySQL Configuration
app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST')
app.config['MYSQL_USER'] = os.getenv('MYSQL_USER')
app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD')
app.config['MYSQL_DB'] = os.getenv('MYSQL_DB')
mysql = MySQL(app)

# Initialize password hashing
hasher = sha256_crypt.using(rounds=1000, salt_size=16)


# Existing route for index
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Handle form submission or any other logic here
        # For example, you can access form data using request.form
        # data = request.form['input_name']
        # Perform some processing with the form data

        # Redirect to another page after processing
        return redirect(url_for('success'))

    return render_template('index.html')


# Existing route for success
@app.route('/success')
def success():
    return "Form submitted successfully!"


# New route for user login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cur = mysql.connection.cursor()
        cur.execute("SELECT username, password_hash FROM tbl_users WHERE username = %s", (username,))
        user = cur.fetchone()

        cur.close()

        if user and sha256_crypt.verify(password, user[1]):
            session['username'] = user[0]

            return redirect(url_for('index'))

        flash('Invalid username or password', 'error')

    return render_template('login.html')


# New route for user registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        # Hash the password before storing it
        hashed_password = sha256_crypt.hash(password)

        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO tbl_users (username, email, password_hash) VALUES (%s, %s, %s)",
                    (username, email, hashed_password))
        mysql.connection.commit()
        cur.close()

        flash('Registration successful! You can now log in.', 'success')

        return redirect(url_for('login'))

    return render_template('register.html')


# Existing route for user logout
@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))


# New route for adding or searching product
@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    if 'username' in session:
        product_url=''
        if request.method == 'POST':
            if 'search_product' in request.form:
                # Handle product search
                product_url = request.form['product_details']
                result = extract_info_from_url(product_url)
                return jsonify(result)

            else:  # Assuming the other button is 'add_product'
                username = session['username']
                user_id = get_user_id_by_username(username)

                if user_id:
                    url = request.form['product_details']
                    target_price = request.form['target_price']

                    currency, product_name, initial_price = extract_info_from_url(url)

                    if not product_exists(user_id, product_name):
                        # Extract current price and currency here
                        current_price = initial_price

                        save_tracked_product(user_id, product_name, url, initial_price, target_price, current_price,
                                             currency)

                        return redirect(url_for('success'))

                    flash('Product already exists for the user.', 'error')
                else:
                    flash('User not found.', 'error')

        return render_template('add_product.html')
    else:
        flash('Please log in to add or search a product.', 'error')
        return redirect(url_for('login'))

@app.route('/price_comparison', methods=['GET', 'POST'])
def price_comparison():
    if request.method == 'POST':
        # Handle form submission or any other logic here
        return redirect(url_for('success'))

    return render_template('price_comparison.html')


if __name__ == '__main__':
    app.run(debug=True)
