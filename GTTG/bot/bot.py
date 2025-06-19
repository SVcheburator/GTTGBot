import os
import requests
import telebot
from dotenv import load_dotenv
from telebot import types

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
    user = get_or_create_user(message.from_user.id, message.from_user.username or "")
    if user:
        bot.send_message(message.chat.id, f"Hello, {user.get('username') or 'Gym rat'}! Ready to train?")
    else:
        bot.send_message(message.chat.id, "Error while creating user")


@bot.message_handler(commands=['help'])
def handle_help(message):
    help_text = "/start - start GTTG" \
    "\n/help - show this" \
    "\n/createplan - create a new training plan" \
    "\n/myplans - show all training plans" \
    "\n/currentplan - show plan that was set as current" \
    "\n/startworkout - start a new workout from plan or not"
    bot.send_message(message.chat.id, help_text)


# Creating a training plan
user_plan_data = {}

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


# Listing plan summary
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
    
    bot.send_message(message.chat.id, "⭐ Your current plan: /currentplan\n📋 All Your training plans:", reply_markup=markup)


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
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("🗑️ Delete", callback_data=f"delete_plan_confirm_{plan_id}"),
        types.InlineKeyboardButton("⭐ Set as current", callback_data=f"set_current_plan_{plan_id}")
    )
    bot.send_message(call.message.chat.id, summary, parse_mode="Markdown", reply_markup=markup)
    bot.answer_callback_query(call.id)


@bot.message_handler(commands=['currentplan'])
def handle_current_plan(message):
    user_id = message.from_user.id

    user_resp = requests.get(f"{API_URL}users/{user_id}/")
    if user_resp.status_code != 200:
        bot.send_message(message.chat.id, "❌ Failed to fetch user info.")
        return

    user_data = user_resp.json()
    current_cycle = user_data.get("current_cycle")

    if not current_cycle:
        bot.send_message(message.chat.id, "⚠️ You don't have a current plan set.")
        return

    plan_resp = requests.get(f"{API_URL}training-cycles/{current_cycle}/")
    if plan_resp.status_code != 200:
        bot.send_message(message.chat.id, "❌ Failed to fetch your current plan.")
        return

    plan_data = plan_resp.json()

    days_resp = requests.get(f"{API_URL}cycle-days/?cycle_id={current_cycle}")
    if days_resp.status_code != 200:
        bot.send_message(message.chat.id, "❌ Failed to fetch plan days.")
        return

    days = days_resp.json()

    summary = generate_plan_summary(plan_data, days)
    bot.send_message(message.chat.id, f"⭐ *Your current plan:*\n\n{summary}", parse_mode="Markdown")


# Setting training plan as current
@bot.callback_query_handler(func=lambda call: call.data.startswith("set_current_plan_"))
def handle_set_current_plan(call):
    plan_id = call.data.split("set_current_plan_")[1]
    user_id = call.from_user.id

    response = requests.patch(f"{API_URL}users/{user_id}/", json={"current_cycle": plan_id})
    if response.status_code == 200:
        bot.send_message(call.message.chat.id, "⭐ This plan was set as current!")
    else:
        bot.send_message(call.message.chat.id, "❌ Error while setting as current.")
    bot.answer_callback_query(call.id)


# Deleting training plan
@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_plan_confirm_"))
def confirm_delete_plan(call):
    plan_id = call.data.split("delete_plan_confirm_")[1]

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("🗑️ Yes, delete", callback_data=f"delete_plan_{plan_id}"),
        types.InlineKeyboardButton("❌ No, cancel", callback_data="cancel_delete")
    )
    bot.send_message(call.message.chat.id, "Are You sure You want to delete this training plan?", reply_markup=markup)
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_plan_"))
def handle_delete_plan(call):
    plan_id = call.data.split("delete_plan_")[1]
    response = requests.delete(f"{API_URL}training-cycles/{plan_id}/")

    if response.status_code == 204:
        bot.send_message(call.message.chat.id, "✅ Training plan was deleted.")
    else:
        bot.send_message(call.message.chat.id, "❌ Error while deleting plan.")
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data == "cancel_delete")
def cancel_delete(call):
    bot.send_message(call.message.chat.id, "❎ Deleting canceled.")
    bot.answer_callback_query(call.id)


# Starting workout
@bot.message_handler(commands=['startworkout'])
def start_workout(message):
    user_id = message.from_user.id
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("From my plan", "Custom workout")
    msg = bot.send_message(message.chat.id, "Do you want to start workout from your current plan or create a custom one?", reply_markup=markup)
    bot.register_next_step_handler(msg, process_workout_type)


def process_workout_type(message):
    user_id = message.from_user.id
    text = message.text.strip().lower()

    if text == "from my plan":
        user_resp = requests.get(f"{API_URL}users/{user_id}/")
        if user_resp.status_code != 200:
            bot.send_message(message.chat.id, "❌ Failed to fetch your user info.", reply_markup=types.ReplyKeyboardRemove())
            return
        user_data = user_resp.json()
        current_cycle = user_data.get("current_cycle")
        if not current_cycle:
            bot.send_message(message.chat.id, "⚠️ You don't have a current plan set.", reply_markup=types.ReplyKeyboardRemove())
            return

        days_resp = requests.get(f"{API_URL}cycle-days/?cycle_id={current_cycle}")
        if days_resp.status_code != 200:
            bot.send_message(message.chat.id, "❌ Failed to fetch plan days.", reply_markup=types.ReplyKeyboardRemove())
            return

        days = days_resp.json()
        training_days = [d for d in days if d["is_training_day"]]

        if not training_days:
            bot.send_message(message.chat.id, "⚠️ Your plan has no training days.", reply_markup=types.ReplyKeyboardRemove())
            return


        user_plan_data[user_id] = {"training_days": training_days}
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        for d in training_days:
            day_label = f"Day {d['day_number']}: " + ", ".join(str(gid) for gid in d['muscle_groups'])
            markup.add(day_label)
        msg = bot.send_message(message.chat.id, "Choose day to start workout:", reply_markup=markup)
        bot.register_next_step_handler(msg, process_select_plan_day)

    elif text == "custom workout":
        response = requests.get(f"{API_URL}muscle-groups/")
        if response.status_code != 200:
            bot.send_message(message.chat.id, "Error while fetching muscle groups.", reply_markup=types.ReplyKeyboardRemove())
            return

        groups = response.json()
        user_plan_data[user_id] = {"available_groups": groups, "selected_groups": set()}
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
        for g in groups:
            markup.add(g["name"])
        markup.add("✅ Done")
        msg = bot.send_message(message.chat.id, "Choose muscle groups for your workout, then press '✅ Done':", reply_markup=markup)
        bot.register_next_step_handler(msg, process_custom_muscle_groups)

    else:
        bot.send_message(message.chat.id, "Choose button from below.")
        start_workout(message)


def process_select_plan_day(message):
    user_id = message.from_user.id
    text = message.text.strip()
    data = user_plan_data.get(user_id, {})
    training_days = data.get("training_days", [])

    selected_day = None
    for day in training_days:
        day_label = f"Day {day['day_number']}: " + ", ".join(str(gid) for gid in day['muscle_groups'])
        if day_label == text:
            selected_day = day
            break

    if not selected_day:
        bot.send_message(message.chat.id, "Choose day from the buttons below.")
        msg = bot.send_message(message.chat.id, "Choose day to start workout:")
        bot.register_next_step_handler(msg, process_select_plan_day)
        return

    workout_payload = {
        "telegram_id": user_id,
        "is_from_plan": True,
        "muscle_groups": selected_day["muscle_groups"]
    }
    resp = requests.post(f"{API_URL}workouts/", json=workout_payload)

    if resp.status_code == 201:
        workout = resp.json()
        bot.send_message(message.chat.id, f"Workout started from your plan (Day {selected_day['day_number']}) ✅", reply_markup=types.ReplyKeyboardRemove())

        user_plan_data[user_id] = user_plan_data.get(user_id, {})
        user_plan_data[user_id]['current_workout_id'] = workout['id']

        group_ids = selected_day["muscle_groups"]
        exercises_resp = requests.get(f"{API_URL}exercises/")
        if exercises_resp.status_code != 200:
            bot.send_message(message.chat.id, "❌ Failed to fetch exercises.")
            return

        all_exercises = exercises_resp.json()
        workout_exercises = [ex for ex in all_exercises if ex["muscle_group"]["id"] in group_ids]

        if not workout_exercises:
            bot.send_message(message.chat.id, "⚠️ No exercises found for selected groups.")
            return

        user_plan_data[user_id]['pending_exercises'] = workout_exercises
        user_plan_data[user_id]['exercise_index'] = 0

        bot.send_message(message.chat.id, "👇 Select an exercise to start logging sets:", reply_markup=types.ReplyKeyboardRemove())
        show_exercise_choices(message)

    else:
        print("Workout creation failed:", resp.status_code, resp.text)
        bot.send_message(message.chat.id, "❌ Failed to start workout. Please try again later.", reply_markup=types.ReplyKeyboardRemove())
        user_plan_data.pop(user_id, None)


def process_custom_muscle_groups(message):
    user_id = message.from_user.id
    text = message.text.strip()
    data = user_plan_data.get(user_id, {})
    available = data.get("available_groups", [])
    selected_set = data.get("selected_groups", set())

    if text == "✅ Done":
        if not selected_set:
            bot.send_message(message.chat.id, "Choose at least 1 muscle group.")
            msg = bot.send_message(message.chat.id, "Choose muscle groups for your workout, then press '✅ Done':")
            bot.register_next_step_handler(msg, process_custom_muscle_groups)
            return

        group_ids = [g["id"] for g in available if g["name"] in selected_set]
        workout_payload = {
            "telegram_id": user_id,
            "is_from_plan": False,
            "muscle_groups": group_ids
        }
        resp = requests.post(f"{API_URL}workouts/", json=workout_payload)

        if resp.status_code == 201:
            workout = resp.json()
            bot.send_message(message.chat.id, f"Custom workout started ✅", reply_markup=types.ReplyKeyboardRemove())

            user_plan_data[user_id] = user_plan_data.get(user_id, {})
            user_plan_data[user_id]['current_workout_id'] = workout['id']

            exercises_resp = requests.get(f"{API_URL}exercises/")
            if exercises_resp.status_code != 200:
                bot.send_message(message.chat.id, "❌ Failed to fetch exercises.")
                return

            all_exercises = exercises_resp.json()
            workout_exercises = [ex for ex in all_exercises if ex["muscle_group"]["id"] in group_ids]

            if not workout_exercises:
                bot.send_message(message.chat.id, "⚠️ No exercises found for selected groups.")
                return

            user_plan_data[user_id]['pending_exercises'] = workout_exercises
            user_plan_data[user_id]['exercise_index'] = 0

            bot.send_message(message.chat.id, "👇 Select an exercise to start logging sets:", reply_markup=types.ReplyKeyboardRemove())
            show_exercise_choices(message)

        else:
            print("Custom workout creation failed:", resp.status_code, resp.text)
            bot.send_message(message.chat.id, "❌ Failed to start workout. Please try again later.", reply_markup=types.ReplyKeyboardRemove())
            user_plan_data.pop(user_id, None)

    else:
        valid_names = [g["name"] for g in available]
        if text not in valid_names:
            bot.send_message(message.chat.id, "Choose from buttons below.")
        else:
            selected_set.add(text)
        msg = bot.send_message(message.chat.id, "Choose more or press '✅ Done'")
        bot.register_next_step_handler(msg, process_custom_muscle_groups)


def show_exercise_choices(message):
    user_id = message.from_user.id
    exercises = user_plan_data[user_id].get("pending_exercises", [])

    markup = types.InlineKeyboardMarkup()
    for ex in exercises:
        markup.add(types.InlineKeyboardButton(text=ex["name"], callback_data=f"choose_ex:{ex['id']}"))
    
    markup.add(types.InlineKeyboardButton("✅ Finish workout", callback_data="finish_workout"))

    bot.send_message(message.chat.id, "🏋️ Choose an exercise to log a set:", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("choose_ex:"))
def process_exercise_choice(call):
    user_id = call.from_user.id
    exercise_id = int(call.data.split(":")[1])
    user_plan_data[user_id]['current_exercise_id'] = exercise_id

    bot.send_message(call.message.chat.id, "Enter weight for the set (kg):")
    bot.register_next_step_handler(call.message, process_set_weight)


def process_set_weight(message):
    user_id = message.from_user.id
    try:
        weight = float(message.text.strip())
    except ValueError:
        bot.send_message(message.chat.id, "❌ Please enter a valid weight (number).")
        bot.register_next_step_handler(message, process_set_weight)
        return

    user_plan_data[user_id]["current_weight"] = weight
    bot.send_message(message.chat.id, "Enter number of reps:")
    bot.register_next_step_handler(message, process_set_reps)


def process_set_reps(message):
    user_id = message.from_user.id
    try:
        reps = int(message.text.strip())
    except ValueError:
        bot.send_message(message.chat.id, "❌ Please enter a valid number of reps.")
        bot.register_next_step_handler(message, process_set_reps)
        return

    data = user_plan_data.get(user_id, {})
    payload = {
        "workout": data.get("current_workout_id"),
        "exercise": data.get("current_exercise_id"),
        "sets": 1,
        "reps": reps,
        "weight": data.get("current_weight")
    }

    resp = requests.post(f"{API_URL}workout-exercises/", json=payload)

    if resp.status_code == 201:
        bot.send_message(message.chat.id, "✅ Set logged successfully!")
        show_exercise_choices(message)
    else:
        bot.send_message(message.chat.id, "❌ Failed to log set. Try again.")
        bot.register_next_step_handler(message, process_set_weight)


@bot.callback_query_handler(func=lambda call: call.data == "finish_workout")
def finish_workout(call):
    user_id = call.from_user.id
    user_plan_data.pop(user_id, None)
    bot.send_message(call.message.chat.id, "🏁 Workout completed! Well done 💪", reply_markup=types.ReplyKeyboardRemove())



if __name__ == '__main__':
    print("Bot polling...")
    bot.infinity_polling(skip_pending=True)
