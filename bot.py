import telebot
import random
import threading
import time
from flask import Flask
from collections import defaultdict

TOKEN = "8701691785:AAEbFDGSJqZTXLh7B082dtGzbDNLXmoLi8k"

bot = telebot.TeleBot(TOKEN, parse_mode="Markdown")
app = Flask(__name__)

# --------------------
# Storage
# --------------------

game_data = {}
scores = defaultdict(dict)

ROUND_TIME = 120
TOTAL_ROUNDS = 10


# --------------------
# Load Questions
# --------------------

def load_questions():

    q = []

    with open("questions.txt", "r", encoding="utf-8") as f:
        for line in f:

            if "|" in line:

                question, answer = line.split("|")

                q.append((question.strip(), answer.strip().lower()))

    return q


questions = load_questions()


# --------------------
# Flask (Render)
# --------------------

@app.route('/')
def home():
    return "Quiz Bot Running!"


# --------------------
# Welcome message (DM)
# --------------------

@bot.message_handler(commands=['start'])
def start_dm(message):

    if message.chat.type != "private":
        return

    text = """
👋 *Welcome to Brain Battle Bot* 🧠

This is a *Telegram Group Quiz Game Bot.*

🎮 **How To Play**

1️⃣ Add bot to group  
2️⃣ Give *Delete Messages permission*  
3️⃣ Type **#start**

⚡ **Game Rules**

• 10 rounds per game  
• 1 question per round  
• 120 seconds to answer  
• First correct answer wins points  

🏆 **Commands**

#start – start game  
#rank – show leaderboard  
#end – stop game  

Good luck 🍀
"""

    bot.send_message(message.chat.id, text)


# --------------------
# Start Game
# --------------------

@bot.message_handler(func=lambda m: m.text and m.text.lower() == "#start")
def start_game(message):

    if message.chat.type == "private":
        return

    chat_id = message.chat.id

    if chat_id in game_data:
        bot.send_message(chat_id, "⚠️ Game already running!")
        return

    game_data[chat_id] = {
        "round": 0,
        "asked": [],
        "answer": None,
        "msg_id": None
    }

    bot.send_message(chat_id, "🎮 Game Started!\n10 Rounds Begin!")

    next_round(chat_id)


# --------------------
# Next Round
# --------------------

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

    question, answer = q

    data["answer"] = answer

    data["round"] += 1

    msg = bot.send_message(
        chat_id,
        f"🧠 Round {data['round']}/{TOTAL_ROUNDS}\n\n{question}\n\n⏳ 120 seconds!"
    )

    data["msg_id"] = msg.message_id

    threading.Thread(
        target=round_timer,
        args=(chat_id,),
        daemon=True
    ).start()


# --------------------
# Round Timer
# --------------------

def round_timer(chat_id):

    time.sleep(ROUND_TIME)

    if chat_id not in game_data:
        return

    data = game_data[chat_id]

    if data["answer"] is None:
        return

    try:
        bot.delete_message(chat_id, data["msg_id"])
    except:
        pass

    data["answer"] = None

    next_round(chat_id)


# --------------------
# Answer Checker
# --------------------

@bot.message_handler(func=lambda m: True)
def check_answer(message):

    if not message.text:
        return

    if message.text.startswith("#"):
        return

    chat_id = message.chat.id

    if chat_id not in game_data:
        return

    data = game_data[chat_id]

    if data["answer"] is None:
        return

    user_answer = message.text.lower().strip()

    if user_answer == data["answer"]:

        user_id = message.from_user.id
        name = message.from_user.first_name

        scores[chat_id][user_id] = scores[chat_id].get(user_id, 0) + 10

        bot.send_message(
            chat_id,
            f"✅ {name} answered correctly!\n+10 points 🎉"
        )

        try:
            bot.delete_message(chat_id, data["msg_id"])
        except:
            pass

        data["answer"] = None

        next_round(chat_id)


# --------------------
# Leaderboard
# --------------------

@bot.message_handler(func=lambda m: m.text and m.text.lower() == "#rank")
def rank(message):

    chat_id = message.chat.id

    if chat_id not in scores or not scores[chat_id]:

        bot.send_message(chat_id, "No scores yet.")
        return

    sorted_users = sorted(
        scores[chat_id].items(),
        key=lambda x: x[1],
        reverse=True
    )

    text = "🏆 Leaderboard\n\n"

    for i, (uid, pts) in enumerate(sorted_users[:10], 1):

        text += f"{i}. {pts} points\n"

    bot.send_message(chat_id, text)


# --------------------
# End Command
# --------------------

@bot.message_handler(func=lambda m: m.text and m.text.lower() == "#end")
def end_cmd(message):

    chat_id = message.chat.id

    end_game(chat_id)


# --------------------
# End Game
# --------------------

def end_game(chat_id):

    if chat_id not in game_data:
        return

    text = "🎮 Game Ended!\n\n🏆 Final Scores\n\n"

    if chat_id in scores:

        sorted_users = sorted(
            scores[chat_id].items(),
            key=lambda x: x[1],
            reverse=True
        )

        for i, (uid, pts) in enumerate(sorted_users[:10], 1):

            text += f"{i}. {pts} points\n"

    bot.send_message(chat_id, text)

    del game_data[chat_id]


# --------------------
# Run Bot
# --------------------

def run_bot():
    bot.infinity_polling(skip_pending=True)


if __name__ == "__main__":

    threading.Thread(target=run_bot).start()

    app.run(host="0.0.0.0", port=10000)
