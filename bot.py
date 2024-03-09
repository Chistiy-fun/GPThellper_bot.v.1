import json

import telebot
from telebot import TeleBot
from telebot.types import KeyboardButton, ReplyKeyboardMarkup
import logging
import requests
from gpt import GPT

gpt = GPT()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt="%Y-%m-%d %H:%M:%S",
    filename="log_file.txt",
    filemode="w",
)

# токены
from config import TOKEN, MAX_TOKENS

# создаем бота
bot = telebot.TeleBot(TOKEN)
MAX_LETTERS = MAX_TOKENS


def save_to_json():
    with open('users_history.json', 'w', encoding='utf-8') as f:
        json.dump(users_history, f, indent=2, ensure_ascii=False)


def load_from_json():
    # noinspection PyBroadException
    try:
        with open('users_history.json', 'r+', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        data = {}

    return data

#
users_history = load_from_json()


# создание клавы

def create_keyboard(buttons_list):
    keyboard = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True, one_time_keyboard=True)
    keyboard.add(*buttons_list)
    return keyboard


# Команды
@bot.message_handler(commands=['start'])
def start_command(message):
    logging.info("Выполнение команды /start")
    user_name = message.from_user.first_name
    bot.send_message(message.from_user.id, text=f"Доброго времени суток, {user_name}!",
                     reply_markup=create_keyboard(["/solve_task", '/help']))

@bot.message_handler(commands=['help'])
def start_command(message):
    logging.info("Выполнение команды /help")
    user_name = message.from_user.first_name
    bot.send_message(message.from_user.id, text=f"Вот список моих команд:\n/solve_task - используй чтобы задать вопрос ИИ\n/about - тут я расскожу подробнее о себе  ",
                     reply_markup=create_keyboard(["/solve_task"]))

@bot.message_handler(commands=['about'])
def start_command(message):
    logging.info("Выполнение команды /about")
    user_name = message.from_user.first_name
    bot.send_message(message.from_user.id, text=f"Я бот, который оснащен магией ИИ🪄\n"
                                                f"я могу помочь тебе решить любой пример по математике.\n"
                                                f"P.S Я не всегда могу давать точные ответы на твои вопросы, не судите строго :")

@bot.message_handler(commands=['solve_task'])
def solve_task(message):
    logging.info("Выполнение команды /solve_task")
    bot.send_message(message.chat.id, "Напиши условие новой задачи:")
    bot.register_next_step_handler(message, get_promt)

@bot.message_handler(commands=['debug'])
def send_logs(message):
    with open("log_file.txt", "rb") as f:
        bot.send_document(message.chat.id, f)

# Фильтры

def filter_hello(message):
    word = "привет"
    return word in message.text.lower()

@bot.message_handler(content_types=['text'], func=filter_hello)
def say_hello(message):
    logging.info("Выполнение команды filter_hello")
    user_name = message.from_user.first_name
    bot.send_message(message.from_user.id, text=f"{user_name }, Приветик!")

def continue_filter(message):
    logging.debug("нажата кнопка 'Продолжить решение'")
    button_text = 'Продолжить решение'
    return message.text == button_text

@bot.message_handler(func=continue_filter)
def get_promt(message):
    logging.info("Выполнение команды continue_filter")
    user_id = str(message.from_user.id)

    if not message.text:
        logging.warning("Получено пустое текстовое сообщение")
        bot.send_message(user_id, "Необходимо отправить именно текстовое сообщение")
        bot.register_next_step_handler(message, get_promt)
        return

 # Получаем текст сообщения от пользователя
    user_request = message.text

    if gpt.count_tokens(user_request) >= gpt.MAX_TOKENS:
        logging.warning("превышено кол-во символов")
        bot.send_message(user_id, "Запрос превышает количество символов\nИсправь запрос")
        bot.register_next_step_handler(message, get_promt)
        return


    if user_id not in users_history or users_history[user_id] == {}:
        if user_request == "Продолжить решение":
            logging.warning("Пользователя нету в users_history")
            bot.send_message(message.chat.id, "Кажется, вы еще не задали вопрос.")
            bot.register_next_step_handler(message, get_promt)
            return

        # Сохраняем промт пользователя и начало ответа GPT в словарик users_history
    users_history[user_id] = {
        'system_content': ("Ты - дружелюбный помощник для решения задач по математике. Давай подробный ответ с решением на русском языке "),
        'user_content': user_request,
        'assistant_content': "Решим задачу по шагам:"
        }
    save_to_json()

    prompt = gpt.make_promt(users_history[user_id])
    resp = gpt.send_request(prompt)
    answer = resp.json()['choices'][0]['message']['content']

# users_history...
    users_history[user_id]["assistant_content"] += answer
    save_to_json()

    keyboard = create_keyboard(["Продолжить решение", "Завершить решение"])
    bot.send_message(message.chat.id, answer, reply_markup=keyboard)

@bot.message_handler(commands=['end'])
@bot.message_handler(content_types=['text'], func=lambda message: message.text.lower() == "завершить решение")
def end_task(message):
    logging.info("Завершение решения")
    user_id = message.from_user.id
    bot.send_message(user_id, "Текущие решение завершено")
    users_history[user_id] = {}
    solve_task(message)









if __name__ == "__main__":
    logging.info("Бот запущен")
    bot.infinity_polling()