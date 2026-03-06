import telebot
import random
import threading
import time
from flask import Flask
from collections import defaultdict

TOKEN = "8701691785:AAEbFDGSJqZTXLh7B082dtGzbDNLXmoLi8k"

bot = telebot.TeleBot(TOKEN, parse_mode="Markdown")
app = Flask(__name__)

game_data = {}
scores = defaultdict(dict)

ROUND_TIME = 120
TOTAL_ROUNDS = 10


# -------------------------
# Load Questions
# -------------------------
def load_questions():
    q = []
    with open("questions.txt", "r", encoding="utf-8") as f:
        for line in f:
            if "|" in line:
                q.append(line.strip().split("|"))
    return q


questions = load_questions()


# -------------------------
# Flask route (Render)
# -------------------------
@app.route('/')
def home():
    return "Quiz Bot Running"


# -------------------------
# Welcome Message
# -------------------------
@bot.message_handler(commands=['start'])
def start_dm(message):

    if message.chat.type != "private":
        return

    text = """
👋 *Welcome to Brain Battle Bot 🧠🎮*

This is a *text-based quiz game bot for Telegram groups.*

🤖 *How to Play*

1️⃣ Add the bot to your group  
2️⃣ Give the bot *Delete Messages permission*  
3️⃣ Type **#start** in the group  

🎮 *Game Rules*

• 10 rounds per game  
• 1 question per round  
• 120 seconds to answer  
• First correct answer gets points  

🏆 *Commands*

#start – Start game  
#rank – Leaderboard  
#end – End game  

Good luck 🍀
"""

    bot.send_message(message.chat.id, text)


# -------------------------
# Start Game
# -------------------------
@bot.message_handler(func=lambda m: m.text and m.text.lower() == "#start")
def start_game(message):

    chat_id = message.chat.id

    if chat_id in game_data:
        bot.send_message(chat_id, "⚠️ Game already running!")
        return

    game_data[chat_id] = {
        "round": 0,
        "asked": [],
        "answer": None,
        "msg_id": None,
        "round_active": False
    }

    bot.send_message(chat_id, "🎮 *Game Started!*")

    next_round(chat_id)


# -------------------------
# Next Round
# -------------------------
def next_round(chat_id):

    if chat_id not in game_data:
        return

    data = game_data[chat_id]

    if data["round"] >= TOTAL_ROUNDS:
        end_game(chat_id)
        return

    q = random.choice(questions)

    while q in data["asked"]:
        q = random.choice(questions)

    data["asked"].append(q)

    data["round"] += 1
    data["answer"] = q[1].lower()
    data["round_active"] = True

    msg = bot.send_message(
        chat_id,
        f"🧠 Round {data['round']}/{TOTAL_ROUNDS}\n\n{q[0]}\n\n⏳ {ROUND_TIME} seconds!"
    )

    data["msg_id"] = msg.message_id

    threading.Thread(target=round_timer, args=(chat_id, msg.message_id)).start()


# -------------------------
# Round Timer
# -------------------------
def round_timer(chat_id, msg_id):

    time.sleep(ROUND_TIME)

    if chat_id not in game_data:
        return

    data = game_data[chat_id]

    if not data["round_active"]:
        return

    data["round_active"] = False

    try:
        bot.delete_message(chat_id, msg_id)
    except:
        pass

    data["answer"] = None

    next_round(chat_id)


# -------------------------
# Answer Checker
# -------------------------
@bot.message_handler(func=lambda m: True)
def check_answer(message):

    chat_id = message.chat.id

    if chat_id not in game_data:
        return

    data = game_data[chat_id]

    if not data["round_active"]:
        return

    if message.text.lower().strip() == data["answer"]:

        data["round_active"] = False

        user_id = message.from_user.id
        name = message.from_user.first_name

        if user_id not in scores[chat_id]:
            scores[chat_id][user_id] = {"name": name, "points": 0}

        scores[chat_id][user_id]["points"] += 10

        bot.send_message(
            chat_id,
            f"✅ {name} got correct answer!\n+10 points 🎉"
        )

        try:
            bot.delete_message(chat_id, data["msg_id"])
        except:
            pass

        data["answer"] = None

        next_round(chat_id)


# -------------------------
# Rank
# -------------------------
@bot.message_handler(func=lambda m: m.text and m.text.lower() == "#rank")
def rank(message):

    chat_id = message.chat.id

    if chat_id not in scores or not scores[chat_id]:
        bot.send_message(chat_id, "No scores yet.")
        return

    sorted_users = sorted(
        scores[chat_id].items(),
        key=lambda x: x[1]["points"],
        reverse=True
    )

    text = "🏆 *Leaderboard*\n\n"

    for i, (uid, info) in enumerate(sorted_users[:10], 1):
        text += f"{i}. {info['name']} - {info['points']} pts\n"

    bot.send_message(chat_id, text)


# -------------------------
# End Game
# -------------------------
@bot.message_handler(func=lambda m: m.text and m.text.lower() == "#end")
def end_cmd(message):

    chat_id = message.chat.id

    end_game(chat_id)


def end_game(chat_id):

    if chat_id not in game_data:
        return

    bot.send_message(chat_id, "🎮 Game Ended!")

    if chat_id in scores:

        sorted_users = sorted(
            scores[chat_id].items(),
            key=lambda x: x[1]["points"],
            reverse=True
        )

        text = "🏆 *Final Leaderboard*\n\n"

        for i, (uid, info) in enumerate(sorted_users[:10], 1):
            text += f"{i}. {info['name']} - {info['points']} pts\n"

        bot.send_message(chat_id, text)

    del game_data[chat_id]


# -------------------------
# Run Bot
# -------------------------
def run_bot():
    bot.infinity_polling()


if __name__ == "__main__":

    threading.Thread(target=run_bot).start()

    app.run(host="0.0.0.0", port=10000)
