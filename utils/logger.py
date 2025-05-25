import datetime

def log_event(user_id, message):
    with open("logs/bot.log", "a", encoding="utf-8") as f:
        time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"[{time}] Пользователь {user_id}: {message}\n")

def log_user_action(user_id, action):
    print(f"User {user_id}: {action}")
