import json

import sqlalchemy as sq
from sqlalchemy.orm import declarative_base, relationship


Base = declarative_base()


class Word(Base):
    __tablename__ = 'words'

    id = sq.Column(sq.Integer, primary_key=True)
    eng = sq.Column(sq.String(length=50), unique=True)
    rus = sq.Column(sq.String(length=50), unique=True)

    def __str__(self):
        return f'{self.eng} {self.rus}'


class User(Base):
    __tablename__ = 'users'

    id = sq.Column(sq.Integer, primary_key=True)
    user_id = sq.Column(sq.BigInteger, unique=True)

    def __str__(self):
        return f'{self.user_id}'


class UserWord(Base):
    __tablename__ = 'user_word'

    id = sq.Column(sq.Integer, primary_key=True)
    user_id = sq.Column(sq.Integer, sq.ForeignKey(User.id), nullable=False)
    word_id = sq.Column(sq.Integer, sq.ForeignKey(Word.id), nullable=False)

    user = relationship(User, backref='users_word')
    word = relationship(Word, backref='user_words')


def create_tables(engine):
    '''
    Создание таблиц
    '''
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def initial_data(path, session):
    '''
    Первоначальное заполнение таблицы WORD из файла json 10-ю словами
    '''
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    for s in data:
        session.add(Word(eng=s.get('eng'), rus=s.get('rus')))
    session.commit()
