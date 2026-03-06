import telebot
import random
import threading
import time
from flask import Flask
from collections import defaultdict

TOKEN = "8701691785:AAEbFDGSJqZTXLh7B082dtGzbDNLXmoLi8k"  # Replace

bot = telebot.TeleBot(TOKEN, parse_mode="Markdown")
app = Flask(__name__)

# -----------------------------
# Storage
# -----------------------------
game_data = {}
scores = defaultdict(dict)

ROUND_TIME = 120  # Changed to 120 seconds
TOTAL_ROUNDS = 10

# -----------------------------
# Load Questions
# -----------------------------
def load_questions():
    q = []
    with open("questions.txt", "r", encoding="utf-8") as f:
        for line in f:
            if "|" in line:
                q.append(line.strip().split("|"))
    return q

questions = load_questions()

# -----------------------------
# DM START MESSAGE
# -----------------------------
@bot.message_handler(commands=['start'])
def start_dm(message):
    if message.chat.type != "private":
        return
    text = """
👋 *Welcome to Brain Battle Bot 🧠🎮*

Add me to a group, give delete permission, type #start to play.
"""
    bot.send_message(message.chat.id, text)

# -----------------------------
# START GAME
# -----------------------------
@bot.message_handler(func=lambda m: m.text and m.text.lower() == "#start")
def start_game(message):
    chat_id = message.chat.id
    if chat_id in game_data:
        bot.send_message(chat_id, "⚠️ Game already running!")
        return
    if not questions:
        bot.send_message(chat_id, "⚠️ No questions loaded!")
        return
    game_data[chat_id] = {"round":0, "asked":[], "answer":None, "msg_id":None}
    bot.send_message(chat_id, f"🎮 Game Started! {TOTAL_ROUNDS} Rounds")
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

    # Pick a valid question
    q = random.choice(questions)
    while q in data["asked"]:
        q = random.choice(questions)

    data["asked"].append(q)
    data["answer"] = q[1].lower()
    data["round"] += 1

    msg = bot.send_message(chat_id,
        f"🧠 Round {data['round']}/{TOTAL_ROUNDS}\n\n{q[0]}\n\n⏳ {ROUND_TIME} seconds!"
    )
    data["msg_id"] = msg.message_id

    # Start timer
    threading.Thread(target=round_timer, args=(chat_id, msg.message_id)).start()

# -----------------------------
# ROUND TIMER
# -----------------------------
def round_timer(chat_id, msg_id):
    time.sleep(ROUND_TIME)
    if chat_id not in game_data:
        return
    data = game_data[chat_id]
    # Delete old question
    try: bot.delete_message(chat_id, msg_id)
    except: pass
    data["answer"] = None
    # Send next round only after delete
    threading.Thread(target=next_round, args=(chat_id,)).start()

# -----------------------------
# ANSWER CHECKER
# -----------------------------
@bot.message_handler(func=lambda m: True)
def check_answer(message):
    chat_id = message.chat.id
    if chat_id not in game_data: return
    data = game_data[chat_id]
    if not data["answer"]: return
    if message.text.lower().strip() == data["answer"]:
        user_id = message.from_user.id
        name = message.from_user.first_name
        # Points store
        if user_id not in scores[chat_id]:
            scores[chat_id][user_id] = {"points":0,"name":name}
        scores[chat_id][user_id]["points"] += 10
        bot.send_message(chat_id,f"✅ {name} got correct answer! +10 points 🎉")
        # Delete old question
        try: bot.delete_message(chat_id, data["msg_id"])
        except: pass
        data["answer"] = None
        threading.Thread(target=next_round, args=(chat_id,)).start()

# -----------------------------
# END GAME
# -----------------------------
@bot.message_handler(func=lambda m: m.text and m.text.lower() == "#end")
def end_cmd(message):
    end_game(message.chat.id)

def end_game(chat_id):
    if chat_id not in game_data: return
    bot.send_message(chat_id, "🎮 Game Ended!")
    # Auto leaderboard
    if chat_id in scores and scores[chat_id]:
        sorted_users = sorted(scores[chat_id].items(), key=lambda x:x[1]["points"], reverse=True)
        text = "🏆 *Leaderboard*\n\n"
        for i,(uid,info) in enumerate(sorted_users[:10],1):
            text += f"{i}. {info['name']} - {info['points']} points\n"
        bot.send_message(chat_id,text)
    del game_data[chat_id]

# -----------------------------
# RUN BOT
# -----------------------------
def run_bot():
    bot.infinity_polling()

if __name__ == "__main__":
    threading.Thread(target=run_bot).start()
    app = Flask(__name__)
    @app.route('/')
    def home(): return "Quiz Bot Running!"
    app.run(host="0.0.0.0", port=10000)
