# db.py

import psycopg2
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
import datetime, os

load_dotenv()

def get_connection():
    return psycopg2.connect(os.getenv("DB_URL"))

def get_or_create_user(user_id, first_name, last_name, username):
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO users (tg_id, first_name, last_name, username)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (tg_id) DO NOTHING;
        """, (user_id, first_name, last_name, username))
        conn.commit()

def add_event(text):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO events (text) VALUES (%s);", (text,))
    conn.commit()
    conn.close()

def get_events(limit=5):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT text FROM events ORDER BY id DESC LIMIT %s;", (limit,))
    events = [row[0] for row in cur.fetchall()]
    conn.close()
    return events

def set_birthday(user_id, date):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET birthday = %s WHERE id = %s;", (date, user_id))
    conn.commit()
    conn.close()

def set_notify_status(user_id, status):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET notify = %s WHERE id = %s;", (status, user_id))
    conn.commit()
    conn.close()




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
    tg_id       = Column(Integer, unique=True, index=True)
    first_name  = Column(String(60))
    last_name   = Column(String(60))
    username    = Column(String(60))

class Log(Base):
    __tablename__ = "logs"
    id        = Column(Integer, primary_key=True)
    tg_id     = Column(Integer)
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
