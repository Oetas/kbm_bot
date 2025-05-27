from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from db import add_event, get_events, update_birthday, update_notify_status, create_or_get_user
from utils.logger import log_user_action

import os
import datetime

from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")

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
    if user_id not in [552167621]:  #
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

import datetime  # не забудь импортировать

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


async def notify_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or context.args[0].lower() not in ["on", "off"]:
        await update.message.reply_text("Формат: /notify on или /notify off")
        return

    value = context.args[0].lower() == "on"
    user_id = update.effective_user.id
    update_notify_status(user_id, value)
    await update.message.reply_text("Уведомления включены." if value else "Уведомления выключены.")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("add_event", add_event_command))
    app.add_handler(CommandHandler("events", events_command))
    app.add_handler(CommandHandler("birthday", birthday_command))
    app.add_handler(CommandHandler("notify", notify_command))
    app.run_polling()
