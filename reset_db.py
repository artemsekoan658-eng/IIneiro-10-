from main import db, app, User

if __name__ == "__main__":
    with app.app_context():
        db.drop_all()       # Удаляем все таблицы
        db.create_all()     # Создаём все таблицы заново

        # Создаём админа, если его ещё нет (логин и пароль твои)
        if not User.query.filter_by(login="Artem2013").first():
            admin = User(
                login="Artem2013",
                password="Art2013Ar",
                is_admin=True,
                tariff="premium"
            )
            db.session.add(admin)
            db.session.commit()
            print("Аккаунт администратора создан: Artem2013 / Art2013Ar")

        print("База данных сброшена и создана заново.")