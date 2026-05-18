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
    food_name = StringField("Food Name", validators=[DataRequired(), Length(max=100)])
    description = TextAreaField("Description", validators=[Length(max=500)])
    price = DecimalField("Price (RM)", validators=[DataRequired(), NumberRange(min=0.01)])
    status = SelectField(
        "Status",
        choices=[("Available", "Available"), ("Sold Out", "Sold Out"), ("Hidden", "Hidden")],
        default="Available",
    )
