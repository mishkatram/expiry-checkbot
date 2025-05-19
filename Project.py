import telebot
import sqlite3
import html
import threading
from dateutil.relativedelta import relativedelta
from time import sleep
from datetime import datetime, timedelta, date
from telebot import types
from Config import TOKEN

bot = telebot.TeleBot(TOKEN)
conn = sqlite3.connect('Project.sql')
cur = conn.cursor()
cur.execute('CREATE TABLE IF NOT EXISTS table_1 (id integer primary key autoincrement not null, tg_id int, '
            'crutch text, product text, finish_time text, finish_date text)')
conn.commit()
cur.close()
conn.close()
add_dict = {}


@bot.message_handler(commands=['start'])
def start(message):
    time = datetime.now()
    hour = time.hour
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    if hour < 5:
        bot.send_message(message.chat.id, f'Доброй ночи, {first_name} {last_name}!')
    elif hour < 12:
        bot.send_message(message.chat.id, f'Доброе утро, {first_name} {last_name}!')
    elif hour < 17:
        bot.send_message(message.chat.id, f'Добрый день, {first_name} {last_name}!')
    else:
        bot.send_message(message.chat.id, f'Добрый вечер, {first_name} {last_name}!')
    start_main_menu(message)


@bot.message_handler(commands=['list'])
def start_main_menu(message):
    parts = message.text.strip().split()
    if len(parts) > 1 and parts[1].isdigit():
        page = int(parts[1]) - 1
    else:
        page = 0
    main_menu(message, page)


def main_menu(message, page):
    emoji_dict = {1: "1️⃣", 2: "2️⃣", 3: "3️⃣", 4: "4️⃣", 5: "5️⃣", 6: "6️⃣", 7: "7️⃣", 8: "8️⃣", 9: "9️⃣", 10: "🔟"}
    tgID = int(message.chat.id)
    conn = sqlite3.connect('Project.sql')
    cur = conn.cursor()
    cur.execute("SELECT * FROM table_1 WHERE tg_id = ? ORDER BY finish_date ASC, finish_time ASC", (tgID,))
    row = cur.fetchall()
    conn.commit()
    cur.close()
    buttons = []
    comment = ""
    if page > (len(row) - 1) // 10:
        comment = f"\nВы ввели несуществующую страницу! Вы переведены на максимальную странциу"
        page = (len(row) - 1) // 10
    info = f"<b>Список Ваших товаров: {comment}</b>\n(Страница {page + 1} из {(len(row) + 9) // 10})\n======\n"
    exp, void = False, False
    if not row:
        info = "<b>У вас нет зарегестрированных товаров!</b>\nДля добавления товара нажмите на кнопку ниже ⬇️"
        void = True
    else:
        for i in range(page * 10, min((page + 1) * 10, len(row))):
            date_obj = datetime.strptime(f"{row[i][5]} {row[i][4]}", "%Y-%m-%d %H:%M")
            formatted_date = date_obj.strftime("%d.%m.%Y %H:%M")
            now = datetime.now().replace(second=0, microsecond=0)
            expired = ""
            buttons.append(types.InlineKeyboardButton(emoji_dict[i % 10 + 1], callback_data=f"more#{page}*{row[i][0]}"))
            if date_obj < now:
                expired = "ПРОСРОЧЕН‼️\n"
                exp = True
            info += f'{emoji_dict[i % 10 + 1]} Товар: {html.escape(row[i][3])}.\n' \
                    f'Годен до: {formatted_date}\n{expired}-----\n'
        info += 'ℹ️ Всегда можно переключиться на нужную страницу, введя "/list &lt;i&gt;",' \
                ' где i - номер нужной страницы'
    markup = types.InlineKeyboardMarkup(row_width=5)
    markup.add(*buttons)
    nav_buttons = []
    if (len(row) - 1) // 10 != 0 and not void:
        if page > 0:
            nav_buttons.append(types.InlineKeyboardButton("⏪", callback_data=f"page#{page - 1}"))
        else:
            nav_buttons.append(types.InlineKeyboardButton("ㅤ", callback_data="no_act"))
        nav_buttons.append(types.InlineKeyboardButton(f"{page + 1} из {(len(row) + 9) // 10}", callback_data="no_act"))
        if page < (len(row) - 1) // 10:
            nav_buttons.append(types.InlineKeyboardButton("⏩", callback_data=f"page#{page + 1}"))
        else:
            nav_buttons.append(types.InlineKeyboardButton("ㅤ", callback_data="no_act"))
    markup.add(*nav_buttons)
    markup.add(types.InlineKeyboardButton("Добавить новый товар", callback_data="add#add"))
    if exp:
        markup.add(types.InlineKeyboardButton("Удалить просроченные товары", callback_data=f"del_exp_chek#{page}"))
    bot.send_message(message.chat.id, info, reply_markup=markup, parse_mode="HTML")


def more_menu(message, id, page):
    conn = sqlite3.connect('Project.sql')
    cur = conn.cursor()
    cur.execute("SELECT * FROM table_1 WHERE id = ?", (id,))
    row = cur.fetchall()
    conn.commit()
    cur.close()
    nm = row[0][3]
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton("⬅️ Назад", callback_data=f"page#{page}")
    btn2 = types.InlineKeyboardButton("🗑 Удалить", callback_data=f"del_chek#{page}*{id}")
    btn3 = types.InlineKeyboardButton("📝 Переим.", callback_data=f"rename#{page}*{id}")
    markup.row(btn1, btn2, btn3)
    bot.send_message(message.chat.id, f"<b>Товар: {html.escape(nm)}</b>\n"
                                      f"Выберите действие:", reply_markup=markup, parse_mode="HTML")


def add(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("↪️ Отменить действие", callback_data=f"cancel# "))
    item_card = {}
    bot.send_message(message.chat.id, 'Начинаем регистрацию нового товара. \n\n⚠️Товар считается вскрытым при его '
                                      'регистрации в базе данных⚠️. \n\nВведите наименование товара.\n(⚠️Пожалуйста, '
                                      'не используйте символ "#"⚠️)', reply_markup=markup)
    bot.register_next_step_handler(message, add2, item_card)


def add2(message, item_card):
    if message.text is None:
        bot.send_message(message.chat.id, '⚠️ Вы не ввели наименование товара — операция прервана!')
        return start_main_menu(message)
    name = message.text.strip()
    if "#" in name:
        bot.send_message(message.chat.id, '⚠️ В названии товара не используйте символ "#".')
        return start_main_menu(message)
    if len(name) > 200:
        bot.send_message(message.chat.id, '⚠️ В названии товара было использованно более 200 символов.')
        return start_main_menu(message)
    item_card['name'] = name
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("↪️ Отменить действие", callback_data=f"cancel# "))
    bot.send_message(message.chat.id, 'А теперь введите его срок годности (день, до которого его надо '
                                      'употребить).\nФормат ввода: \"ДД.ММ.ГГГГ\"', reply_markup=markup)
    bot.register_next_step_handler(message, add3, item_card)


def add3(message, item_card):
    global add_dict
    tgID = message.from_user.id
    if message.text is None:
        bot.send_message(message.chat.id, '⚠️ Вы не ввели дату — операция прервана!')
        return start_main_menu(message)
    fDate = message.text.strip()
    if Try(fDate):
        fDate = datetime.strptime(f"{fDate}", "%d.%m.%Y").date()
    else:
        bot.send_message(message.chat.id, '⚠️ Такая дата не существует!')
        return start_main_menu(message)
    if fDate <= date.today():
        bot.send_message(message.chat.id, '⚠️ Введена некорректная дата, т. к. в этом случае товар просрочен.')
        return start_main_menu(message)
    print(123)
    item_card['fDate'] = fDate
    if f"{tgID}" in add_dict:
        del add_dict[f"{tgID}"]
    add_dict[f'{tgID}'] = item_card
    bot.send_message(message.chat.id, 'Теперь надо ввести срок хранения товара в открытом виде.')
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton('Часы', callback_data=f"add#h")
    btn2 = types.InlineKeyboardButton('Дни', callback_data=f"add#d")
    btn3 = types.InlineKeyboardButton('Месяцы', callback_data=f"add#m")
    markup.row(btn1, btn2, btn3)
    markup.add(types.InlineKeyboardButton("↪️ Отменить действие", callback_data=f"cancel# "))
    bot.send_message(message.chat.id, 'Для этого нажмите на кнопку размерности '
                                      '(кол-во часов/дней/месяцев)', reply_markup=markup)
    add_dict[str(tgID)] = item_card
    add_dict[str(tgID)]["awaiting_dimension"] = True


def add_4(message, dim):
    global add_dict
    fn_tm = "00:00"
    tgID = message.from_user.id
    if message.text is None:
        bot.send_message(message.chat.id, '⚠️ Вы не ввели срок хранения — операция прервана!')
        return start_main_menu(message)
    fTime = str(message.text.strip())
    if not fTime.isdigit():
        bot.send_message(message.chat.id, "⚠️ Вы ввели какую-то странную абракадабру — операция прервана!")
        return start_main_menu(message)
    if dim == "h":
        fTime = datetime.now() + timedelta(hours=int(fTime))
    elif dim == "d":
        fTime = datetime.now() + timedelta(days=int(fTime))
    elif dim == "m":
        fTime = datetime.now() + relativedelta(month=int(fTime))
    dt_us_dict = add_dict[f"{tgID}"]
    fDate = dt_us_dict["fDate"]
    name = dt_us_dict["name"]
    if fDate > fTime.date():
        fDate = fTime.date()
        fn_tm = str(fTime.strftime("%H:%M"))
    if fDate == date.today():
        bot.send_message(message.chat.id, f"⚠️ Срок годности этого товара истекает сегодня в {fn_tm}⚠️")
    conn = sqlite3.connect('Project.sql')
    cur = conn.cursor()
    cur.execute("INSERT INTO table_1 (tg_id, product, finish_time, finish_date) VALUES (?, ?, ?, ?)",
                (tgID, name, fn_tm, fDate))
    bot.send_message(message.chat.id, '✅ Добавил!')
    conn.commit()
    cur.close()
    start_main_menu(message)


def rename(message, product_id, old_naim):
    if message.text is None:
        return start_main_menu(message)
    new_name = message.text.strip()
    if "#" in new_name:
        bot.send_message(message.chat.id, '⚠️ В названии товара не используйте символ "#".')
        return start_main_menu(message)
    conn = sqlite3.connect('Project.sql')
    cur = conn.cursor()
    cur.execute("UPDATE table_1 SET product = ? WHERE id = ?", (new_name, product_id))
    conn.commit()
    bot.send_message(message.chat.id, f'✅ Товар "{html.escape(old_naim[:27])}..." <b>успешно переименован</b>'
                                      f' в "{html.escape(new_name)}".', parse_mode="HTML")
    cur.close()
    conn.close()
    start_main_menu(message)


def delete(message, ID):
    conn = sqlite3.connect('Project.sql')
    cur = conn.cursor()
    cur.execute("DELETE FROM table_1 WHERE id = ?", (ID,))
    bot.send_message(message.chat.id, '✅ Удалено!')
    conn.commit()
    cur.close()
    start_main_menu(message)


def delete_expired(message):
    tgID = message.chat.id
    print(tgID)
    conn = sqlite3.connect('Project.sql')
    cur = conn.cursor()
    now = datetime.now()
    current_date = now.strftime('%Y-%m-%d')
    current_time = now.strftime('%H:%M')
    cur.execute("DELETE FROM table_1 WHERE tg_id = ? AND (finish_date < ? OR (finish_date = ? AND "
                "finish_time < ?))", (tgID, current_date, current_date, current_time))
    conn.commit()
    cur.close()
    bot.send_message(message.chat.id, '✅ Удалено!')
    start_main_menu(message)


@bot.callback_query_handler(func=lambda callback: True)
def callback_message(callback):
    callback_data, other = str(callback.data).split("#")
    if callback_data == "add":
        if other == "add":
            add(callback.message)
            return
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("↪️ Отменить действие", callback_data=f"cancel# "))
        bot.send_message(callback.message.chat.id, "А теперь введите численное значение", reply_markup=markup)
        bot.register_next_step_handler(callback.message, add_4, other)
    if callback_data == "info" or callback_data == "delete":
        pass
    if callback_data == "del":
        delete(callback.message, other)
        print(other)
    if callback_data == "page":
        main_menu(callback.message, int(other))
    if callback_data == "more":
        page, id = other.split("*")
        more_menu(callback.message, int(id), int(page))
    if callback_data == "del_chek":
        page, id = other.split("*")
        bot.answer_callback_query(callback.id)
        markup = types.InlineKeyboardMarkup()
        conn = sqlite3.connect('Project.sql')
        cur = conn.cursor()
        cur.execute("SELECT * FROM table_1 WHERE id = ?", (id,))
        row = cur.fetchall()
        conn.commit()
        cur.close()
        btn1 = types.InlineKeyboardButton("✅ Да", callback_data=f"del#{id}")
        btn2 = types.InlineKeyboardButton("❌ Нет", callback_data=f"more#{page}*{id}")
        markup.row(btn1, btn2)
        bot.send_message(callback.message.chat.id, f"Вы уверенны что хотите удалить {row[0][3]}?", reply_markup=markup)
    if callback_data == "del_exp_chek":
        bot.answer_callback_query(callback.id)
        markup = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton("✅ Да", callback_data="del_exp# ")
        btn2 = types.InlineKeyboardButton("❌ Нет", callback_data=f"page#{other}")
        markup.row(btn1, btn2)
        bot.send_message(callback.message.chat.id, f"Вы уверенны что хотите удалить <b>ВСЕ</b> "
                                                   f"просроченные товары?", reply_markup=markup, parse_mode="HTML")
    if callback_data == "del_exp":
        delete_expired(callback.message)
    if callback_data == "cancel":
        start_main_menu(callback.message)
    if callback_data == "rename":
        page, id = other.split("*")
        bot.answer_callback_query(callback.id)
        conn = sqlite3.connect('Project.sql')
        cur = conn.cursor()
        cur.execute("SELECT * FROM table_1 WHERE id = ?", (id,))
        row = cur.fetchall()
        conn.commit()
        cur.close()
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("↪️ Отменить действие", callback_data=f"more#{page}*{id}"))
        bot.send_message(callback.message.chat.id, f'Переименновываем товар {row[0][3]}\nДля этого введите новое '
                                                   f'название\n(⚠️Пожалуйста, не используйте символ '
                                                   f'"#"⚠️)', reply_markup=markup)
        bot.register_next_step_handler(callback.message, rename, id, row[0][3])


def is_awaiting_dimension(message):
    user_id = str(message.from_user.id)
    return user_id in add_dict and add_dict[user_id].get("awaiting_dimension")


@bot.message_handler(func=is_awaiting_dimension)
def reject_text_input(message):
    bot.send_message(message.chat.id, "⚠️ Сейчас нужно выбрать размерность срока хранения, "
                                      "а не писать текст.\nНажмите кнопку выше ⬆️")


def notify_users_about_today_expirations():
    today = date.today()
    conn = sqlite3.connect('Project.sql')
    cur = conn.cursor()
    cur.execute("SELECT product, tg_id, finish_time FROM table_1 WHERE finish_date"
                " = ? ORDER BY finish_date ASC, finish_time ASC", (str(today),))
    rows = cur.fetchall()
    user_messages = {}
    for product, tg_id, finish_time in rows:
        if tg_id not in user_messages:
            user_messages[tg_id] = "‼️<b>Сегодня истекает срок годности у этих товаров:</b>\n"
        user_messages[tg_id] += f"● <b>{html.escape(product)}</b> — срок годности истечёт в <b>{finish_time}</b>\n"
    for tg_id, msg in user_messages.items():
        msg += "ℹ️ Для продолжения работы с ботом введите /list"
        bot.send_message(int(tg_id), msg, parse_mode="HTML")
    cur.close()
    conn.close()


def midnight_notifier():
    while True:
        now = datetime.now()
        if now.hour == 0 and now.minute == 0:
            notify_users_about_today_expirations()
            sleep(61)
        else:
            sleep(55)


def Try(Date):
    try:
        datetime.strptime(f"{Date}", "%d.%m.%Y").date()
        return True
    except ValueError:
        return False


threading.Thread(target=midnight_notifier, daemon=True).start()
while True:
    try:
        bot.polling(none_stop=True)
    except Exception as _ex:
        print(_ex)
        sleep(5)
