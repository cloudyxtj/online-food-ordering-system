"""Seed the database with sample food items and an admin account.

Run once: python seed.py
"""
from app import create_app, db
from app.models import User, FoodItem

app = create_app()

with app.app_context():
    # Create admin account
    admin = User.query.filter_by(email="admin@foodorder.com").first()
    if not admin:
        admin = User(
            name="Admin",
            email="admin@foodorder.com",
            role="Admin",
        )
        admin.set_password("admin123")
        db.session.add(admin)
        print("Created admin account: admin@foodorder.com / admin123")

    # Create sample food items
    sample_items = [
        FoodItem(food_name="Double Cheeseburger", description="Two beef patties with cheese, lettuce, and tomato.", price=12.50, status="Available"),
        FoodItem(food_name="Chicken Fried Rice", description="Wok-fried rice with egg, chicken, and vegetables.", price=10.00, status="Available"),
        FoodItem(food_name="Margherita Pizza", description="Classic tomato, mozzarella, and basil on thin crust.", price=15.00, status="Available"),
        FoodItem(food_name="Nasi Lemak", description="Coconut rice with sambal, fried egg, anchovies, and peanuts.", price=8.50, status="Available"),
        FoodItem(food_name="Iced Lemon Tea", description="Refreshing brewed tea with fresh lemon.", price=4.50, status="Available"),
        FoodItem(food_name="Chocolate Milkshake", description="Thick and creamy chocolate milkshake.", price=6.00, status="Available"),
        FoodItem(food_name="Caesar Salad", description="Romaine lettuce, croutons, parmesan with Caesar dressing.", price=11.00, status="Available"),
        FoodItem(food_name="Spaghetti Carbonara", description="Creamy pasta with bacon, egg, and parmesan.", price=13.00, status="Sold Out"),
    ]

    for s in sample_items:
        existing = FoodItem.query.filter_by(food_name=s.food_name).first()
        if not existing:
            db.session.add(s)
            print(f"Added food item: {s.food_name} (RM {s.price:.2f})")

    db.session.commit()
    print("\nSeed complete! Run 'flask run' to start the app.")
