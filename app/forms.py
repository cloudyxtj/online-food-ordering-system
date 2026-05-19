"""WTForms for input validation across all modules.

Covers register, login, add/edit food items.
"""
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, DecimalField, TextAreaField, SelectField, ValidationError
from wtforms.validators import DataRequired, Email, Length, EqualTo, NumberRange
from app.models import User

class RegisterForm(FlaskForm):
    
    def validate_email(self, field):
        user = User.query.filter_by(email=field.data).first()
    
        if user:
            raise ValidationError("Email already registered. Please use a different one.")
    
    def validate_password(self, field):
        password = field.data
        
        # Uppercase check
        if not any(char.isupper() for char in password):
            raise ValidationError("Password must contain at least one uppercase letter.")
            
        # Lowercase check
        if not any(char.islower() for char in password):
            raise ValidationError("Password must contain at least one lowercase letter.")
            
        # Digit check
        if not any(char.isdigit() for char in password):
            raise ValidationError("Password must contain at least one number.")
            
        # Special Character check
        special_chars = "!@#$%^&*()-_+="
        if not any(char in special_chars for char in password):
            raise ValidationError("Password must contain at least one symbol (!@#$%^&*()-_+=).")
    
    name = StringField("Full Name", validators=[DataRequired(), Length(max=100)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=150)], filters=[lambda x: x.strip().lower() if x else x])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField(
        "Confirm Password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match.")],
    )


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()], filters=[lambda x: x.strip().lower() if x else x])
    password = PasswordField("Password", validators=[DataRequired()])


class FoodItemForm(FlaskForm):
    food_name = StringField(
        "Food Name",
        validators=[DataRequired(), Length(min=2, max=100, message="Food name must be between 2 and 100 characters.")],
        filters=[lambda x: x.strip() if x else x],
    )
    description = TextAreaField(
        "Description",
        validators=[Length(max=500, message="Description cannot exceed 500 characters.")],
        filters=[lambda x: x.strip() if x else x],
    )
    price = DecimalField(
        "Price (RM)",
        validators=[DataRequired(), NumberRange(min=0.01, max=9999.99, message="Price must be between RM 0.01 and RM 9,999.99.")],
    )
    status = SelectField(
        "Status",
        choices=[("Available", "Available"), ("Sold Out", "Sold Out"), ("Hidden", "Hidden")],
        default="Available",
    )

    def validate_status(self, field):
        allowed = {"Available", "Sold Out", "Hidden"}
        if field.data not in allowed:
            raise ValidationError("Invalid status value.")
