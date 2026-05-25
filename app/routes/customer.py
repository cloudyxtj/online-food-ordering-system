from decimal import Decimal
from flask import Blueprint, abort, current_app, render_template, redirect, url_for, flash, session, request
from flask_login import login_required, current_user
from app import db
from app.models import FoodItem, Order, OrderItem
from app.services.audit_service import log_action

customer_bp = Blueprint("customer", __name__)


@customer_bp.route("/")
def catalog():
    items = FoodItem.query.filter(FoodItem.status.in_(["Available", "Sold Out"])).all()
    return render_template("customer/catalog.html", items=items)


@customer_bp.route("/cart")
@login_required
def view_cart():
    if current_user.role == 'Admin':
        abort(403)
    cart = session.get("cart", {})
    # Resolve names and prices from DB
    cart_items = {}
    for food_id, qty in cart.items():
        item = db.session.get(FoodItem, int(food_id))
        if item:
            cart_items[food_id] = {
                "name": item.food_name,
                "price": item.price,
                "qty": qty,
            }
    return render_template("customer/cart.html", cart_items=cart_items)


@customer_bp.route("/cart/add/<int:food_id>", methods=["POST"])
@login_required
def add_to_cart(food_id):
    if current_user.role == 'Admin':
        abort(403)
    item = db.session.get(FoodItem, food_id)
    if not item or item.status != "Available":
        flash("That item is not available.", "danger")
        return redirect(url_for("customer.catalog"))

    cart = session.get("cart", {})
    cart[str(food_id)] = cart.get(str(food_id), 0) + 1
    session["cart"] = cart
    flash(f"Added {item.food_name} to cart.", "success")
    return redirect(url_for("customer.catalog"))


@customer_bp.route("/cart/remove/<int:food_id>", methods=["POST"])
@login_required
def remove_from_cart(food_id):
    if current_user.role == 'Admin':
        abort(403)
    cart = session.get("cart", {})
    cart.pop(str(food_id), None)
    session["cart"] = cart
    flash("Item removed from cart.", "info")
    return redirect(url_for("customer.view_cart"))


@customer_bp.route("/checkout", methods=["POST"])
@login_required
def checkout():
    print(current_app.config["SQLALCHEMY_DATABASE_URI"])
    if current_user.role == 'Admin':
        abort(403)
    cart = session.get("cart", {})
    if not cart:
        flash("Your cart is empty.", "warning")
        return redirect(url_for("customer.view_cart"))

    total = Decimal("0.00")
    order_items_to_create = []

    for food_id_str, qty in cart.items():
        item = db.session.get(FoodItem, int(food_id_str))
        if not item or item.status != "Available":
            flash(f"Sorry, {item.food_name if item else 'an item'} is no longer available.", "danger")
            return redirect(url_for("customer.view_cart"))

        subtotal = Decimal(str(item.price)) * qty
        total += subtotal
        order_items_to_create.append((item, qty, subtotal))

    order = Order(
        user_id=current_user.user_id,
        total_price=total,
        order_status="Pending",
    )
    db.session.add(order)
    db.session.flush()  # get order_id

    for item, qty, subtotal in order_items_to_create:
        oi = OrderItem(
            order_id=order.order_id,
            food_id=item.food_id,
            quantity=qty,
            subtotal=subtotal,
        )
        db.session.add(oi)

    log_action(
        user_id=current_user.user_id,
        action_type="INSERT",
        description=f"Placed order #{order.order_id} for RM {total:.2f}",
        entity_type="orders",
        entity_id=order.order_id,
    )

    db.session.commit()
    session.pop("cart", None)

    flash(f"Order #{order.order_id} placed successfully!", "success")
    return redirect(url_for("customer.order_confirmation", order_id=order.order_id))


@customer_bp.route("/order/<int:order_id>")
@login_required
def order_confirmation(order_id):
    if current_user.role == 'Admin':
        abort(403)
    order = db.session.get(Order, order_id)
    if not order or order.user_id != current_user.user_id:
        flash("Order not found.", "danger")
        return redirect(url_for("customer.catalog"))
    return render_template("customer/confirmation.html", order=order)


@customer_bp.route("/orders")
@login_required
def order_history():
    if current_user.role == 'Admin':
        abort(403)
    orders = (
        Order.query
        .filter_by(user_id=current_user.user_id)
        .order_by(Order.created_at.desc())
        .all()
    )
    return render_template("customer/order_history.html", orders=orders)
