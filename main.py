import db
db.init_db()

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from handlers import start_command, help_command, about_command
import os

if not os.path.exists("logs"):
    os.makedirs("logs")

app = ApplicationBuilder().token("7404512928:AAG6ZfRiwe7KongTrdY6dsIJnuv-Nu1SoKg").build()

app.add_handler(CommandHandler("start", start_command))
app.add_handler(CommandHandler("help", help_command))
app.add_handler(CommandHandler("about", about_command))

print("Бот запущен!")
app.run_polling()
