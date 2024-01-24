from flask import Flask, render_template, request, session, redirect, url_for, flash
import secrets
from flask_mysqldb import MySQL
import os
from passlib.hash import sha256_crypt  # Added for password hashing
from database_management import *
from asos_scraper import *
from flask import jsonify
from flask_swagger_ui import get_swaggerui_blueprint
from flasgger import Swagger

app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(16)
# MySQL Configuration
app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST')
app.config['MYSQL_USER'] = os.getenv('MYSQL_USER')
app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD')
app.config['MYSQL_DB'] = os.getenv('MYSQL_DB')
mysql = MySQL(app)
swagger_url = '/swagger'
swaggerui_blueprint = get_swaggerui_blueprint(
    swagger_url,
    '/static/swagger.json',
    config={
        'app_name': "Retail Analysis Platform"
    }
)
Swagger(app)

app.register_blueprint(swaggerui_blueprint, url_prefix=swagger_url)

# Initialize password hashing
hasher = sha256_crypt.using(rounds=1000, salt_size=16)


@app.route('/api/example', methods=['GET'])
def example_route():
    """
    This is an example route that demonstrates how to use docstrings for documentation.

    ---
    tags:
      - Example
    responses:
      200:
        description: Successful response
    """
    return jsonify({"message": "Hello, this is an example route!"})


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


#  user login
@app.route('/login', methods=['POST'])
def login():
    """
    User login endpoint.

    ---
    tags:
      - Authentication
    parameters:
      - name: username
        in: formData
        type: string
        required: true
        description: The username for login.
      - name: password
        in: formData
        type: string
        required: true
        description: The password for login.
    responses:
      200:
        description: Login successful
        content:
          application/json:
            example: {"message": "Login successful"}
      401:
        description: Unauthorized, invalid credentials
        content:
          application/json:
            example: {"message": "Invalid username or password"}
      400:
        description: Bad request, missing or invalid parameters
        content:
          application/json:
            example: {"message": "Bad request"}
    """
    if 'username' in session:
        return jsonify({"message": "Bad request - There is a connection to another user"}), 400

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            return jsonify({"message": "Bad request"}), 400

        cur = mysql.connection.cursor()
        cur.execute("SELECT username, password_hash FROM tbl_users WHERE username = %s", (username,))
        user = cur.fetchone()
        cur.close()

        if user and sha256_crypt.verify(password, user[1]):
            session['username'] = user[0]
            return jsonify({"message": "Login successful"}), 200

        return jsonify({"message": "Invalid username or password"}), 401

    # If not a POST request, return method not allowed
    return jsonify({"message": "Method not allowed"}), 405


@app.route('/register', methods=['POST'])
def register():
    """
    User registration endpoint.

    ---
    tags:
      - Authentication
    parameters:
      - name: username
        in: formData
        type: string
        required: true
        description: The username for registration.
      - name: email
        in: formData
        type: string
        required: true
        description: The email for registration.
      - name: password
        in: formData
        type: string
        required: true
        description: The password for registration.
    responses:
      201:
        description: Registration successful
        content:
          application/json:
            example: {"message": "Registration successful! You can now log in."}
      400:
        description: Bad request, missing or invalid parameters
        content:
          application/json:
            example: {"message": "Bad request"}
    """
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        if not username or not email or not password:
            return jsonify({"message": "Bad request"}), 400

        # Hash the password before storing it
        hashed_password = sha256_crypt.hash(password)

        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO tbl_users (username, email, password_hash) VALUES (%s, %s, %s)",
                    (username, email, hashed_password))
        mysql.connection.commit()
        cur.close()

        return jsonify({"message": "Registration successful! You can now log in."}), 201

    # If not a POST request, return method not allowed
    return jsonify({"message": "Method not allowed"}), 405


@app.route('/logout', methods=['POST'])
def logout():
    """
    User logout endpoint.

    ---
    tags:
      - Authentication
    responses:
      200:
        description: Logout successful
        content:
          application/json:
            example: {"message": "Logout successful"}
      401:
        description: Unauthorized, user not logged in
        content:
          application/json:
            example: {"message": "Unauthorized, user not logged in"}
      405:
        description: Method not allowed
        content:
          application/json:
            example: {"message": "Method not allowed"}
    """
    if request.method == 'POST':
        if 'username' in session:
            session.pop('username', None)
            return jsonify({"message": "Logout successful"}), 200
        else:
            return jsonify({"message": "Unauthorized, user not logged in"}), 401

    # If not a POST request, return method not allowed
    return jsonify({"message": "Method not allowed"}), 405


@app.route('/add_product', methods=['POST'])
def add_product():
    """
    User add product to track endpoint.

    ---

    tags:
      - Product Management
    parameters:
      - name: product_url
        in: formData
        type: string
        description: Search for product details using the provided URL.
      - name: price_target
        in: formData
        type: double
        description: Set target price.
    responses:
      200:
        description: Add product to track successfully.
        content:
          application/json:
            example:
              {
                "currency": "ILS",
                "price target": 88,
                "product_name": "Topman oversized collarless jersey blazer in grey",
                "product_price": 175.81,
                "message": "Product added successfully"
              }

      401:
        description: User not logged in. Please log in.
        content:
          application/json:
            example: {"message": "User not logged in. Please log in."}

      400:
        description: Invalid product URL.
        content:
          application/json:
            example:
              value: {"message": "Invalid product URL."}

      402:
        description: Product already exists.
        content:
          application/json:
            example:
              value: {"message": "Product already exists for the user."}

      404:
        description: Product not found in the provided URL.
        content:
          application/json:
            example:
              value: {"message": "Product not found in the provided URL."}

      403:
        description: Error extracting product information.
        content:
          application/json:
            example:
              value: {"message": "Error extracting product information."}
    """

    if 'username' in session:
        if request.method == 'POST':
            app.logger.info(request.form)
            product_url = request.form.get('product_url')
            price_target = request.form.get('price_target')

            if not is_valid_asos_product_link(product_url):
                return jsonify({"message": "Invalid product URL."}), 400

            try:
                currency, product_name, initial_price = extract_info_from_url(product_url)
            except Exception as e:
                return jsonify({"message": "Error extracting product information."}), 403

            response_data = {
                'product_name': product_name,
                'product_price': initial_price,
                'currency': currency,
                'price target': price_target
            }

            username = session['username']
            user_id = get_user_id_by_username(username)

            if product_exists(user_id, product_name):
                return jsonify({"message": "Product already exists for the user."}), 402

            save_tracked_product(
                user_id,
                product_name,
                product_url,
                initial_price,
                price_target,
                initial_price,
                currency
            )

            response_data["message"] = "Product added successfully"
            return jsonify(response_data), 200

    else:
        return jsonify({"message": "User not logged in. Please log in."}), 401


@app.route('/price_comparison', methods=['GET', 'POST'])
def price_comparison():
    """
    Price comparison endpoint.

    ---

    tags:
      - Product Management
    parameters:
      - name: product_details
        in: formData
        type: string
        description: Product details for price comparison.

    responses:
      200:
        description: Price comparison successful.
        content:
          application/json:
            example:
              {
                "success": true,
                "data": [{"product_name": "Product 1", "price": 99.99}, {"product_name": "Product 2", "price": 129.99}]
              }

      400:
        description: Bad request, missing or invalid parameters.
        content:
          application/json:
            example: {"message": "Bad request"}

      404:
        description: Product not found for the provided details.
        content:
          application/json:
            example: {"message": "Product not found for the provided details."}
    """

    # Check if the request method is POST
    if request.method == 'POST':
        # Get product details from the form
        product_url = request.form.get('product_details')

        # Handle product basket search
        df_result = handle_product_basket_search(product_url)

        # Convert DataFrame result to JSON
        json_result = df_result.to_json(orient='records')

        # Prepare response data
        response_data = {
            'success': True,
            'data': json_result
        }

        return jsonify(response_data), 200

    # If not a POST request, return bad request
    return jsonify({"message": "Bad request"}), 400


if __name__ == '__main__':
    app.run(debug=True)
