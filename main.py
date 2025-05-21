import os
import json, threading, schedule, requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

def search_movies(query):
    url = "https://yts.mx/api/v2/list_movies.json"
    params = {"query_term": query}
    try:
        res = requests.get(url, params=params).json()
        movies = res.get("data", {}).get("movies", [])
        results = []
        for movie in movies:
            res_options = []
            for t in movie.get("torrents", []):
                res_options.append({
                    "quality": t["quality"],
                    "size": t["size"],
                    "url": t["url"]
                })
            results.append({
                "title": movie["title_long"],
                "slug": movie["slug"],
                "resolutions": res_options
            })
        return results
    except:
        return []

def init_stats():
    try:
        with open("stats.json") as f: json.load(f)
    except:
        with open("stats.json", "w") as f:
            json.dump({"daily": {"users": [], "downloads": 0}, "monthly": {"users": [], "downloads": 0}}, f)

def update_stats(user_id, download=False):
    with open("stats.json", "r+") as f:
        stats = json.load(f)
        for key in ["daily", "monthly"]:
            if user_id not in stats[key]["users"]:
                stats[key]["users"].append(user_id)
            if download:
                stats[key]["downloads"] += 1
        f.seek(0)
        json.dump(stats, f, indent=2)
        f.truncate()

def reset_daily():
    with open("stats.json", "r+") as f:
        stats = json.load(f)
        stats["daily"] = {"users": [], "downloads": 0}
        f.seek(0)
        json.dump(stats, f, indent=2)
        f.truncate()

def reset_monthly():
    with open("stats.json", "r+") as f:
        stats = json.load(f)
        stats["monthly"] = {"users": [], "downloads": 0}
        f.seek(0)
        json.dump(stats, f, indent=2)
        f.truncate()

def schedule_tasks():
    schedule.every().day.at("00:00").do(reset_daily)
    schedule.every().month.at("00:00").do(reset_monthly)
    def loop(): 
        while True: schedule.run_pending()
    threading.Thread(target=loop, daemon=True).start()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hi! Send me a movie or series name to get download options.")

async def handle_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text
    user_id = update.message.from_user.id
    update_stats(user_id)
    results = search_movies(query)
    if not results:
        await update.message.reply_text("No results found.")
        return
    for movie in results[:3]:
        msg = f"*{movie['title']}*\nChoose version:"
        buttons = [[InlineKeyboardButton(f"{res['quality']} ({res['size']})", callback_data=res["url"])]
                   for res in movie["resolutions"]]
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    update_stats(query.from_user.id, download=True)
    await query.message.reply_text(f"Here is your link:\n{query.data}")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("Not authorized.")
        return
    with open("stats.json") as f:
        stats = json.load(f)
    msg = (f"*Daily:*\nUsers: {len(stats['daily']['users'])}, Downloads: {stats['daily']['downloads']}\n\n"
           f"*Monthly:*\nUsers: {len(stats['monthly']['users'])}, Downloads: {stats['monthly']['downloads']}")
    await update.message.reply_text(msg, parse_mode="Markdown")

def main():
    init_stats()
    schedule_tasks()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_query))
    app.add_handler(CallbackQueryHandler(handle_button))
    app.run_polling()

if __name__ == "__main__":
    main()
