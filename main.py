import os
import json
import datetime
import requests
import logging
import asyncio
import schedule
import time

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler

BOT_TOKEN = os.getenv("BOT_TOKEN")

DATA_FILE = "stats.json"

if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({"daily": {"users": [], "downloads": 0},
                   "monthly": {"users": [], "downloads": 0}}, f)

def load_stats():
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_stats(stats):
    with open(DATA_FILE, "w") as f:
        json.dump(stats, f)

def update_stats(user_id, is_download=False):
    stats = load_stats()
    today = stats["daily"]
    month = stats["monthly"]

    if user_id not in today["users"]:
        today["users"].append(user_id)
    if user_id not in month["users"]:
        month["users"].append(user_id)

    if is_download:
        today["downloads"] += 1
        month["downloads"] += 1

    save_stats(stats)

def reset_daily():
    stats = load_stats()
    stats["daily"] = {"users": [], "downloads": 0}
    save_stats(stats)

def reset_monthly():
    stats = load_stats()
    stats["monthly"] = {"users": [], "downloads": 0}
    save_stats(stats)

def check_and_reset_monthly():
    if datetime.datetime.now().day == 1:
        reset_monthly()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send the name of a movie or series to search.")

async def stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stats = load_stats()
    daily_users = len(stats["daily"]["users"])
    daily_downloads = stats["daily"]["downloads"]
    monthly_users = len(stats["monthly"]["users"])
    monthly_downloads = stats["monthly"]["downloads"]

    msg = (
        f"**Daily Stats**\nUsers: {daily_users}\nDownloads: {daily_downloads}\n\n"
        f"**Monthly Stats**\nUsers: {monthly_users}\nDownloads: {monthly_downloads}"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

def search_movie(query):
    url = f"https://yts.mx/api/v2/list_movies.json?query_term={query}"
    try:
        response = requests.get(url)
        data = response.json()
        if data["data"]["movie_count"] == 0:
            return []
        return data["data"]["movies"]
    except Exception:
        return []

async def handle_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text
    results = search_movie(query)
    user_id = str(update.message.from_user.id)
    update_stats(user_id)

    if not results:
        await update.message.reply_text("No results found.")
        return

    for movie in results:
        msg = f"*{movie['title']}*\nYear: {movie['year']}\nRating: {movie['rating']}\n"
        buttons = []
        for torrent in movie.get("torrents", []):
            quality = torrent["quality"]
            url = torrent["url"]
            buttons.append([InlineKeyboardButton(f"Download {quality}", url=url)])

        reply_markup = InlineKeyboardMarkup(buttons)
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=reply_markup)

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    update_stats(user_id, is_download=True)

def schedule_tasks():
    schedule.every().day.at("00:00").do(reset_daily)
    schedule.every().day.at("00:00").do(check_and_reset_monthly)

    async def scheduler_loop():
        while True:
            schedule.run_pending()
            await asyncio.sleep(60)

    asyncio.create_task(scheduler_loop())

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_search))
    app.add_handler(CallbackQueryHandler(button_click))

    schedule_tasks()

    app.run_polling()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
