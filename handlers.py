from telegram import Update
from telegram.ext import ContextTypes
from utils.logger import log_event
import db

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.register_user_if_not_exists(user)            # ← новое
    db.add_log(user.id, "/start")                   # ← лог в БД
    await update.message.reply_text("Бот работает! Привет!")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/start - запустить бота\n"
        "/help - помощь по командам\n"
        "/about - информация о проекте"
    )

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Этот бот создан в рамках ВКР. Автор: G.")
