"""Admin routes — Manage Food Catalog, Manage Orders, Audit Logs View.

FR1: RBAC — all routes require Admin role.
FR2: CRUD — add, edit, toggle food items.
FR3: Audit Trail — all sensitive actions are logged.
"""
from decimal import Decimal, InvalidOperation
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from functools import wraps
from app import db
from app.models import FoodItem, Order, AuditLog
from app.forms import FoodItemForm
from app.services.audit_service import log_action

admin_bp = Blueprint("admin", __name__)


def admin_required(f):
    """Decorator to restrict views to Admin users (FR1: RBAC)."""
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_admin:
            flash("Admin access required.", "danger")
            return redirect(url_for("customer.catalog"))
        return f(*args, **kwargs)
    return decorated


@admin_bp.route("/dashboard")
@admin_required
def dashboard():
    """Admin dashboard — manage food items."""
    items = FoodItem.query.all()
    form = FoodItemForm()
    return render_template("admin/dashboard.html", items=items, form=form)


@admin_bp.route("/food/add", methods=["POST"])
@admin_required
def add_food():
    """Add a new food item (FR2: CREATE)."""
    form = FoodItemForm()
    if form.validate_on_submit():
        item = FoodItem(
            food_name=form.food_name.data.strip(),
            description=form.description.data.strip() if form.description.data else "",
            price=form.price.data,
            status=form.status.data,
        )
        db.session.add(item)
        db.session.flush()

        log_action(
            user_id=current_user.user_id,
            action_type="INSERT",
            description=f"Added new food item: {item.food_name} (RM {item.price:.2f})",
            entity_type="food_items",
            entity_id=item.food_id,
        )
        db.session.commit()
        flash(f"Food item '{item.food_name}' added successfully!", "success")
    else:
        for field, errors in form.errors.items():
            for err in errors:
                flash(f"{field}: {err}", "danger")

    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/food/edit/<int:food_id>", methods=["POST"])
@admin_required
def edit_food(food_id):
    """Edit an existing food item (FR2: UPDATE)."""
    item = db.session.get(FoodItem, food_id)
    if not item:
        flash("Food item not found.", "danger")
        return redirect(url_for("admin.dashboard"))

    food_name = request.form.get("food_name", "").strip()
    description = request.form.get("description", "").strip()
    price_str = request.form.get("price", "").strip()
    status = request.form.get("status", "Available")

    try:
        price = Decimal(price_str)
    except (InvalidOperation, TypeError):
        flash("Invalid price value.", "danger")
        return redirect(url_for("admin.dashboard"))

    if not food_name:
        flash("Food name is required.", "danger")
        return redirect(url_for("admin.dashboard"))

    old_name = item.food_name
    item.food_name = food_name
    item.description = description
    item.price = price
    item.status = status

    log_action(
        user_id=current_user.user_id,
        action_type="UPDATE",
        description=f"Updated food item #{food_id}: {old_name} → {food_name}",
        entity_type="food_items",
        entity_id=food_id,
    )
    db.session.commit()
    flash(f"Food item '{food_name}' updated.", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/food/toggle/<int:food_id>", methods=["POST"])
@admin_required
def toggle_food(food_id):
    """Toggle food item status between Available and Sold Out."""
    item = db.session.get(FoodItem, food_id)
    if not item:
        flash("Food item not found.", "danger")
        return redirect(url_for("admin.dashboard"))

    old_status = item.status
    item.status = "Sold Out" if item.status == "Available" else "Available"

    log_action(
        user_id=current_user.user_id,
        action_type="UPDATE",
        description=f"Toggled food item #{food_id} status: {old_status} → {item.status}",
        entity_type="food_items",
        entity_id=food_id,
    )
    db.session.commit()
    flash(f"'{item.food_name}' status changed to {item.status}.", "info")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/food/delete/<int:food_id>", methods=["POST"])
@admin_required
def delete_food(food_id):
    """Delete a food item (FR2: DELETE)."""
    item = db.session.get(FoodItem, food_id)
    if not item:
        flash("Food item not found.", "danger")
        return redirect(url_for("admin.dashboard"))
    food_name = item.food_name
    db.session.delete(item)
    log_action(
        user_id=current_user.user_id,
        action_type="DELETE",
        description=f"Deleted food item: {food_name}",
        entity_type="food_items",
        entity_id=food_id,
    )
    db.session.commit()
    flash(f"Food item '{food_name}' deleted.", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/orders")
@admin_required
def orders():
    """View all customer orders."""
    all_orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template("admin/orders.html", orders=all_orders)


@admin_bp.route("/orders/update/<int:order_id>", methods=["POST"])
@admin_required
def update_order_status(order_id):
    """Update order status (Pending → Completed / Cancelled)."""
    order = db.session.get(Order, order_id)
    if not order:
        flash("Order not found.", "danger")
        return redirect(url_for("admin.orders"))

    new_status = request.form.get("status", "")
    if new_status not in ("Completed", "Cancelled"):
        flash("Invalid status.", "danger")
        return redirect(url_for("admin.orders"))

    old_status = order.order_status
    order.order_status = new_status

    log_action(
        user_id=current_user.user_id,
        action_type="UPDATE",
        description=f"Updated order #{order_id}: {old_status} → {new_status}",
        entity_type="orders",
        entity_id=order_id,
    )
    db.session.commit()
    flash(f"Order #{order_id} marked as {new_status}.", "success")
    return redirect(url_for("admin.orders"))


@admin_bp.route("/audit")
@admin_required
def audit():
    """View audit logs (read-only, FR3)."""
    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).all()
    return render_template("admin/audit_logs.html", logs=logs)
