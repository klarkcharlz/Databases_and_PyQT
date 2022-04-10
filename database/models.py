from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey


Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    description = Column(Text, nullable=True)

    def __init__(self, name, description):
        self.name = name
        self.description = description

    def __repr__(self):
        return f"{self.name}"


class History(Base):
    __tablename__ = 'history'

    id = Column(Integer, ForeignKey(User.id), primary_key=True,)
    entry_time = Column(DateTime)
    ip = Column(String)

    def __init__(self, name, description):
        self.name = name
        self.description = description

    def __repr__(self):
        return f"{self.ip}: {self.entry_time}"


class ActiveUsers(Base):
    __tablename__ = 'active_users'
    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey(User.id), unique=True)

    def __init__(self, user_id):
        self.user_id = user_id
