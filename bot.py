import json
import os
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

STATS_FILE = "stats.json"

def load_stats():
    if not os.path.exists(STATS_FILE):
        return {"daily": {}, "monthly": {}}
    with open(STATS_FILE, "r") as f:
        return json.load(f)

def save_stats(stats):
    with open(STATS_FILE, "w") as f:
        json.dump(stats, f, indent=4)

def update_stats(user_id: str):
    stats = load_stats()
    today = datetime.now().strftime("%Y-%m-%d")

    # Initialize keys if missing
    if "daily" not in stats:
        stats["daily"] = {}
    if today not in stats["daily"]:
        stats["daily"][today] = {}
    if user_id not in stats["daily"][today]:
        stats["daily"][today][user_id] = 0

    stats["daily"][today][user_id] += 1
    save_stats(stats)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome! Send me any message and I'll track your daily usage.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    update_stats(user_id)
    await update.message.reply_text(
        f"Hi {update.message.from_user.first_name}, your message has been counted for today!"
    )

def main():
    application = Application.builder().token("7404332983:AAHmID9arE_YrqCofKZgMIcVMCtae_fIxrY").build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    application.run_polling()

if __name__ == "__main__":
    main()
