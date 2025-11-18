# manage.py
import click
from flask.cli import with_appcontext
from app import create_app
from app.services import user_service
from app.extensions import db # <-- Импортируем db

app = create_app()

@app.cli.command("create-admin")
@click.argument("username")
@click.argument("password")
@with_appcontext # <-- Оборачиваем, чтобы получить доступ к db.session
def create_admin(username, password):
    """
    Создает пользователя с ролью 'admin'.
    Пример: flask create-admin myadmin 12345
    """
    try:
        user_service.create_user(username, password, role='admin')
        print(f"Администратор '{username}' успешно создан.")
    except ValueError as e:
        print(f"Ошибка: {e}")
    except Exception as e:
        print(f"Произошла непредвиденная ошибка: {e}")

if __name__ == '__main__':
    app.run()