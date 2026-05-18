from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login_manager


class User(UserMixin, db.Model):
    __tablename__ = "user"

    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="Customer")  # Customer | Admin
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    orders = db.relationship("Order", backref="customer", lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        return str(self.user_id)

    @property
    def is_admin(self):
        return self.role == "Admin"


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


class FoodItem(db.Model):
    __tablename__ = "food_items"

    food_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    food_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="Available")  # Available | Sold Out | Hidden

    order_items = db.relationship("OrderItem", backref="food_item", lazy=True)


class Order(db.Model):
    __tablename__ = "orders"

    order_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.user_id"), nullable=False)
    total_price = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)
    order_status = db.Column(db.String(20), nullable=False, default="Pending")  # Pending | Completed | Cancelled
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    items = db.relationship("OrderItem", backref="order", lazy=True, cascade="all, delete-orphan")


class OrderItem(db.Model):
    __tablename__ = "order_items"

    order_item_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.order_id"), nullable=False)
    food_id = db.Column(db.Integer, db.ForeignKey("food_items.food_id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    subtotal = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    log_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.user_id"), nullable=True)
    action_type = db.Column(db.String(50), nullable=False)  # INSERT | UPDATE | DELETE
    action_description = db.Column(db.Text, nullable=False)
    entity_type = db.Column(db.String(50), nullable=False)
    entity_id = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    user = db.relationship("User", backref="audit_logs", lazy=True)
