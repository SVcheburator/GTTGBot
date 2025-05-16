import os
import requests
import telebot
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_URL = os.getenv("API_URL")

bot = telebot.TeleBot(TOKEN)


def get_or_create_user(telegram_id, username):
    url = f"{API_URL}auth-user/"
    response = requests.post(url, json={"telegram_id": telegram_id, "username": username})
    if response.status_code == 200:
        return response.json()
    return None


@bot.message_handler(commands=['start'])
def handle_start(message):
    user = get_or_create_user(message.from_user.id, message.from_user.username)
    if user:
        bot.send_message(message.chat.id, f"Hello, {user['username'] or 'Gym rat'}! Ready to train?")
    else:
        bot.send_message(message.chat.id, "Error while creating user")


@bot.message_handler(commands=['help'])
def handle_help(message):
    bot.send_message(message.chat.id, "/start — start\n/help — help with bot's commands")


if __name__ == '__main__':
    print("Bot poling...")
    bot.infinity_polling()
