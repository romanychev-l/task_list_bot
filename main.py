import config
import random
import pickle

from aiogram import Bot, Dispatcher, executor, types
from aiogram.utils.executor import start_webhook


WEBHOOK_HOST = 'https://romanychev.online'
WEBHOOK_PATH = '/tasks/'
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

WEBAPP_HOST = '127.0.0.1'
WEBAPP_PORT = 7771

bot = Bot(token=config.token)
dp = Dispatcher(bot)

#channel_id = -1001381328759
channel_id = -1001380279825
my_id = 248603604

f = open(r'keyb.txt', 'rb')
keyb = pickle.load(f)#types.InlineKeyboardMarkup(pickle.load(f))
f.close()

OK = '✅'
NOK = '❌'


async def on_startup(dp):
    await bot.set_webhook(WEBHOOK_URL)


async def on_shutdown(dp):
    await bot.delete_webhook()


def put_string(s):
	l = 0
	r = 2
	a = []
	while(r < len(s)):
		if s[r] == '\n':
			a.append(s[l:r])
			l = r + 1
			r += 1
		else:
			r += 1
	a.append(s[l:r])
	return a


def get_data():
    f = open('members.txt')
    data = []
    for line in f:
        data.append(line[:-1])

    f.close()
    return data


def update_data(data):
    f = open('members.txt', 'w')
    for val in data:
        f.write(val + '\n')

    f.close()


def up_keyb():
    f = open(r'keyb.txt', 'wb')
    pickle.dump(keyb, f)
    f.close()


@dp.message_handler(commands=['start'])
async def reg_fun(msg):
    if(not 'username' in msg['chat']):
        await bot.send_message(msg['chat']['id'], 'Я не вижу ваш ник - откройте доступ в настройках и повторите команду')
        return
    username = msg['chat']['username']
    data = get_data()
    if username in data:
        await bot.send_message(msg['chat']['id'], 'Вы уже участвуете!')
        return

    data.append(username)
    update_data(data)
    await bot.send_message(msg['chat']['id'], 'Вы успешно зарегистрированы!')


@dp.message_handler(commands=['finish'])
async def unreg_fun(msg):
    data = get_data()
    username = msg['chat']['username']
    if username in data:
        data.remove(username)
        update_data(data)
        await bot.send_message(msg['chat']['id'], 'Вы отписались от игры!')
    else:
        await bot.send_message(msg['chat']['id'], 'Вы еще не зарегистированы')


@dp.channel_post_handler(content_types=["text"])
async def get_winner(msg):
    if msg['text'] != 'Выбрать победителя':
        return
    chat_id = msg['chat']['id']
    if chat_id != my_id and chat_id != channel_id:
        return
    data = get_data()
    n = len(data)
    await bot.send_message(my_id, 'Всего участников ' + str(n))
    if n == 0:
        return
    k = random.randint(0, n-1)
    await bot.send_message(channel_id, 'Сегодня выиграл:\n@' + data[k] + '\n' +\
    'Чтобы участвовать в розыгрыше запусти бота @romanychev_bot')


@dp.message_handler(content_types=["text"])
async def inline(message):
    if message.text[:4] != 'План':
        return
    a = put_string(message.text[5:])

    key = types.InlineKeyboardMarkup()
    for i in range(0, len(a)):
        but = types.InlineKeyboardButton(text=NOK + ' ' + a[i], callback_data=str(i+1))
        key.add(but)
    global keyb
    keyb = key
    up_keyb()

    await bot.send_message(channel_id, 'План:', reply_markup=key)


@dp.callback_query_handler(lambda c:True)
async def inline(c):
    global keyb
    if c['from']['id'] != my_id:
        return

    d = int(c.data)
    if d > 0:
        but = types.InlineKeyboardButton(text=NOK, callback_data=str(-1*d))
    else:
        but = types.InlineKeyboardButton(text=OK, callback_data=str(-1*d))
    n = len(keyb['inline_keyboard'])
    for i in range(n):
        if keyb['inline_keyboard'][i][0]['callback_data'] == str(d):
            t = keyb['inline_keyboard'][i][0]['text'][2:]
            if d > 0:
                but = types.InlineKeyboardButton(text=OK + ' ' + t, callback_data=str(-1*d))
            else:
                but = types.InlineKeyboardButton(text=NOK + ' ' + t, callback_data=str(-1*d))

            keyb['inline_keyboard'][i][0] = but

    await bot.edit_message_reply_markup(chat_id=channel_id, message_id=c.message.message_id, reply_markup=keyb)


if __name__ == '__main__':
    start_webhook(
        dispatcher=dp,
        webhook_path=WEBHOOK_PATH,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
        skip_updates=True,
        host=WEBAPP_HOST,
        port=WEBAPP_PORT,
    )
