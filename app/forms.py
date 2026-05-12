"""WTForms for input validation across all modules.

Covers register, login, add/edit food items.
"""
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, DecimalField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Email, Length, EqualTo, NumberRange


class RegisterForm(FlaskForm):
    name = StringField("Full Name", validators=[DataRequired(), Length(max=100)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=150)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField(
        "Confirm Password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match.")],
    )


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])


class FoodItemForm(FlaskForm):
    food_name = StringField("Food Name", validators=[DataRequired(), Length(max=100)])
    description = TextAreaField("Description", validators=[Length(max=500)])
    price = DecimalField("Price (RM)", validators=[DataRequired(), NumberRange(min=0.01)])
    status = SelectField(
        "Status",
        choices=[("Available", "Available"), ("Sold Out", "Sold Out"), ("Hidden", "Hidden")],
        default="Available",
    )
