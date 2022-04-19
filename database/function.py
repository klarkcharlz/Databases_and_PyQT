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
                     KnownUsers)


class ServerError(Exception):
    def __init__(self, text):
        self.text = text

    def __str__(self):
        return self.text


def create_db(engine, models):
    for model in models:
        try:
            model.__table__.create(engine)
        except OperationalError:
            print(f"Таблица {model} уже есть в БД.")
        else:
            print(f"Таблица {model} создана в БД.")


def get_server_session(path):
    database_engine = create_engine(f'sqlite:///{path}', echo=False, pool_recycle=7200,
                                    connect_args={'check_same_thread': False})
    create_db(database_engine, server_models)
    Session = sessionmaker(bind=database_engine)
    session = Session()

    session.query(ActiveUsers).delete()
    session.commit()

    return session


def user_logout(session, name):
    user = session.query(User).filter_by(name=name).first()
    session.query(ActiveUsers).filter_by(user_id=user.id).delete()
    session.commit()


def user_login(session, name, ip, port):
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
    sender = session.query(User).filter_by(name=sender).first().id
    recipient = session.query(User).filter_by(name=recipient).first().id
    if sender and recipient:
        sender_row = session.query(History).filter_by(user_id=sender).first()
        sender_row.sent += 1
        recipient_row = session.query(History).filter_by(user_id=recipient).first()
        recipient_row.accepted += 1
        session.commit()


def get_contacts(session, username):
    user = session.query(User).filter_by(name=username).one()
    query = session.query(UsersContacts, User). \
        filter_by(user_id=user.id). \
        join(User, UsersContacts.contact == User.id)
    return [contact[1] for contact in query.all()]


def add_contact(session, user, contact):
    user = session.query(User).filter_by(name=user).first()
    contact = session.query(User).filter_by(name=contact).first()
    if not contact or session.query(UsersContacts).filter_by(user_id=user.id, contact=contact.id).count():
        return
    contact_row = UsersContacts(user.id, contact.id)
    session.add(contact_row)
    session.commit()


def remove_contact(session, user, contact):
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
    query = session.query(
        User.name,
        User.last_login
    )
    return query.all()


def message_history(session):
    query = session.query(
        User.name,
        User.last_login,
        History.sent,
        History.accepted
    ).join(User)
    return query.all()


def active_users_list(session):
    query = session.query(
        User.name,
        ActiveUsers.ip_address,
        ActiveUsers.port,
        ActiveUsers.login_time
    ).join(User)
    return query.all()


# client function
def get_client_session(name):
    database_engine = create_engine(f'sqlite:///./db/client_{name}.db3', echo=False, pool_recycle=7200,
                                    connect_args={'check_same_thread': False})
    create_db(database_engine, client_models)
    Session = sessionmaker(bind=database_engine)
    session = Session()

    session.query(Contacts).delete()
    session.commit()

    return session


def add_users(session, users_list):
    session.query(KnownUsers).delete()
    for user in users_list:
        user_row = KnownUsers(user)
        session.add(user_row)
    session.commit()


def add_client_contact(session, contact):
    if not session.query(Contacts).filter_by(name=contact).count():
        contact_row = Contacts(contact)
        session.add(contact_row)
        session.commit()
