from datetime import datetime

from sqlalchemy.orm import declarative_base
from sqlalchemy import (Column,
                        Integer,
                        String,
                        DateTime,
                        ForeignKey,
                        Text)


Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    last_login = Column(DateTime, default=datetime.now())

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return f"{self.name}"


class History(Base):
    __tablename__ = 'history'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey(User.id))
    sent = Column(Integer)
    accepted = Column(Integer)

    def __init__(self, user_id):
        self.user_id = user_id
        self.sent = 0
        self.accepted = 0

    def __repr__(self):
        return f"{self.ip}: {self.entry_time}"


class ActiveUsers(Base):
    __tablename__ = 'active_users'
    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey(User.id), unique=True)
    ip_address = Column(String)
    port = Column(Integer)
    login_time = Column(DateTime)

    def __init__(self, user_id, ip_address, port, login_time):
        self.user_id = user_id
        self.ip_address = ip_address
        self.port = port
        self.login_time = login_time


class LoginHistory(Base):
    __tablename__ = 'login_history'

    id = Column(Integer, primary_key=True)
    user_id = Column(ForeignKey(User.id))
    date_time = Column(DateTime)
    ip = Column(String)
    port = Column(String)

    def __init__(self, user_id, date, ip, port):
        self.user_id = user_id
        self.date_time = date
        self.ip = ip
        self.port = port


class UsersContacts(Base):
    __tablename__ = 'user_contacts'

    id = Column(Integer, primary_key=True)
    user_id = Column(ForeignKey(User.id))
    contact = Column(ForeignKey(User.id))

    def __init__(self, user_id, contact):
        self.user_id = user_id
        self.contact = contact


server_models = [User, History, ActiveUsers, LoginHistory, UsersContacts]


# client
class KnownUsers(Base):
    __tablename__ = 'known_users'

    id = Column(Integer, primary_key=True)
    username = Column(String)

    def __init__(self, user):
        self.username = user


class MessageHistory(Base):
    __tablename__ = 'message_history'

    id = Column(Integer, primary_key=True)
    from_user = Column(String)
    to_user = Column(String)
    message = Column(Text)
    date = Column(DateTime)

    def __init__(self, from_user, to_user, message):
        self.from_user = from_user
        self.to_user = to_user
        self.message = message
        self.date = datetime.now()


class Contacts(Base):
    __tablename__ = 'client_contacts'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)

    def __init__(self, contact):
        self.id = None
        self.name = contact


client_models = [KnownUsers, MessageHistory, Contacts]
