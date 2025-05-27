# db.py

import psycopg2
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
import datetime, os
from sqlalchemy import BigInteger
from sqlalchemy import Boolean, Date

load_dotenv()

def get_user(tg_id: int):
    with SessionLocal() as db:
        return db.query(User).filter_by(tg_id=tg_id).first()


def create_or_get_user(tg_user):
    with SessionLocal() as db:
        user = db.query(User).filter_by(tg_id=tg_user.id).first()
        if not user:
            user = User(
                tg_id=tg_user.id,
                first_name=tg_user.first_name,
                last_name=tg_user.last_name,
                username=tg_user.username
            )
            db.add(user)
            db.commit()
        return user

def update_birthday(tg_id: int, date_obj):
    with SessionLocal() as db:
        user = db.query(User).filter_by(tg_id=tg_id).first()
        if user:
            user.birthday = date_obj
            db.commit()

def update_notify_status(tg_id: int, status: bool):
    with SessionLocal() as db:
        user = db.query(User).filter_by(tg_id=tg_id).first()
        if user:
            user.notify = status
            db.commit()

def add_event(text_content):
    with SessionLocal() as db:
        db.add(Event(text=text_content))
        db.commit()

def get_events(limit=5):
    with SessionLocal() as db:
        events = db.query(Event).order_by(Event.id.desc()).limit(limit).all()
        return [e.text for e in events]

# строка подключения к бд
DB_USER = os.getenv("PG_USER", "postgres")
DB_PASS = os.getenv("PG_PASS", "postgres")
DB_HOST = os.getenv("PG_HOST", "localhost")
DB_NAME = os.getenv("PG_NAME", "kbm_bot")

engine = create_engine(
    f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}",
    echo=False, pool_pre_ping=True
)

Base = declarative_base()
SessionLocal = sessionmaker(bind=engine)

# модели
class User(Base):
    __tablename__ = "users"
    id          = Column(Integer, primary_key=True, index=True)
    tg_id       = Column(BigInteger, unique=True, index=True)  # <-- BigInteger, чтобы влез Telegram ID
    first_name  = Column(String(60))
    last_name   = Column(String(60))
    username    = Column(String(60))
    notify      = Column(Boolean, default=False)
    birthday    = Column(Date)

class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True)
    text = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
class Log(Base):
    __tablename__ = "logs"
    id        = Column(Integer, primary_key=True)
    tg_id     = Column(BigInteger)  # <-- Важно!
    action    = Column(String(255))
    ts        = Column(DateTime, default=datetime.datetime.utcnow)

# служебные функции
def init_db():
    """Создаем таблицы, если их нет"""
    Base.metadata.create_all(bind=engine)

def register_user_if_not_exists(tg_user):
    with SessionLocal() as db:
        if not db.query(User).filter_by(tg_id=tg_user.id).first():
            db.add(
                User(
                    tg_id=tg_user.id,
                    first_name=tg_user.first_name,
                    last_name=tg_user.last_name,
                    username=tg_user.username
                )
            )
            db.commit()

def add_log(tg_id: int, action: str):
    with SessionLocal() as db:
        db.add(Log(tg_id=tg_id, action=action))
        db.commit()
