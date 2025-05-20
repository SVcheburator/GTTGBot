import os
import requests
import telebot
from dotenv import load_dotenv
from telebot import types

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_URL = os.getenv("API_URL")

bot = telebot.TeleBot(TOKEN)

user_plan_data = {}

def get_or_create_user(telegram_id, username):
    url = f"{API_URL}auth-user/"
    response = requests.post(url, json={"telegram_id": telegram_id, "username": username})
    if response.status_code == 200:
        return response.json()
    return None


@bot.message_handler(commands=['start'])
def handle_start(message):
    user = get_or_create_user(message.from_user.id, message.from_user.username or "")
    if user:
        bot.send_message(message.chat.id, f"Hello, {user.get('username') or 'Gym rat'}! Ready to train?")
    else:
        bot.send_message(message.chat.id, "Error while creating user")


@bot.message_handler(commands=['help'])
def handle_help(message):
    bot.send_message(message.chat.id, "/start - start GTTG bot\n/help - help with bot's commands\n/createplan - create a new training plan")


# Creating a training plan
@bot.message_handler(commands=['createplan'])
def start_create_plan(message):
    user_id = message.from_user.id
    user_plan_data[user_id] = {}
    msg = bot.send_message(message.chat.id, "let's create a new training plan for You\nWhat's the name of the plan?")
    bot.register_next_step_handler(msg, process_plan_name)


def process_plan_name(message):
    user_id = message.from_user.id
    user_plan_data[user_id]['name'] = message.text.strip()
    msg = bot.send_message(message.chat.id, "How long is Your training cycle going to be? (Days)")
    bot.register_next_step_handler(msg, process_plan_length)


def process_plan_length(message):
    user_id = message.from_user.id
    try:
        length = int(message.text)
        if length < 1:
            raise ValueError()
        user_plan_data[user_id]['length'] = length
        user_plan_data[user_id]['days'] = []
        user_plan_data[user_id]['current_day'] = 1
        ask_day_type(message)
    except ValueError:
        msg = bot.send_message(message.chat.id, "Has to be a number.")
        bot.register_next_step_handler(msg, process_plan_length)


def ask_day_type(message):
    user_id = message.from_user.id
    current_day = user_plan_data[user_id]['current_day']
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("Training", "Rest day")
    msg = bot.send_message(message.chat.id, f"Day {current_day}: Training or Rest day?", reply_markup=markup)
    bot.register_next_step_handler(msg, process_day_type)


def process_day_type(message):
    user_id = message.from_user.id
    text = message.text.lower().strip()

    if text not in ["training", "rest day"]:
        bot.send_message(message.chat.id, "Choose the button ⬇️")
        return ask_day_type(message)

    is_training = text == "training"
    current_day = user_plan_data[user_id]['current_day']

    if is_training:
        response = requests.get(f"{API_URL}muscle-groups/")
        if response.status_code == 200:
            groups = response.json()
            user_plan_data[user_id]['available_groups'] = groups
            user_plan_data[user_id]['selected_groups'] = set()

            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
            for g in groups:
                markup.add(g["name"])
            markup.add("✅ Done")

            msg = bot.send_message(message.chat.id, f"Choose all muscle groups for day {current_day} then press '✅ Done':", reply_markup=markup)
            bot.register_next_step_handler(msg, process_muscle_groups)
        else:
            bot.send_message(message.chat.id, "Error while getting muscle groups.")
            ask_day_type(message)
    else:
        user_plan_data[user_id]['days'].append({
            "day_number": current_day,
            "is_training_day": False,
            "muscle_groups": []
        })
        proceed_next_day(message)


def process_muscle_groups(message):
    user_id = message.from_user.id
    text = message.text.strip()
    available = user_plan_data[user_id].get("available_groups", [])
    selected_set = user_plan_data[user_id]["selected_groups"]

    if text == "✅ Done":
        if not selected_set:
            bot.send_message(message.chat.id, "Choose at least 1 muscle group.")
            return ask_day_type(message)
        group_ids = [g["id"] for g in available if g["name"] in selected_set]
        current_day = user_plan_data[user_id]['current_day']
        user_plan_data[user_id]['days'].append({
            "day_number": current_day,
            "is_training_day": True,
            "muscle_groups": group_ids
        })

        bot.send_message(message.chat.id, "Muscle groups chosen successfuly ✅", reply_markup=types.ReplyKeyboardRemove())
        proceed_next_day(message)
    else:
        valid_names = [g["name"] for g in available]
        if text not in valid_names:
            bot.send_message(message.chat.id, "Choose from buttons below.")
        else:
            selected_set.add(text)
        msg = bot.send_message(message.chat.id, "Choose more or press '✅ Done'")
        bot.register_next_step_handler(msg, process_muscle_groups)


def proceed_next_day(message):
    user_id = message.from_user.id
    user_plan_data[user_id]['current_day'] += 1
    if user_plan_data[user_id]['current_day'] > user_plan_data[user_id]['length']:
        finalize_plan(message)
    else:
        ask_day_type(message)


def finalize_plan(message):
    user_id = message.from_user.id
    data = user_plan_data[user_id]

    cycle_payload = {
        "name": data['name'],
        "length": data['length'],
        "telegram_id": user_id
    }
    response = requests.post(f"{API_URL}training-cycles/", json=cycle_payload)
    if response.status_code != 201:
        bot.send_message(message.chat.id, "Error while creating training cycle.")
        return

    cycle_id = response.json()['id']
    data['id'] = cycle_id

    for day in data['days']:
        day_payload = {
            "cycle": cycle_id,
            "day_number": day['day_number'],
            "is_training_day": day['is_training_day'],
            "muscle_groups": day['muscle_groups']
        }
        requests.post(f"{API_URL}cycle-days/", json=day_payload)

    bot.send_message(message.chat.id, f"Plan created ✅", reply_markup=types.ReplyKeyboardRemove())
    
    summary_text = generate_plan_summary(data)
    bot.send_message(message.chat.id, summary_text, parse_mode="Markdown")

    user_plan_data.pop(user_id, None)


def generate_plan_summary(plan_data, days_data=None):
    try:
        group_resp = requests.get(f"{API_URL}muscle-groups/")
        if group_resp.status_code != 200:
            return "Error while getting muscle groups."

        group_map = {g['id']: g['name'] for g in group_resp.json()}
        summary = f"📝 *Here is your plan \"{plan_data['name']}\":*\n\n"

        if days_data is None:
            days_resp = requests.get(f"{API_URL}cycle-days/?cycle_id={plan_data['id']}")
            if days_resp.status_code != 200:
                return "Error while getting cycle days."
            days_data = days_resp.json()

        seen = set()
        unique_days = []
        for day in days_data:
            key = (day['day_number'], day['is_training_day'], tuple(day['muscle_groups']))
            if key not in seen:
                seen.add(key)
                unique_days.append(day)

        unique_days.sort(key=lambda x: x['day_number'])

        for day in unique_days:
            summary += f"*Day {day['day_number']}:* "
            if day['is_training_day']:
                group_names = [group_map.get(gid, f"ID:{gid}") for gid in day['muscle_groups']]
                summary += f"Training day 💪\nMuscle groups: *{', '.join(group_names)}*\n"
            else:
                summary += "Rest day 😴\n"
            summary += "\n"

        return summary.strip()
    except Exception as e:
        return f"Error generating plan summary: {str(e)}"



@bot.message_handler(commands=['myplans'])
def list_user_plans(message):
    user_id = message.from_user.id
    response = requests.get(f"{API_URL}training-cycles/?telegram_id={user_id}")
    
    if response.status_code != 200 or not response.json():
        bot.send_message(message.chat.id, "You have no saved plans.")
        return

    plans = response.json()

    markup = types.InlineKeyboardMarkup()
    for plan in plans:
        btn = types.InlineKeyboardButton(
            text=plan['name'],
            callback_data=f"view_plan_{plan['id']}"
        )
        markup.add(btn)
    
    bot.send_message(message.chat.id, "📋 Your training plans:", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("view_plan_"))
def handle_view_plan(call):
    plan_id = call.data.split("view_plan_")[1]

    plan_resp = requests.get(f"{API_URL}training-cycles/{plan_id}/")
    if plan_resp.status_code != 200:
        bot.answer_callback_query(call.id, "Plan not found.")
        return

    plan = plan_resp.json()

    days_resp = requests.get(f"{API_URL}cycle-days/?cycle_id={plan_id}")
    if days_resp.status_code != 200:
        bot.answer_callback_query(call.id, "Failed to get days.")
        return

    days = days_resp.json()

    summary = generate_plan_summary(plan, days)
    bot.send_message(call.message.chat.id, summary, parse_mode="Markdown")
    bot.answer_callback_query(call.id)




if __name__ == '__main__':
    print("Bot polling...")
    bot.infinity_polling(skip_pending=True)
