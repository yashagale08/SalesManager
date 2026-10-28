from flask import Flask, render_template, request, jsonify, Response
from mysql.connector import Error
from db import get_db_connection
from math import isfinite
import secrets
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import os
import hmac

app = Flask(__name__)


# --------------------------------------------------
# PROTECT THE REMOTE DEMO WITH A USERNAME AND PASSWORD
# --------------------------------------------------
@app.before_request
def protect_demo():
    username = os.getenv("DEMO_USERNAME")
    password = os.getenv("DEMO_PASSWORD")

    # Allow normal local development when demo credentials
    # have not been configured.
    if not username or not password:
        if request.remote_addr in ("127.0.0.1", "::1"):
            return None

        return Response(
            "Demo access has not been configured.",
            status=503,
            mimetype="text/plain"
        )

    auth = request.authorization

    if (
        auth is None
        or not hmac.compare_digest(auth.username or "", username)
        or not hmac.compare_digest(auth.password or "", password)
    ):
        return Response(
            "Login required.",
            status=401,
            headers={
                "WWW-Authenticate": 'Basic realm="SalesManager Demo"'
            },
            mimetype="text/plain"
        )


# ==================================================
# DASHBOARD
# ==================================================
@app.route("/")
def dashboard():
    database_status = "Disconnected"

    stats = {
        "total_sales": 0.0,
        "total_customers": 0,
        "outstanding_payments": 0.0,
        "total_products": 0
    }

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                (SELECT COUNT(*)
                 FROM customers) AS total_customers,

                (SELECT COUNT(*)
                 FROM products
                 WHERE is_active = 1) AS total_products,

                (SELECT COALESCE(SUM(total_amount), 0)
                 FROM sales) AS total_sales,

                (SELECT COALESCE(
                    SUM(GREATEST(total_amount - amount_paid, 0)), 0
                 )
                 FROM sales) AS outstanding_payments
        """)

        result = cursor.fetchone()

        if result:
            stats["total_sales"] = float(
                result["total_sales"] or 0
            )

            stats["total_customers"] = int(
                result["total_customers"] or 0
            )

            stats["outstanding_payments"] = float(
                result["outstanding_payments"] or 0
            )

            stats["total_products"] = int(
                result["total_products"] or 0
            )

        database_status = "Connected"

    except Error:
        app.logger.exception("Could not load dashboard statistics")

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()

    return render_template(
        "index.html",
        database_status=database_status,
        **stats
    )


# ==================================================
# PAGE ROUTES
# ==================================================
@app.route("/customers")
def customers_page():
    return render_template("customers.html")


@app.route("/products")
def products_page():
    return render_template("products.html")


@app.route("/sales")
def sales_page():
    return render_template("sales.html")


@app.route("/sales-history")
def sales_history_page():
    return render_template("sales_history.html")


@app.route("/payments")
def payments_page():
    return render_template("payments.html")


@app.route("/reports")
def reports_page():
    return render_template("reports.html")


# ==================================================
# CUSTOMERS API: VIEW CUSTOMERS / ADD CUSTOMER
# ==================================================
@app.route("/api/customers", methods=["GET", "POST"])
def customers_api():

    if request.method == "GET":
        connection = None
        cursor = None

        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)

            cursor.execute("""
                SELECT
                    customer_id,
                    name,
                    phone,
                    email,
                    address,
                    created_at
                FROM customers
                ORDER BY customer_id DESC
            """)

            customers = cursor.fetchall()

            for customer in customers:
                if customer["created_at"]:
                    customer["created_at"] = (
                        customer["created_at"].strftime("%d %b %Y")
                    )

            return jsonify(customers), 200

        except Error:
            app.logger.exception("Could not retrieve customers")

            return jsonify({
                "error": "Could not load customers."
            }), 500

        finally:
            if cursor:
                cursor.close()

            if connection and connection.is_connected():
                connection.close()

    data = request.get_json(silent=True) or {}

    name = (data.get("name") or "").strip()
    phone = (data.get("phone") or "").strip() or None
    email = (data.get("email") or "").strip() or None
    address = (data.get("address") or "").strip() or None

    if not name:
        return jsonify({
            "error": "Customer name is required."
        }), 400

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO customers (name, phone, email, address)
            VALUES (%s, %s, %s, %s)
            """,
            (name, phone, email, address)
        )

        connection.commit()
        customer_id = cursor.lastrowid

        return jsonify({
            "message": "Customer saved successfully.",
            "customer_id": customer_id
        }), 201

    except Error:
        if connection and connection.is_connected():
            connection.rollback()

        app.logger.exception("Could not save customer")

        return jsonify({
            "error": "Could not save customer."
        }), 500

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()


# ==================================================
# CUSTOMERS API: EDIT CUSTOMER
# ==================================================
@app.route("/api/customers/<int:customer_id>", methods=["PUT"])
def update_customer(customer_id):
    connection = None
    cursor = None

    data = request.get_json(silent=True) or {}

    name = (data.get("name") or "").strip()
    phone = (data.get("phone") or "").strip() or None
    email = (data.get("email") or "").strip() or None
    address = (data.get("address") or "").strip() or None

    if not name:
        return jsonify({
            "error": "Customer name is required."
        }), 400

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT customer_id
            FROM customers
            WHERE customer_id = %s
            """,
            (customer_id,)
        )

        if cursor.fetchone() is None:
            return jsonify({
                "error": "Customer not found."
            }), 404

        cursor.execute(
            """
            UPDATE customers
            SET
                name = %s,
                phone = %s,
                email = %s,
                address = %s
            WHERE customer_id = %s
            """,
            (name, phone, email, address, customer_id)
        )

        connection.commit()

        return jsonify({
            "message": "Customer updated successfully."
        }), 200

    except Error:
        if connection and connection.is_connected():
            connection.rollback()

        app.logger.exception("Could not update customer")

        return jsonify({
            "error": "Could not update customer."
        }), 500

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()


# ==================================================
# CUSTOMERS API: DELETE CUSTOMER
# ==================================================
@app.route("/api/customers/<int:customer_id>", methods=["DELETE"])
def delete_customer(customer_id):
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            DELETE FROM customers
            WHERE customer_id = %s
            """,
            (customer_id,)
        )

        if cursor.rowcount == 0:
            return jsonify({
                "error": "Customer not found."
            }), 404

        connection.commit()

        return jsonify({
            "message": "Customer deleted successfully."
        }), 200

    except Error:
        if connection and connection.is_connected():
            connection.rollback()

        app.logger.exception("Could not delete customer")

        return jsonify({
            "error": "Could not delete customer."
        }), 500

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()


# ==================================================
# PRODUCTS API: VIEW PRODUCTS / ADD PRODUCT
# ==================================================
@app.route("/api/products", methods=["GET", "POST"])
def products_api():

    if request.method == "GET":
        connection = None
        cursor = None

        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)

            cursor.execute("""
                SELECT
                    product_id,
                    name,
                    description,
                    current_price AS price,
                    stock_quantity,
                    created_at
                FROM products
                WHERE is_active = 1
                ORDER BY product_id DESC
            """)

            products = cursor.fetchall()

            for product in products:
                if product["price"] is not None:
                    product["price"] = float(product["price"])

                if product["stock_quantity"] is not None:
                    quantity = float(product["stock_quantity"])

                    product["stock_quantity"] = (
                        int(quantity)
                        if quantity.is_integer()
                        else quantity
                    )

                if product["created_at"]:
                    product["created_at"] = (
                        product["created_at"].strftime("%d %b %Y")
                    )

            return jsonify(products), 200

        except Error:
            app.logger.exception("Could not retrieve products")

            return jsonify({
                "error": "Could not load products."
            }), 500

        finally:
            if cursor:
                cursor.close()

            if connection and connection.is_connected():
                connection.close()

    data = request.get_json(silent=True) or {}

    name = str(data.get("name") or "").strip()
    description = (
        str(data.get("description") or "").strip() or None
    )

    if not name:
        return jsonify({
            "error": "Product name is required."
        }), 400

    try:
        price = float(data.get("price", 0))
        quantity_value = float(data.get("stock_quantity", 0))

        if (
            not isfinite(price)
            or price < 0
            or price > 9999999999.99
        ):
            raise ValueError("Invalid price.")

        if (
            not isfinite(quantity_value)
            or quantity_value < 0
            or quantity_value > 9999999999.99
        ):
            raise ValueError("Invalid stock quantity.")

        if not quantity_value.is_integer():
            return jsonify({
                "error": "Stock quantity must be a whole number."
            }), 400

        stock_quantity = int(quantity_value)

    except (ValueError, TypeError, OverflowError):
        return jsonify({
            "error": (
                "Enter a valid non-negative price "
                "and stock quantity."
            )
        }), 400

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO products
                (
                    name,
                    description,
                    current_price,
                    stock_quantity,
                    track_stock,
                    is_active
                )
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                name,
                description,
                price,
                stock_quantity,
                1,
                1
            )
        )

        connection.commit()
        product_id = cursor.lastrowid

        return jsonify({
            "message": "Product added successfully.",
            "product_id": product_id
        }), 201

    except Error:
        if connection and connection.is_connected():
            connection.rollback()

        app.logger.exception("Could not add product")

        return jsonify({
            "error": "Could not add product."
        }), 500

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()


# ==================================================
# PRODUCTS API: EDIT / UPDATE PRODUCT
# ==================================================
@app.route("/api/products/<int:product_id>", methods=["PUT"])
def update_product(product_id):
    connection = None
    cursor = None

    data = request.get_json(silent=True) or {}

    name = str(data.get("name") or "").strip()
    description = (
        str(data.get("description") or "").strip() or None
    )

    if not name:
        return jsonify({
            "error": "Product name is required."
        }), 400

    try:
        price = float(data.get("price"))
        quantity_value = float(data.get("stock_quantity"))

        if (
            not isfinite(price)
            or price < 0
            or price > 9999999999.99
        ):
            raise ValueError("Invalid price.")

        if (
            not isfinite(quantity_value)
            or quantity_value < 0
            or quantity_value > 9999999999.99
        ):
            raise ValueError("Invalid stock quantity.")

        if not quantity_value.is_integer():
            return jsonify({
                "error": "Stock quantity must be a whole number."
            }), 400

        stock_quantity = int(quantity_value)

    except (ValueError, TypeError, OverflowError):
        return jsonify({
            "error": (
                "Enter a valid non-negative price "
                "and stock quantity."
            )
        }), 400

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT product_id
            FROM products
            WHERE product_id = %s AND is_active = 1
            """,
            (product_id,)
        )

        if cursor.fetchone() is None:
            return jsonify({
                "error": "Product not found."
            }), 404

        cursor.execute(
            """
            UPDATE products
            SET
                name = %s,
                description = %s,
                current_price = %s,
                stock_quantity = %s,
                track_stock = 1
            WHERE product_id = %s AND is_active = 1
            """,
            (
                name,
                description,
                price,
                stock_quantity,
                product_id
            )
        )

        connection.commit()

        return jsonify({
            "message": "Product updated successfully."
        }), 200

    except Error:
        if connection and connection.is_connected():
            connection.rollback()

        app.logger.exception("Could not update product")

        return jsonify({
            "error": "Could not update product."
        }), 500

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()


# ==================================================
# PRODUCTS API: REMOVE PRODUCT FROM ACTIVE INVENTORY
# ==================================================
@app.route("/api/products/<int:product_id>", methods=["DELETE"])
def delete_product(product_id):
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        # Soft-delete: preserve the record in the database.
        cursor.execute(
            """
            UPDATE products
            SET is_active = 0
            WHERE product_id = %s AND is_active = 1
            """,
            (product_id,)
        )

        if cursor.rowcount == 0:
            return jsonify({
                "error": "Product not found or already removed."
            }), 404

        connection.commit()

        return jsonify({
            "message": "Product removed from active inventory."
        }), 200

    except Error:
        if connection and connection.is_connected():
            connection.rollback()

        app.logger.exception("Could not remove product")

        return jsonify({
            "error": "Could not remove product."
        }), 500

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()


# --------------------------------------------------
# SALES API: CREATE AND SAVE AN INVOICE
# --------------------------------------------------
@app.route("/api/sales", methods=["POST"])
def create_sale():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "Invalid invoice data."}), 400

    # --------------------------------------------------
    # DELIVERY DETAILS
    # --------------------------------------------------
    delivery_address = str(
        data.get("delivery_address") or ""
    ).strip()

    delivery_landmark = str(
        data.get("delivery_landmark") or ""
    ).strip() or None

    delivery_instructions = str(
        data.get("delivery_instructions") or ""
    ).strip() or None

    if not delivery_address:
        return jsonify({
            "error": "Delivery address is required."
        }), 400

    if len(delivery_address) > 1500:
        return jsonify({
            "error": "Delivery address cannot exceed 1500 characters."
        }), 400

    if delivery_landmark and len(delivery_landmark) > 255:
        return jsonify({
            "error": "Landmark cannot exceed 255 characters."
        }), 400

    if delivery_instructions and len(delivery_instructions) > 2000:
        return jsonify({
            "error": (
                "Delivery instructions cannot exceed "
                "2000 characters."
            )
        }), 400

    # Validate customer ID
    try:
        raw_customer_id = data.get("customer_id")

        if isinstance(raw_customer_id, bool):
            raise ValueError()

        customer_id = int(raw_customer_id)

        if customer_id <= 0:
            raise ValueError()

        if (
            isinstance(raw_customer_id, float)
            and not raw_customer_id.is_integer()
        ):
            raise ValueError()

    except (ValueError, TypeError, OverflowError):
        return jsonify({
            "error": "Please select a valid customer."
        }), 400

    # Validate and combine invoice items
    raw_items = data.get("items")

    if not isinstance(raw_items, list) or not raw_items:
        return jsonify({
            "error": "Add at least one product to the invoice."
        }), 400

    if len(raw_items) > 100:
        return jsonify({
            "error": (
                "An invoice cannot contain more than "
                "100 item entries."
            )
        }), 400

    requested_quantities = {}

    try:
        for item in raw_items:
            if not isinstance(item, dict):
                raise ValueError()

            raw_product_id = item.get("product_id")

            if isinstance(raw_product_id, bool):
                raise ValueError()

            product_id = int(raw_product_id)

            if product_id <= 0:
                raise ValueError()

            if (
                isinstance(raw_product_id, float)
                and not raw_product_id.is_integer()
            ):
                raise ValueError()

            quantity_value = Decimal(str(item.get("quantity")))

            if (
                not quantity_value.is_finite()
                or quantity_value <= 0
                or quantity_value != quantity_value.to_integral_value()
                or quantity_value > Decimal("1000000")
            ):
                raise ValueError()

            quantity = int(quantity_value)

            requested_quantities[product_id] = (
                requested_quantities.get(product_id, 0) + quantity
            )

            if requested_quantities[product_id] > 1000000:
                raise ValueError()

    except (ValueError, TypeError, InvalidOperation, OverflowError):
        return jsonify({
            "error": (
                "Each product must have a valid ID and "
                "positive whole-number quantity."
            )
        }), 400

    # Validate monetary values on the server
    def parse_money(value, field_name):
        try:
            amount = Decimal(str(0 if value is None else value))
        except (InvalidOperation, ValueError, TypeError):
            raise ValueError(
                f"{field_name} must be a valid amount."
            )

        if (
            not amount.is_finite()
            or amount < 0
            or amount > Decimal("9999999999.99")
        ):
            raise ValueError(
                f"{field_name} must be a non-negative amount."
            )

        return amount.quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

    try:
        discount = parse_money(
            data.get("discount_amount", 0), "Discount"
        )
        tax = parse_money(
            data.get("tax_amount", 0), "Tax"
        )
        amount_paid = parse_money(
            data.get("amount_paid", 0), "Amount paid"
        )
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        connection.start_transaction()
        cursor = connection.cursor(dictionary=True)

        # Confirm the customer exists
        cursor.execute(
            """
            SELECT customer_id
            FROM customers
            WHERE customer_id = %s
            """,
            (customer_id,)
        )

        if cursor.fetchone() is None:
            connection.rollback()
            return jsonify({"error": "Customer not found."}), 404

        # Lock and validate products, then calculate prices from MySQL.
        prepared_items = []
        subtotal = Decimal("0.00")

        for product_id in sorted(requested_quantities):
            quantity = requested_quantities[product_id]

            cursor.execute(
                """
                SELECT
                    product_id,
                    name,
                    current_price,
                    stock_quantity,
                    track_stock
                FROM products
                WHERE product_id = %s
                  AND is_active = 1
                FOR UPDATE
                """,
                (product_id,)
            )

            product = cursor.fetchone()

            if product is None:
                connection.rollback()
                return jsonify({
                    "error": (
                        f"Product {product_id} was not found "
                        "or is inactive."
                    )
                }), 404

            unit_price = Decimal(str(product["current_price"]))
            stock_quantity = Decimal(str(product["stock_quantity"]))
            track_stock = bool(product["track_stock"])

            # Prevent selling more than the available tracked stock.
            if (
                track_stock
                and stock_quantity < Decimal(quantity)
            ):
                connection.rollback()
                return jsonify({
                    "error": (
                        f"Not enough stock for {product['name']}. "
                        f"Available quantity: {stock_quantity}"
                    )
                }), 400

            line_total = (unit_price * quantity).quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP
            )

            subtotal += line_total

            prepared_items.append({
                "product_id": product_id,
                "product_name": product["name"],
                "quantity": quantity,
                "unit_price": unit_price,
                "line_total": line_total,
                "track_stock": track_stock
            })

        subtotal = subtotal.quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

        if subtotal > Decimal("9999999999.99"):
            connection.rollback()
            return jsonify({
                "error": "Invoice subtotal exceeds the supported limit."
            }), 400

        if discount > subtotal:
            connection.rollback()
            return jsonify({
                "error": "Discount cannot exceed the invoice subtotal."
            }), 400

        total = (subtotal - discount + tax).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

        if total > Decimal("9999999999.99"):
            connection.rollback()
            return jsonify({
                "error": "Invoice total exceeds the supported limit."
            }), 400

        if amount_paid > total:
            connection.rollback()
            return jsonify({
                "error": "Amount paid cannot exceed the invoice total."
            }), 400

        if amount_paid >= total:
            payment_status = "Paid"
        elif amount_paid > 0:
            payment_status = "Partially Paid"
        else:
            payment_status = "Unpaid"

        # Generate a unique invoice number.
        invoice_number = (
            f"INV-{datetime.now().strftime('%Y%m%d%H%M%S')}-"
            f"{secrets.token_hex(3).upper()}"
        )

        # Save invoice and delivery details.
        cursor.execute(
            """
            INSERT INTO sales (
                invoice_number,
                customer_id,
                subtotal,
                discount_amount,
                tax_amount,
                total_amount,
                amount_paid,
                payment_status,
                delivery_address,
                delivery_landmark,
                delivery_instructions
            )
            VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            """,
            (
                invoice_number,
                customer_id,
                subtotal,
                discount,
                tax,
                total,
                amount_paid,
                payment_status,
                delivery_address,
                delivery_landmark,
                delivery_instructions
            )
        )

        sale_id = cursor.lastrowid

        # Save invoice items and update tracked stock.
        for item in prepared_items:
            cursor.execute(
                """
                INSERT INTO sale_items (
                    sale_id,
                    product_id,
                    product_name,
                    quantity,
                    unit_price,
                    line_total
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    sale_id,
                    item["product_id"],
                    item["product_name"],
                    item["quantity"],
                    item["unit_price"],
                    item["line_total"]
                )
            )

            if item["track_stock"]:
                cursor.execute(
                    """
                    UPDATE products
                    SET stock_quantity = stock_quantity - %s
                    WHERE product_id = %s
                      AND is_active = 1
                      AND track_stock = 1
                      AND stock_quantity >= %s
                    """,
                    (
                        item["quantity"],
                        item["product_id"],
                        item["quantity"]
                    )
                )

                if cursor.rowcount != 1:
                    raise RuntimeError(
                        "Stock changed while saving the invoice. "
                        "Please refresh and try again."
                    )

        # Commit invoice, delivery details, items and stock changes together.
        connection.commit()

        return jsonify({
            "message": "Invoice saved successfully.",
            "sale_id": sale_id,
            "invoice_number": invoice_number,
            "subtotal": float(subtotal),
            "discount_amount": float(discount),
            "tax_amount": float(tax),
            "total_amount": float(total),
            "amount_paid": float(amount_paid),
            "payment_status": payment_status
        }), 201

    except Error:
        if connection and connection.is_connected():
            connection.rollback()

        app.logger.exception("Could not save invoice")

        return jsonify({
            "error": "Could not save invoice. Check the Flask terminal."
        }), 500

    except RuntimeError as error:
        if connection and connection.is_connected():
            connection.rollback()

        app.logger.warning("Invoice not saved: %s", error)

        return jsonify({"error": str(error)}), 409

    except Exception:
        if connection and connection.is_connected():
            connection.rollback()

        app.logger.exception("Unexpected invoice error")

        return jsonify({
            "error": (
                "An unexpected error occurred while saving the invoice."
            )
        }), 500

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()


# --------------------------------------------------
# INVOICE HISTORY API: GET SAVED INVOICES
# --------------------------------------------------
@app.route("/api/sales-history", methods=["GET"])
def sales_history_api():
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                s.sale_id,
                s.invoice_number,
                s.sale_date,
                s.subtotal,
                s.discount_amount,
                s.tax_amount,
                s.total_amount,
                s.amount_paid,
                s.payment_status,
                c.name AS customer_name
            FROM sales AS s
            INNER JOIN customers AS c
                ON s.customer_id = c.customer_id
            ORDER BY s.sale_id DESC
        """)

        invoices = cursor.fetchall()

        for invoice in invoices:
            for field in (
                "subtotal",
                "discount_amount",
                "tax_amount",
                "total_amount",
                "amount_paid"
            ):
                if invoice[field] is not None:
                    invoice[field] = float(invoice[field])

            if invoice["sale_date"]:
                invoice["sale_date"] = (
                    invoice["sale_date"].strftime(
                        "%d %b %Y, %I:%M %p"
                    )
                )

        return jsonify(invoices), 200

    except Error:
        app.logger.exception("Could not retrieve invoice history")

        return jsonify({
            "error": "Could not load invoice history."
        }), 500

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()


# --------------------------------------------------
# PAYMENTS API: VIEW INVOICES / RECORD PAYMENTS
# --------------------------------------------------
@app.route("/api/payments", methods=["GET", "POST"])
def payments_api():

    # GET: Retrieve invoices and payment history
    if request.method == "GET":
        connection = None
        cursor = None

        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)

            cursor.execute("""
                SELECT
                    s.sale_id,
                    s.invoice_number,
                    c.name AS customer_name,
                    s.sale_date,
                    s.total_amount,
                    s.amount_paid,
                    GREATEST(
                        s.total_amount - s.amount_paid, 0
                    ) AS outstanding_balance,
                    s.payment_status
                FROM sales s
                INNER JOIN customers c
                    ON s.customer_id = c.customer_id
                ORDER BY s.sale_id DESC
            """)

            invoices = cursor.fetchall()

            for invoice in invoices:
                for field in (
                    "total_amount",
                    "amount_paid",
                    "outstanding_balance"
                ):
                    invoice[field] = float(invoice[field] or 0)

                if invoice["sale_date"]:
                    invoice["sale_date"] = (
                        invoice["sale_date"].strftime(
                            "%d %b %Y, %I:%M %p"
                        )
                    )

            cursor.execute("""
                SELECT
                    p.payment_id,
                    p.sale_id,
                    s.invoice_number,
                    c.name AS customer_name,
                    p.amount,
                    p.payment_method,
                    p.reference_number,
                    p.notes,
                    p.payment_date
                FROM payments p
                INNER JOIN sales s
                    ON p.sale_id = s.sale_id
                INNER JOIN customers c
                    ON s.customer_id = c.customer_id
                ORDER BY p.payment_id DESC
            """)

            payment_records = cursor.fetchall()

            for payment in payment_records:
                payment["amount"] = float(payment["amount"] or 0)

                if payment["payment_date"]:
                    payment["payment_date"] = (
                        payment["payment_date"].strftime(
                            "%d %b %Y, %I:%M %p"
                        )
                    )

            return jsonify({
                "invoices": invoices,
                "payments": payment_records
            }), 200

        except Error:
            app.logger.exception("Could not retrieve payment records")

            return jsonify({
                "error": "Could not load payment records."
            }), 500

        finally:
            if cursor:
                cursor.close()

            if connection and connection.is_connected():
                connection.close()

    # POST: Record a payment against an invoice
    data = request.get_json(silent=True) or {}

    if not isinstance(data, dict):
        return jsonify({"error": "Invalid payment data."}), 400

    try:
        raw_sale_id = data.get("sale_id")

        if isinstance(raw_sale_id, bool):
            raise ValueError()

        sale_id = int(raw_sale_id)

        if sale_id <= 0:
            raise ValueError()

        if (
            isinstance(raw_sale_id, float)
            and not raw_sale_id.is_integer()
        ):
            raise ValueError()

    except (ValueError, TypeError, OverflowError):
        return jsonify({
            "error": "Please select a valid invoice."
        }), 400

    try:
        amount = Decimal(str(data.get("amount")))

        if (
            not amount.is_finite()
            or amount <= 0
            or amount > Decimal("9999999999.99")
        ):
            raise ValueError()

        rounded_amount = amount.quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

        if amount != rounded_amount:
            raise ValueError()

        amount = rounded_amount

    except (InvalidOperation, ValueError, TypeError):
        return jsonify({
            "error": (
                "Enter a valid payment amount greater than zero, "
                "with at most two decimal places."
            )
        }), 400

    payment_method = str(
        data.get("payment_method") or "Cash"
    ).strip()

    allowed_methods = {
        "Cash",
        "UPI",
        "Bank Transfer",
        "Card",
        "Cheque",
        "Other"
    }

    if payment_method not in allowed_methods:
        return jsonify({
            "error": "Choose a valid payment method."
        }), 400

    reference_number = (
        str(data.get("reference_number") or "").strip() or None
    )

    notes = str(data.get("notes") or "").strip() or None

    if reference_number and len(reference_number) > 100:
        return jsonify({
            "error": "Reference number cannot exceed 100 characters."
        }), 400

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        connection.start_transaction()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                sale_id,
                invoice_number,
                total_amount,
                amount_paid
            FROM sales
            WHERE sale_id = %s
            FOR UPDATE
        """, (sale_id,))

        invoice = cursor.fetchone()

        if invoice is None:
            connection.rollback()
            return jsonify({"error": "Invoice not found."}), 404

        total_amount = Decimal(str(invoice["total_amount"]))
        previous_paid = Decimal(str(invoice["amount_paid"] or 0))
        balance = total_amount - previous_paid

        if balance <= 0:
            connection.rollback()
            return jsonify({
                "error": "This invoice has already been fully paid."
            }), 400

        if amount > balance:
            connection.rollback()
            return jsonify({
                "error": (
                    "Payment exceeds the outstanding balance of "
                    f"{balance:.2f}."
                )
            }), 400

        new_amount_paid = previous_paid + amount

        if new_amount_paid >= total_amount:
            new_status = "Paid"
        else:
            new_status = "Partially Paid"

        cursor.execute("""
            INSERT INTO payments (
                sale_id,
                amount,
                payment_method,
                reference_number,
                notes
            )
            VALUES (%s, %s, %s, %s, %s)
        """, (
            sale_id,
            amount,
            payment_method,
            reference_number,
            notes
        ))

        payment_id = cursor.lastrowid

        cursor.execute("""
            UPDATE sales
            SET
                amount_paid = %s,
                payment_status = %s
            WHERE sale_id = %s
        """, (
            new_amount_paid,
            new_status,
            sale_id
        ))

        connection.commit()

        return jsonify({
            "message": "Payment recorded successfully.",
            "payment_id": payment_id,
            "invoice_number": invoice["invoice_number"],
            "amount_paid": float(new_amount_paid),
            "outstanding_balance": float(
                total_amount - new_amount_paid
            ),
            "payment_status": new_status
        }), 201

    except Error:
        if connection and connection.is_connected():
            connection.rollback()

        app.logger.exception("Could not record payment")

        return jsonify({
            "error": "Could not record payment."
        }), 500

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()


# --------------------------------------------------
# REPORTS API: BUSINESS STATISTICS AND SALES HISTORY
# --------------------------------------------------
@app.route("/api/reports", methods=["GET"])
def reports_api():
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # Business summary
        cursor.execute("""
            SELECT
                (SELECT COALESCE(SUM(total_amount), 0)
                 FROM sales) AS total_sales,

                (SELECT COALESCE(SUM(amount), 0)
                 FROM payments) AS payments_collected,

                (SELECT COALESCE(
                    SUM(GREATEST(total_amount - amount_paid, 0)), 0
                 )
                 FROM sales) AS outstanding_balance,

                (SELECT COUNT(*)
                 FROM sales) AS invoice_count,

                (SELECT COUNT(*)
                 FROM sales
                 WHERE amount_paid < total_amount) AS pending_invoice_count,

                (SELECT COUNT(*)
                 FROM customers) AS customer_count,

                (SELECT COUNT(*)
                 FROM products
                 WHERE is_active = 1) AS active_product_count
        """)

        summary = cursor.fetchone()

        for field in (
            "total_sales",
            "payments_collected",
            "outstanding_balance"
        ):
            summary[field] = float(summary[field] or 0)

        for field in (
            "invoice_count",
            "pending_invoice_count",
            "customer_count",
            "active_product_count"
        ):
            summary[field] = int(summary[field] or 0)

        # Monthly sales totals for the last six calendar months
        cursor.execute("""
            SELECT
                DATE_FORMAT(sale_date, '%Y-%m') AS month_key,
                DATE_FORMAT(sale_date, '%b %Y') AS month_label,
                COALESCE(SUM(total_amount), 0) AS sales_total,
                COUNT(*) AS invoice_count
            FROM sales
            WHERE sale_date >= DATE_SUB(
                DATE_FORMAT(CURDATE(), '%Y-%m-01'),
                INTERVAL 5 MONTH
            )
            GROUP BY
                DATE_FORMAT(sale_date, '%Y-%m'),
                DATE_FORMAT(sale_date, '%b %Y')
            ORDER BY month_key ASC
        """)

        monthly_sales = cursor.fetchall()

        for month in monthly_sales:
            month["sales_total"] = float(
                month["sales_total"] or 0
            )
            month["invoice_count"] = int(
                month["invoice_count"] or 0
            )
            month.pop("month_key", None)

        # Payment status counts for the dashboard chart
        cursor.execute("""
            SELECT
                COALESCE(
                    payment_status,
                    'Unspecified'
                ) AS payment_status,
                COUNT(*) AS invoice_count
            FROM sales
            GROUP BY COALESCE(
                payment_status,
                'Unspecified'
            )
            ORDER BY payment_status ASC
        """)

        payment_status_breakdown = cursor.fetchall()

        for item in payment_status_breakdown:
            item["invoice_count"] = int(
                item["invoice_count"] or 0
            )

        # Latest ten invoices
        cursor.execute("""
            SELECT
                s.sale_id,
                s.invoice_number,
                s.sale_date,
                c.name AS customer_name,
                s.total_amount,
                s.amount_paid,
                GREATEST(
                    s.total_amount - s.amount_paid, 0
                ) AS outstanding_balance,
                s.payment_status
            FROM sales AS s
            INNER JOIN customers AS c
                ON s.customer_id = c.customer_id
            ORDER BY s.sale_id DESC
            LIMIT 10
        """)

        recent_invoices = cursor.fetchall()

        for invoice in recent_invoices:
            for field in (
                "total_amount",
                "amount_paid",
                "outstanding_balance"
            ):
                invoice[field] = float(invoice[field] or 0)

            if invoice["sale_date"]:
                invoice["sale_date"] = invoice["sale_date"].strftime(
                    "%d %b %Y, %I:%M %p"
                )

        return jsonify({
            "summary": summary,
            "monthly_sales": monthly_sales,
            "payment_status_breakdown": payment_status_breakdown,
            "recent_invoices": recent_invoices
        }), 200

    except Error:
        app.logger.exception("Could not generate reports")

        return jsonify({
            "error": "Could not generate reports. Check the Flask terminal."
        }), 500

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()


# --------------------------------------------------
# PRINTABLE INVOICE PAGE
# --------------------------------------------------
@app.route("/sales/<int:sale_id>/invoice")
def sales_invoice_page(sale_id):
    return render_template("invoice.html", sale_id=sale_id)


# --------------------------------------------------
# INVOICE API: GET INVOICE AND ITEM DETAILS
# --------------------------------------------------
@app.route("/api/sales/<int:sale_id>/invoice", methods=["GET"])
def get_invoice_details(sale_id):
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # Retrieve invoice, delivery and customer details
        cursor.execute("""
            SELECT
                s.sale_id,
                s.invoice_number,
                s.sale_date,
                s.subtotal,
                s.discount_amount,
                s.tax_amount,
                s.total_amount,
                s.amount_paid,
                s.payment_status,
                s.delivery_address,
                s.delivery_landmark,
                s.delivery_instructions,
                c.customer_id,
                c.name AS customer_name,
                c.phone AS customer_phone,
                c.email AS customer_email,
                c.address AS customer_address
            FROM sales AS s
            INNER JOIN customers AS c
                ON s.customer_id = c.customer_id
            WHERE s.sale_id = %s
        """, (sale_id,))

        invoice = cursor.fetchone()

        if invoice is None:
            return jsonify({
                "error": "Invoice not found."
            }), 404

        # Retrieve products saved with this invoice
        cursor.execute("""
            SELECT
                sale_item_id,
                product_id,
                product_name,
                quantity,
                unit_price,
                line_total
            FROM sale_items
            WHERE sale_id = %s
            ORDER BY sale_item_id ASC
        """, (sale_id,))

        items = cursor.fetchall()

        # Convert database values into JSON-compatible values
        money_fields = (
            "subtotal",
            "discount_amount",
            "tax_amount",
            "total_amount",
            "amount_paid"
        )

        for field in money_fields:
            invoice[field] = float(invoice[field] or 0)

        if invoice["sale_date"]:
            invoice["sale_date"] = invoice["sale_date"].strftime(
                "%d %b %Y, %I:%M %p"
            )

        for item in items:
            item["quantity"] = float(item["quantity"] or 0)
            item["unit_price"] = float(item["unit_price"] or 0)
            item["line_total"] = float(item["line_total"] or 0)

        outstanding = max(
            0,
            invoice["total_amount"] - invoice["amount_paid"]
        )

        return jsonify({
            "invoice": invoice,
            "items": items,
            "outstanding_balance": round(outstanding, 2)
        }), 200

    except Error:
        app.logger.exception("Could not retrieve invoice details")

        return jsonify({
            "error": "Could not load invoice details."
        }), 500

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()


# ==================================================
# RUN FLASK APPLICATION
# ==================================================
if __name__ == "__main__":
    app.run(debug=True)