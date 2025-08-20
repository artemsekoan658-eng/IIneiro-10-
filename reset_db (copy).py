from main import db, User, app

with app.app_context():
    db.drop_all()
    db.create_all()
    admin = User(login="admin", password="admin123", is_admin=True, tariff="premium")
    db.session.add(admin)
    db.session.commit()
    print("Админ создан!")