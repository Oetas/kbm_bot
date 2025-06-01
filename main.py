from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, Application
import httpx
from telegram.request import HTTPXRequest
from db import add_event, get_events, update_birthday, update_notify_status, create_or_get_user, get_today_birthdays
from utils.logger import log_user_action
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import psycopg2
import os
import datetime
import logging
from dotenv import load_dotenv

DB_PARAMS = {
    "dbname": os.getenv("PG_NAME"),
    "user": os.getenv("PG_USER"),
    "password": os.getenv("PG_PASS"),
    "host": os.getenv("PG_HOST"),
    "port": os.getenv("PG_PORT"),
}

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
GROUP_CHAT_ID = int(os.getenv("GROUP_CHAT_ID"))

ADMIN_IDS = [552167621, 747868890, 678405392, 392698511, 542341313]

scheduler = AsyncIOScheduler()

# Кастомный таймаут: 20 секунд
timeout = httpx.Timeout(20.0, connect=5.0)
client = httpx.AsyncClient(timeout=timeout)

application = Application.builder().token(TOKEN).request(HTTPXRequest()).build()

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
    keyboard = [
        [InlineKeyboardButton("🎭 Мероприятия", callback_data="events")],
        [InlineKeyboardButton("➕ Добавить мероприятие", callback_data="add_event")],
        [InlineKeyboardButton("🎂 Указать дату", callback_data="set_birthday"),
         InlineKeyboardButton("📅 Моя дата", callback_data="my_birthday")],
        [InlineKeyboardButton("✏️ Изменить дату", callback_data="edit_birthday")],
        [InlineKeyboardButton("🔔 ВКЛ", callback_data="notify_on"),
         InlineKeyboardButton("🔕 ВЫКЛ", callback_data="notify_off")],
        [InlineKeyboardButton("📡 Пинг", callback_data="ping")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    help_text = (
    "🛠 <b>Команды:</b>\n"
    "/start — запуск бота\n"
    "/help — справка\n"
    "/add_event <code>текст</code> — добавить мероприятие (для админов)\n"
    "/events — последние мероприятия\n"
    "/birthday <code>дд.мм.гггг</code> — указать дату рождения\n"
    "/my_birthday — показать дату рождения\n"
    "/edit_birthday — изменить дату рождения\n"
    "/notify on|off — включить/выключить уведомления\n"
    "/ping — проверить, жив ли бот"
    )

    await update.message.reply_html(help_text, reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()

        user_id = query.from_user.id
        data = query.data

        if data == "ping":
            await query.edit_message_text("🏓 Я на месте!")

        elif data == "events":
            from datetime import datetime
            conn = psycopg2.connect(**DB_PARAMS)
            cur = conn.cursor()
            cur.execute("""
                SELECT text, created_at FROM events
                ORDER BY created_at DESC
                LIMIT 5
            """)
            rows = cur.fetchall()
            conn.close()

            if rows:
                msg = "\n\n".join([f"{text}\n🕒 {ts.strftime('%d.%m.%Y %H:%M')}" for text, ts in rows])
            else:
                msg = "Нет мероприятий за последнее время."
            await query.edit_message_text(f"🎭 Последние мероприятия:\n\n{msg}")

        elif data == "add_event":
            await query.edit_message_text(
                "📝 Введите текст нового мероприятия в формате:\n<code>/add_event текст</code>",
                parse_mode="HTML")

        elif data == "set_birthday":
            await query.edit_message_text(
                "🎂 Введите дату рождения в формате:\n<code>/birthday дд.мм.гггг</code>",
                parse_mode="HTML")

        elif data == "notify_on":
            update_notify_status(user_id, True)
            await query.edit_message_text("🔔 Уведомления включены.")

        elif data == "notify_off":
            update_notify_status(user_id, False)
            await query.edit_message_text("🔕 Уведомления выключены.")

        elif data == "my_birthday":
            conn = psycopg2.connect(**DB_PARAMS)
            cur = conn.cursor()
            cur.execute("SELECT birthday FROM users WHERE tg_id = %s", (user_id,))
            row = cur.fetchone()
            conn.close()

            if row and row[0]:
                bday = row[0].strftime('%d.%m.%Y')
                await query.edit_message_text(f"🎂 Ваша дата рождения: {bday}")
            else:
                await query.edit_message_text(
                    "❌ У вас пока не указана дата рождения.\nВведите её командой:\n<code>/birthday дд.мм.гггг</code>",
                    parse_mode="HTML")

        elif data == "edit_birthday":
            await query.edit_message_text(
                "✏️ Введите новую дату рождения:\n<code>/birthday дд.мм.гггг</code>",
                parse_mode="HTML")

        else:
            await query.edit_message_text("❓ Неизвестная команда.")

    except Exception as e:
        logging.exception("Ошибка в button_handler:")
        await update.callback_query.edit_message_text("⚠️ Произошла ошибка при обработке команды.")


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
    # Планировщик: проверка дней рождения каждый день в 10:00
    scheduler.add_job(check_birthdays, "cron", hour=13, minute=14)
    scheduler.start()


from telegram.ext import MessageHandler, filters

# === Новая функция для рассылки сообщений ===
async def forward_from_thread(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None or update.message.text is None:
        return  # игнорируем не-текстовые сообщения
    message = update.message

    # Проверяем, что это нужная тема
    if message.chat.id != int(os.getenv("GROUP_CHAT_ID")):
        return
    if message.message_thread_id != 260795:  #
        return
    if not message.text:
        return

    # Подключаемся к базе данных
    conn = psycopg2.connect(**DB_PARAMS)
    cursor = conn.cursor()

    # Получаем всех пользователей, подписанных на мероприятия
    cursor.execute("SELECT tg_id FROM users WHERE notify = TRUE")
    users = cursor.fetchall()

    # Рассылаем сообщение каждому пользователю
    for (user_id,) in users:
        try:
            await context.bot.send_message(chat_id=user_id, text=message.text)

            # Логируем рассылку
            cursor.execute(
                "INSERT INTO logs (user_id, action, ts) VALUES (%s, %s, %s)",
                (user_id, 'event_forward', datetime.now())
            )

        except Exception as e:
            print(f"Ошибка при отправке пользователю {user_id}: {e}")

    conn.commit()
    cursor.close()
    conn.close()


async def broadcast_to_subscribed_users(bot: Bot, message_text: str):
    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()

    cur.execute("SELECT telegram_id FROM users WHERE subscribed_to_events = true")
    user_ids = [row[0] for row in cur.fetchall()]

    for user_id in user_ids:
        try:
            await bot.send_message(chat_id=user_id, text=message_text)
            cur.execute("INSERT INTO logs (telegram_id, event_type) VALUES (%s, %s)", (user_id, 'event_message'))
        except Exception as e:
            print(f"Ошибка отправки пользователю {user_id}: {e}")
            cur.execute("INSERT INTO logs (telegram_id, event_type, message) VALUES (%s, %s, %s)", (user_id, 'send_error', str(e)))

    conn.commit()
    cur.close()
    conn.close()

async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Бот в строю!")


async def my_birthday(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()
    cur.execute("SELECT birthday FROM users WHERE tg_id = %s", (user_id,))
    row = cur.fetchone()
    conn.close()

    if row and row[0]:
        bday = row[0].strftime('%d.%m.%Y')
        await update.message.reply_text(f"🎂 Ваша дата рождения: {bday}")
    else:
        await update.message.reply_text("❌ У вас пока не указана дата рождения. Введите её командой:\n<code>/birthday дд.мм.гггг</code>", parse_mode="HTML")

async def edit_birthday(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✏️ Введите новую дату рождения в формате:\n<code>/birthday дд.мм.гггг</code>",
        parse_mode="HTML"
    )


if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).post_init(on_startup).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("add_event", add_event_command))
    app.add_handler(CommandHandler("events", events_command))
    app.add_handler(CommandHandler("birthday", birthday_command))
    app.add_handler(CommandHandler("notify", notify_command))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Chat(chat_id=GROUP_CHAT_ID),
        forward_from_thread
    ))
    app.add_handler(CommandHandler("ping", ping_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(CommandHandler("my_birthday", my_birthday))
    app.add_handler(CommandHandler("edit_birthday", edit_birthday))
    app.run_polling()
