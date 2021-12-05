from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError

from models import User, History


engine = create_engine("sqlite:///users.db")
Session = sessionmaker(bind=engine)
session = Session()


if __name__ == "__main__":
    models = [User, History]
    for model in models:
        try:
            model.__table__.create(engine)
        except OperationalError:
            print(f"Таблица {model} уже есть в БД.")
        else:
            print(f"Таблица {model} создана в БД.")
