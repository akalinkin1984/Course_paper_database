import os
import random

from telebot import types, TeleBot, custom_filters
from telebot.storage import StateMemoryStorage
from telebot.handler_backends import State, StatesGroup
import sqlalchemy
from sqlalchemy.orm import sessionmaker

from models import create_tables, initial_data, Word, User, UserWord


print('Бот запущен...')

state_storage = StateMemoryStorage()
token_bot = input('Введите токен бота: ')
bot = TeleBot(token_bot, state_storage=state_storage)

driver_db = input('Введите название СУБД: ')
login = input('Введите имя пользователя: ')
password = input('Введите пароль: ')
host = input('Введите host сервера: ')
port = input('Введите порт сервера: ')
name_db = input('Введите название БД: ')

DSN = f'{driver_db}://{login}:{password}@{host}:{port}/{name_db}'
engine = sqlalchemy.create_engine(DSN)

path = os.getcwd() + '\\data.json'

known_users = []
buttons = []

session = sessionmaker(bind=engine)()


def show_hint(*lines):
    return '\n'.join(lines)


def show_target(data):
    return f"{data['target_word']} -> {data['translate_word']}"


class Command:
    ADD_WORD = 'Добавить слово ➕'
    DELETE_WORD = 'Удалить слово🔙'
    NEXT = 'Дальше ⏭'


class MyStates(StatesGroup):
    target_word = State()
    translate_word = State()
    another_words = State()


def del_word_db(message):
    chat_id = message.chat.id
    user_id = session.query(User.id).filter(User.user_id == chat_id)
    eng_word = message.text

    all_words_object_for_user = session.query(Word.eng).join(UserWord, UserWord.word_id == Word.id).filter(
        UserWord.user_id == user_id).all()

    count_word = session.query(UserWord).filter(UserWord.user_id == user_id).all()
    if len(count_word) == 5:
        bot.send_message(chat_id, f'В Вашем словаре осталось {len(count_word)} слов. Больше удалять нельзя!')
        create_cards(message)
        return

    all_words_list_for_user = []
    for i in all_words_object_for_user:
        all_words_list_for_user.append(i[0])

    if eng_word not in all_words_list_for_user:
        bot.send_message(chat_id, f'Такого слова в Вашем словаре нет!')
        print(f'Такого слова в Вашем словаре нет!')
        create_cards(message)
        return
    else:
        word_id = session.query(Word.id).filter(Word.eng == eng_word)
        session.query(UserWord).filter((UserWord.word_id == word_id) & (UserWord.user_id == user_id)).delete()
        bot.send_message(chat_id, f'Слово {message.text} удалено из Вашего словаря!')
        print(f'Слово {message.text} удалено из Вашего словаря!')
        session.commit()

    create_cards(message)


def add_word_db(message):
    chat_id = message.chat.id
    eng_word = message.text.split()[0].lower()
    rus_word = message.text.split()[1].lower()

    word_id = session.query(Word.id).filter(Word.eng == eng_word)
    user_id = session.query(User.id).filter(User.user_id == chat_id)
    if not word_id.all():
        session.add(Word(eng=eng_word, rus=rus_word))
        session.add(UserWord(user_id=user_id, word_id=word_id))
        session.commit()
        count_word = session.query(UserWord).filter(UserWord.user_id == user_id).all()
        bot.send_message(chat_id, f'Пара слов "{eng_word} - {rus_word}" сохранена для пользователя с id {chat_id}.')
        bot.send_message(chat_id, f'В Вашем словаре - {len(count_word)} слов.')
        print(f'Пара слов "{eng_word} - {rus_word}" сохранена для пользователя с id {chat_id}.')
        print(f'В Вашем словаре - {len(count_word)} слов.')
        create_cards(message)
        return

    user_word_id_list = session.query(UserWord.word_id).filter(UserWord.user_id == user_id)

    if word_id.one() not in user_word_id_list.all():
        session.add(UserWord(user_id=user_id, word_id=word_id))
        session.commit()
        count_word = session.query(UserWord).filter(UserWord.user_id == user_id).all()
        bot.send_message(chat_id, f'Пара слов {eng_word} - {rus_word} сохранена для пользователя с id {chat_id}.')
        bot.send_message(chat_id, f'В Вашем словаре - {len(count_word)} слов.')
        print(f'Пара слов {eng_word} - {rus_word} сохранена для пользователя с id {chat_id}.')
        print(f'В Вашем словаре - {len(count_word)} слов.')
    else:
        bot.send_message(chat_id, f'Данная пара слов уже есть в Вашем словаре!')
        print(f'Данная пара слов уже есть в Вашем словаре!')

    create_cards(message)


@bot.message_handler(commands=['cards', 'start'])
def create_cards(message):
    chat_id = message.chat.id
    if chat_id not in known_users:
        known_users.append(chat_id)

        session.add(User(user_id=chat_id))
        session.commit()

        user_id = session.query(User.id).filter(User.user_id == chat_id).scalar_subquery()
        for s in session.query(Word.id).limit(10):
            session.add(UserWord(user_id=user_id, word_id=s[0]))
        session.commit()
        bot.send_message(chat_id, "Привет, давай изучать английский...")
    markup = types.ReplyKeyboardMarkup(row_width=2)

    global buttons
    buttons = []
    all_words_pair_user = []
    all_words_objects_user = (session.query(Word)
                              .join(UserWord, Word.id == UserWord.word_id)
                              .join(User, User.id == UserWord.user_id)
                              .filter(User.user_id == chat_id))
    for pair in all_words_objects_user.all():
        eng_word = str(pair).split()[0]
        rus_word = str(pair).split()[1]
        all_words_pair_user.append((eng_word, rus_word))

    word_pair = random.choice(all_words_pair_user)
    target_word = word_pair[0]
    translate = word_pair[1]
    all_words_pair_user.remove(word_pair)

    target_word_btn = types.KeyboardButton(target_word)
    buttons.append(target_word_btn)

    others = []
    for i in range(4):
        word_pair = random.choice(all_words_pair_user)
        eng_word = word_pair[0]
        others.append(eng_word)
        all_words_pair_user.remove(word_pair)

    other_words_btns = [types.KeyboardButton(word) for word in others]
    buttons.extend(other_words_btns)
    random.shuffle(buttons)
    next_btn = types.KeyboardButton(Command.NEXT)
    add_word_btn = types.KeyboardButton(Command.ADD_WORD)
    delete_word_btn = types.KeyboardButton(Command.DELETE_WORD)
    buttons.extend([next_btn, add_word_btn, delete_word_btn])

    markup.add(*buttons)

    greeting = f"Выбери перевод слова:\n🇷🇺 {translate}"
    bot.send_message(message.chat.id, greeting, reply_markup=markup)
    bot.set_state(message.from_user.id, MyStates.target_word, message.chat.id)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['target_word'] = target_word
        data['translate_word'] = translate
        data['other_words'] = others


@bot.message_handler(func=lambda message: message.text == Command.NEXT)
def next_cards(message):
    create_cards(message)


@bot.message_handler(func=lambda message: message.text == Command.DELETE_WORD)
def delete_word(message):
    chat_id = message.chat.id
    markup = types.ReplyKeyboardMarkup(row_width=2)
    print(message.text)
    bot.send_message(chat_id, 'Какое слово хотите удалить? Введите на английском языке', reply_markup=markup)
    bot.register_next_step_handler(message, del_word_db)


@bot.message_handler(func=lambda message: message.text == Command.ADD_WORD)
def add_word(message):
    chat_id = message.chat.id
    markup = types.ReplyKeyboardMarkup(row_width=2)
    print(message.text)
    bot.send_message(chat_id, 'Какую пару слов хотите добавить?', reply_markup=markup)
    bot.register_next_step_handler(message, add_word_db)


@bot.message_handler(func=lambda message: True, content_types=['text'])
def message_reply(message):
    text = message.text
    markup = types.ReplyKeyboardMarkup(row_width=2)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        target_word = data['target_word']
        if text == target_word:
            hint = show_target(data)
            hint_text = ["Отлично!❤", hint]
            next_btn = types.KeyboardButton(Command.NEXT)
            add_word_btn = types.KeyboardButton(Command.ADD_WORD)
            delete_word_btn = types.KeyboardButton(Command.DELETE_WORD)
            buttons.extend([next_btn, add_word_btn, delete_word_btn])
            hint = show_hint(*hint_text)
        else:
            for btn in buttons:
                if btn.text == text:
                    btn.text = text + '❌'
                    break
            hint = show_hint("Допущена ошибка!",
                             f"Попробуй ещё раз вспомнить слово 🇷🇺{data['translate_word']}")
    markup.add(*buttons)
    bot.send_message(message.chat.id, hint, reply_markup=markup)


if __name__ == '__main__':
    create_tables(engine)
    initial_data(path, session)
    bot.add_custom_filter(custom_filters.StateFilter(bot))
    bot.infinity_polling(skip_pending=True)

session.close()
