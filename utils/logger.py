import datetime
import os
from db import add_log


def log_event(user_id, message):
    try:
        os.makedirs("logs", exist_ok=True)
        with open("logs/bot.log", "a", encoding="utf-8") as f:
            time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{time}] Пользователь {user_id}: {message}\n")
    except Exception as e:
        print(f"Ошибка при логировании события в файл: {e}")


def log_user_action(user_id, action):
    try:
        # Логирование в файл
        log_event(user_id, action)

        # Логирование в базу данных
        add_log(user_id, action)

        print(f"User {user_id}: {action}")
    except Exception as e:
        print(f"Ошибка при логировании действия: {e}")
