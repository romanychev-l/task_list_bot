from os import environ
import random
import pickle

from aiogram import Bot, Dispatcher, executor, types
from aiogram.utils.executor import start_webhook


WEBHOOK_HOST = 'https://lenichev.ru'
WEBHOOK_PATH = '/tasks/'
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

WEBAPP_HOST = '127.0.0.1'
WEBAPP_PORT = 7771

print(environ)
bot = Bot(token=environ.get('TG_TOKEN'))
dp = Dispatcher(bot)

#channel_id = -1001381328759
channel_id = -1001422711251
#channel_id = -1001380279825
my_id = 248603604
id_dict = {
    248603604: -1001381328759,
    # test
    #248603604: -1001422711251,
    363513023: -1001510058413
}

f = open(r'keyb.txt', 'rb')
keyb = pickle.load(f)
f.close()

OK = '✅'
NOK = '❌'


async def on_startup(dp):
    await bot.set_webhook(WEBHOOK_URL)


async def on_shutdown(dp):
    await bot.delete_webhook()


def put_string(s):
    a = s.split('\n')
    a = [ str(i + 1) + '. ' + a[i] for i in range(0, len(a))]
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


@dp.message_handler(commands=['enter'])
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
    print('msg', msg)
    if msg.text[:4] == 'План':
        try:
            a = put_string(msg.text[6:])

            key = types.InlineKeyboardMarkup()
            for i in range(0, len(a)):
                but = types.InlineKeyboardButton(text=NOK + ' ' + a[i],
                    callback_data=str(i+1))
                key.add(but)

            await bot.edit_message_text(chat_id=msg['chat']['id'],
                message_id=msg['message_id'], text='План:', reply_markup=key)
        except Exception as e:
            await bot.send_message(msg['chat']['id'], 'Неверный формат')

    elif msg['text'] == 'Выбрать победителя':
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


@dp.callback_query_handler(lambda c:True)
async def inline(c):
    global keyb
    keyb = c['message']['reply_markup']

    if not c['from']['id'] in id_dict.keys():
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

    await bot.edit_message_reply_markup(chat_id=c['message']['chat']['id'],
        message_id=c.message.message_id, reply_markup=keyb)


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
