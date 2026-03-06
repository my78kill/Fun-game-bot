import telebot
import random
import threading
import time
from flask import Flask
from collections import defaultdict

TOKEN = "8701691785:AAEbFDGSJqZTXLh7B082dtGzbDNLXmoLi8k"  # Replace with your bot token

bot = telebot.TeleBot(TOKEN, parse_mode="Markdown")
app = Flask(__name__)

# -----------------------------
# Storage
# -----------------------------
game_data = {}          # active games per chat
scores = defaultdict(dict)  # scores per chat

ROUND_TIME = 60
TOTAL_ROUNDS = 10

# -----------------------------
# Load Questions
# -----------------------------
def load_questions():
    q = []
    try:
        with open("questions.txt", "r", encoding="utf-8") as f:
            for line in f:
                if "|" in line:
                    q.append(line.strip().split("|"))
    except FileNotFoundError:
        print("⚠️ questions.txt not found!")
    if not q:
        print("⚠️ No questions loaded! Add questions in questions.txt")
    return q

questions = load_questions()

# -----------------------------
# Flask route (for Render)
# -----------------------------
@app.route('/')
def home():
    return "Quiz Bot Running!"

# -----------------------------
# DM START MESSAGE
# -----------------------------
@bot.message_handler(commands=['start'])
def start_dm(message):
    if message.chat.type != "private":
        return

    text = """
👋 *Welcome to Brain Battle Bot 🧠🎮*

This is a *text-based quiz game bot for Telegram groups.*

🤖 *How to Play*

1️⃣ Add the bot to your *group*
2️⃣ Give the bot *Delete Messages permission*
3️⃣ Type *#start* in the group to start the game

🎮 *Game Rules*

• Every game has *10 rounds*
• Each round has *1 question*
• You get *1 minute to answer*
• The *first correct answer wins points*

🏆 *Commands*

#start – Start the quiz game  
#rank – View group leaderboard  
#end – End the current game  

💡 Invite me to your group and test your brain!

Good luck 🍀
"""
    bot.send_message(message.chat.id, text)

# -----------------------------
# START GAME
# -----------------------------
@bot.message_handler(func=lambda m: m.text and m.text.lower() == "#start")
def start_game(message):
    chat_id = message.chat.id

    if message.chat.type == "private":
        bot.send_message(chat_id, "ℹ️ Please add me to a group to play.")
        return

    if chat_id in game_data:
        bot.send_message(chat_id, "⚠️ Game already running!")
        return

    if not questions:
        bot.send_message(chat_id, "⚠️ No questions loaded. Add questions in questions.txt")
        return

    game_data[chat_id] = {
        "round": 0,
        "asked": [],
        "answer": None,
        "msg_id": None
    }

    bot.send_message(chat_id, "🎮 *Game Started!*\nGet ready for 10 rounds!")

    threading.Thread(target=next_round, args=(chat_id,)).start()

# -----------------------------
# NEXT ROUND
# -----------------------------
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
    data["answer"] = q[1].lower()
    data["round"] += 1

    msg = bot.send_message(
        chat_id,
        f"🧠 *Round {data['round']}/{TOTAL_ROUNDS}*\n\n{q[0]}\n\n⏳ 60 seconds!"
    )

    data["msg_id"] = msg.message_id

    threading.Thread(target=round_timer, args=(chat_id, msg.message_id)).start()

# -----------------------------
# ROUND TIMER
# -----------------------------
def round_timer(chat_id, msg_id):
    time.sleep(ROUND_TIME)

    if chat_id not in game_data:
        return

    try:
        bot.delete_message(chat_id, msg_id)
    except:
        pass

    game_data[chat_id]["answer"] = None
    next_round(chat_id)

# -----------------------------
# ANSWER CHECKER
# -----------------------------
@bot.message_handler(func=lambda m: True)
def check_answer(message):
    chat_id = message.chat.id

    if chat_id not in game_data:
        return

    data = game_data[chat_id]

    if not data["answer"]:
        return

    if message.text.lower().strip() == data["answer"]:
        user_id = message.from_user.id
        name = message.from_user.first_name

        scores[chat_id][user_id] = scores[chat_id].get(user_id, 0) + 10

        bot.send_message(
            chat_id,
            f"✅ *{name} got the correct answer!*\n+10 points 🎉"
        )

        try:
            bot.delete_message(chat_id, data["msg_id"])
        except:
            pass

        data["answer"] = None
        next_round(chat_id)

# -----------------------------
# RANK
# -----------------------------
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

    text = "🏆 *Leaderboard*\n\n"

    for i, (uid, pts) in enumerate(sorted_users[:10], 1):
        text += f"{i}. {pts} points\n"

    bot.send_message(chat_id, text)

# -----------------------------
# END GAME
# -----------------------------
@bot.message_handler(func=lambda m: m.text and m.text.lower() == "#end")
def end_cmd(message):
    chat_id = message.chat.id
    end_game(chat_id)

def end_game(chat_id):
    if chat_id not in game_data:
        return

    bot.send_message(chat_id, "🎮 *Game Ended!*")
    del game_data[chat_id]

# -----------------------------
# RUN BOT
# -----------------------------
def run_bot():
    bot.infinity_polling()

if __name__ == "__main__":
    threading.Thread(target=run_bot).start()
    app.run(host="0.0.0.0", port=10000)
