"""
Функции для взаимодействия с БД
"""

from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from .models import (server_models,
                     client_models,
                     ActiveUsers,
                     User,
                     History,
                     LoginHistory,
                     UsersContacts,
                     Contacts,
                     KnownUsers,
                     MessageHistory)


class ServerError(Exception):
    """Ошибка со стороны сервера"""
    def __init__(self, text):
        self.text = text

    def __str__(self):
        return self.text


def create_db(engine, models):
    """
    Создание базы данных
    :param engine: движок
    :param models: список моделей
    :return:
    """
    for model in models:
        try:
            model.__table__.create(engine)
        except OperationalError:
            print(f"Таблица {model} уже есть в БД.")
        else:
            print(f"Таблица {model} создана в БД.")


def get_server_session(path):
    """
    Создание сессии для сервера
    :param path: путь до бд
    :return: сессия
    """
    database_engine = create_engine(f'sqlite:///{path}', echo=False, pool_recycle=7200,
                                    connect_args={'check_same_thread': False})
    create_db(database_engine, server_models)
    Session = sessionmaker(bind=database_engine)
    session = Session()

    session.query(ActiveUsers).delete()
    session.commit()

    return session


def user_logout(session, name):
    """
    выход пользователя
    :param session: сессия
    :param name: юзернейм пользователя
    :return:
    """
    user = session.query(User).filter_by(name=name).first()
    session.query(ActiveUsers).filter_by(user_id=user.id).delete()
    session.commit()


def get_pubkey(session, name):
    """
    Получение ключа
    :param session: сессия
    :param name: юзернейм пользователя
    :return: ключ
    """
    user = session.query(User).filter_by(name=name).first()
    return user.pubkey


def user_login(session, name, ip, port):
    """
    Подключение пользователя
    :param session: сессия
    :param name: юзернейм
    :param ip: ip адресс
    :param port: порт
    :return:
    """
    rez = session.query(User).filter_by(name=name)
    if rez.count():
        user = rez.first()
        user.last_login = datetime.now()
    else:
        user = User(name)
        session.add(user)
        session.commit()
        user_in_history = History(user.id)
        session.add(user_in_history)

    new_active_user = ActiveUsers(user.id, ip, port, datetime.now())
    session.add(new_active_user)

    login_history = LoginHistory(user.id, datetime.now(), ip, port)
    session.add(login_history)

    session.commit()


def process_message(session, sender, recipient):
    """

    :param session:
    :param sender:
    :param recipient:
    :return:
    """
    sender = session.query(User).filter_by(name=sender).first().id
    recipient = session.query(User).filter_by(name=recipient).first().id
    if sender and recipient:
        sender_row = session.query(History).filter_by(user_id=sender).first()
        sender_row.sent += 1
        recipient_row = session.query(History).filter_by(user_id=recipient).first()
        recipient_row.accepted += 1
        session.commit()


def get_contacts(session, username):
    """
    Получение списка контактов
    :param session: сессия
    :param username: юзернейм
    :return: контакт
    """
    user = session.query(User).filter_by(name=username).one()
    query = session.query(UsersContacts, User.name). \
        filter_by(user_id=user.id). \
        join(User, UsersContacts.contact == User.id)
    return [contact[1] for contact in query.all()]


def add_contact(session, user, contact):
    """
    Добавление контакта
    :param session: сессия
    :param user: юзернейм
    :param contact: контакт
    :return:
    """
    user = session.query(User).filter_by(name=user).first()
    contact = session.query(User).filter_by(name=contact).first()
    if not contact or session.query(UsersContacts).filter_by(user_id=user.id, contact=contact.id).count():
        return
    contact_row = UsersContacts(user.id, contact.id)
    session.add(contact_row)
    session.commit()


def remove_contact(session, user, contact):
    """
    Удаление контакта
    :param session: сессия
    :param user: юзернейм
    :param contact: контакт
    :return:
    """
    user = session.query(User).filter_by(name=user).first()
    contact = session.query(User).filter_by(name=contact).first()
    if not contact:
        return
    print(session.query(UsersContacts).filter(
        UsersContacts.user == user.id,
        UsersContacts.contact == contact.id
    ).delete())
    session.commit()


def users_list(session):
    """
    Получение списка пользователей
    :param session: сессия
    :return: список пользователей
    """
    query = session.query(
        User.name,
        User.last_login
    )
    return query.all()


def message_history(session):
    """
    Получение истории сообщений
    :param session: сессия
    :return: история сообщений
    """
    query = session.query(
        User.name,
        User.last_login,
        History.sent,
        History.accepted
    ).join(User)
    return query.all()


def active_users_list(session):
    """
    Получение списка активных пользователей
    :param session: сессия
    :return: список активных пользователей
    """
    query = session.query(
        User.name,
        ActiveUsers.ip_address,
        ActiveUsers.port,
        ActiveUsers.login_time
    ).join(User)
    return query.all()


# client function
def get_client_session(name):
    """
    Получение клиентской сессии
    :param name: юзернейм
    :return: сессия
    """
    database_engine = create_engine(f'sqlite:///./client/db/client_{name}.db3', echo=False, pool_recycle=7200,
                                    connect_args={'check_same_thread': False})
    create_db(database_engine, client_models)
    Session = sessionmaker(bind=database_engine)
    session = Session()

    session.query(Contacts).delete()
    session.commit()

    return session


def add_users(session, users_list):
    """
    Добавление пользователей
    :param session: сессия
    :param users_list: список пользователей
    :return:
    """
    session.query(KnownUsers).delete()
    for user in users_list:
        user_row = KnownUsers(user)
        session.add(user_row)
    session.commit()


def add_client_contact(session, contact):
    """
    Добавление контакта
    :param session: сессия
    :param contact: контакт
    :return:
    """
    if not session.query(Contacts).filter_by(name=contact).count():
        contact_row = Contacts(contact)
        session.add(contact_row)
        session.commit()


def get_history(session, contact):
    """
    Получение истории сообщений
    :param session:
    :param contact: история сообщений
    :return:
    """
    query = session.query(MessageHistory).filter_by(contact=contact)
    return [(history_row.contact, history_row.direction,
             history_row.message, history_row.date)
            for history_row in query.all()]


def get_client_contacts(session):
    """
    Получение контактов
    :param session: сессия
    :return: список контактов
    """
    return [contact[0] for contact in session.query(Contacts.name).all()]


def del_contact(session, contact):
    """
    ДУаление кнтакта
    :param session: сессия
    :param contact: контакт
    :return:
    """
    session.query(Contacts).filter_by(name=contact).delete()
    session.commit()


def save_message(session, contact, direction, message):
    """
    Сохранение сообщения
    :param session: сессия
    :param contact: контакт
    :param direction:
    :param message: сообщение
    :return:
    """
    message_row = MessageHistory(contact, direction, message)
    session.add(message_row)
    session.commit()


def check_contact(session, contact):
    """
    Проверка существования контакта
    :param session: сессия
    :param contact: контакт
    :return: лож или истина
    """
    if session.query(Contacts).filter_by(name=contact).count():
        return True
    else:
        return False


def get_users(session):
    """
    Получение списка пользователей
    :param session: сессия
    :return: список пользователей
    """
    return [user[0] for user in session.query(KnownUsers.username).all()]


def check_user(session, user):
    """
    Проверка существования пользователя
    :param session: сессия
    :param user: лож или истина
    :return:
    """
    if session.query(KnownUsers).filter_by(username=user).count():
        return True
    else:
        return False
