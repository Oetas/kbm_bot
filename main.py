from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from db import add_event, get_events, update_birthday, update_notify_status, create_or_get_user, get_today_birthdays
from utils.logger import log_user_action
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import psycopg2
import os
import datetime
from dotenv import load_dotenv

DB_PARAMS = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
}

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
GROUP_CHAT_ID = int(os.getenv("GROUP_CHAT_ID"))

ADMIN_IDS = [552167621, 747868890, 678405392, 552167624, 552167625]

scheduler = AsyncIOScheduler()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    first_name = user.first_name or ""
    last_name = user.last_name or ""
    username = user.username or ""

    # Сохраняем пользователя в БД
    create_or_get_user(update.effective_user)

    # Логируем действие
    log_user_action(user_id, "/start")

    # Приветственное сообщение
    await update.message.reply_text("👋 Привет! Я КБМ Бот. Введи /help для списка команд.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("/add_event <текст> — добавить мероприятие (только для администраторов)\n"
                                    "/events — список последних мероприятий\n"
                                    "/birthday <дд.мм.гггг> — сохранить дату рождения\n"
                                    "/notify on|off — включить/выключить уведомления")

async def add_event_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("Только администратор может добавлять мероприятия.")
        return

    text = ' '.join(context.args)
    if not text:
        await update.message.reply_text("Формат: /add_event <текст>")
        return

    add_event(text)
    await update.message.reply_text("Мероприятие добавлено!")

async def events_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    events = get_events()
    if not events:
        await update.message.reply_text("Нет добавленных мероприятий.")
    else:
        await update.message.reply_text("\n\n".join(events))

async def birthday_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Формат: /birthday дд.мм.гггг")
        return

    input_date = context.args[0]
    try:
        date_obj = datetime.datetime.strptime(input_date, "%d.%m.%Y").date()
    except ValueError:
        await update.message.reply_text("⚠️ Неверный формат даты. Используй дд.мм.гггг")
        return

    user_id = update.effective_user.id
    update_birthday(user_id, date_obj)
    await update.message.reply_text(f"✅ Дата рождения {input_date} сохранена.")

async def check_birthdays():
    bot = Bot(token=TOKEN)
    users = get_today_birthdays()
    if not users:
        return

    names = ", ".join([u.first_name or "Пользователь" for u in users])
    message = f"🎉 Сегодня день рождения у: {names}!\nДружно поздравляем! 🥳"
    await bot.send_message(chat_id=GROUP_CHAT_ID, text=message)

    for user in users:
        if user.notify:
            try:
                await bot.send_message(chat_id=user.tg_id,
                                       text=f"Сегодня твой день! 🎂 С Днём Рождения, {user.first_name}!")
            except:
                pass

async def notify_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or context.args[0].lower() not in ["on", "off"]:
        await update.message.reply_text("Формат: /notify on или /notify off")
        return

    value = context.args[0].lower() == "on"
    user_id = update.effective_user.id
    update_notify_status(user_id, value)
    await update.message.reply_text("Уведомления включены." if value else "Уведомления выключены.")

async def on_startup(app):
    # Планировщик: проверка дней рождения каждый день в 16:52
    scheduler.add_job(check_birthdays, "cron", hour=17, minute=15)
    scheduler.start()


from telegram.ext import MessageHandler, filters

# === Новая функция для рассылки сообщений ===
async def forward_from_thread(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not message.text:
        return

    # Проверка на нужный chat_id и message_thread_id
    if message.chat.id != int(os.getenv("GROUP_CHAT_ID")):
        return
    if message.message_thread_id != 260795:
        return

    # Получаем всех пользователей с подпиской
    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM users WHERE subscribed_to_events = TRUE")
    user_ids = [row[0] for row in cur.fetchall()]

    for uid in user_ids:
        try:
            await context.bot.send_message(chat_id=uid, text=message.text)
            # Логируем отправку
            cur.execute(
                "INSERT INTO logs (user_id, action, timestamp) VALUES (%s, %s, %s)",
                (uid, "event_forwarded", datetime.datetime.now())
            )
        except Exception as e:
            print(f"Не удалось отправить сообщение пользователю {uid}: {e}")

    conn.commit()
    cur.close()
    conn.close()

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).post_init(on_startup).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("add_event", add_event_command))
    app.add_handler(CommandHandler("events", events_command))
    app.add_handler(CommandHandler("birthday", birthday_command))
    app.add_handler(CommandHandler("notify", notify_command))
    app.add_handler(MessageHandler(filters.TEXT & filters.Chat(chat_id=int(os.getenv("GROUP_CHAT_ID"))), forward_from_thread))

    app.run_polling()
