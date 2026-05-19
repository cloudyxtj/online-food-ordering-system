"""Authentication routes (Register, Login, Logout).

Covers user onboarding and session management.
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models import User
from app.forms import RegisterForm, LoginForm
from app.services.audit_service import log_action

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        existing = User.query.filter_by(email=email).first()
        if existing:
            flash("An account with this email already exists.", "danger")
            return render_template("auth/register.html", form=form)

        user = User(
            name=form.name.data.strip(),
            email=email,
            role="Customer",
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        flash("Registration successful! Please login.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        user = User.query.filter_by(email=email).first()

        if user and user.is_locked():
            log_action(
                user_id=user.user_id,
                action_type="LOGIN_BLOCKED",
                description=f"Login blocked — account locked: {email}",
                entity_type="user",
                entity_id=user.user_id,
            )
            db.session.commit()
            flash("Account is temporarily locked due to too many failed attempts. Try again in 5 minutes.", "danger")
            return render_template("auth/login.html", form=form)

        if user and user.check_password(form.password.data):
            if not user.is_active:
                flash("This account has been disabled.", "danger")
                return render_template("auth/login.html", form=form)

            user.reset_login_attempts()
            db.session.commit()
            login_user(user)

            log_action(
                user_id=user.user_id,
                action_type="LOGIN_SUCCESS",
                description=f"Successful login: {email}",
                entity_type="user",
                entity_id=user.user_id,
            )
            db.session.commit()

            flash(f"Welcome back, {user.name}!", "success")
            if user.is_admin:
                return redirect(url_for("admin.dashboard"))
            return redirect(url_for("customer.catalog"))

        # Failed login
        if user:
            user.register_failed_login()
            if user.is_locked():
                log_action(
                    user_id=user.user_id,
                    action_type="ACCOUNT_LOCKED",
                    description=f"Account locked after repeated failed logins: {email}",
                    entity_type="user",
                    entity_id=user.user_id,
                )
            else:
                log_action(
                    user_id=user.user_id,
                    action_type="LOGIN_FAILED",
                    description=f"Failed login attempt ({user.failed_login_attempts}/5): {email}",
                    entity_type="user",
                    entity_id=user.user_id,
                )
            db.session.commit()

        flash("Invalid email or password.", "danger")

    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    log_action(
        user_id=current_user.user_id,
        action_type="LOGOUT",
        description=f"User logged out: {current_user.email}",
        entity_type="user",
        entity_id=current_user.user_id,
    )
    db.session.commit()
    logout_user()
    session.pop("cart", None)
    flash("You have been logged out.", "info")
    return redirect(url_for("customer.catalog"))
