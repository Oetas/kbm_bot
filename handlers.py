from telegram import Update
from telegram.ext import ContextTypes
from utils.logger import log_event

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    log_event(user.id, f"{user.first_name} запустил /start")
    await update.message.reply_text("Бот работает! Привет, друг!")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/start - запустить бота\n"
        "/help - помощь по командам\n"
        "/about - информация о проекте"
    )

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Этот бот создан в рамках ВКР. Автор: G.")
