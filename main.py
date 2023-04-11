import config
import messages
import random
import pickle
import os
import time
import asyncio
from multiprocessing import Process


from aiogram import Bot, Dispatcher, executor, types
from aiogram.utils.executor import start_webhook


WEBHOOK_HOST = 'https://pmpu.site'
WEBHOOK_PATH = '/tasks/'
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

WEBAPP_HOST = '127.0.0.1'
WEBAPP_PORT = 7771

bot = Bot(token=config.token)
dp = Dispatcher(bot)

channel_id = -1001381328759
my_id = 248603604

file_id = 'file_id'
file_callback = 'file_callback'
file_statistics = 'statistics'

id_map = {
    248603604: -1001381328759,
    1037814936: -1001326413554,
    # test
    #248603604: -1001422711251,
    363513023: -1001510058413,
    233305672: -1001791613421,
    1317090820: -1001601747745
}
callback_data = {}
last_time = {}
statistics = {}

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


def read_data(fi):
    with open(fi, 'rb') as f:
        data_new = pickle.load(f)

    return data_new


def write_data(data, name_file):
    with open(name_file, 'wb') as f:
        pickle.dump(data, f)


def check_data(obj, name_file, empty=False):
    if not os.path.isfile(name_file) or empty:
        write_data(obj, name_file)
        return obj
    else:
        return read_data(name_file)


@dp.message_handler(commands=['start'])
async def st(msg):
    print('start')
    print(msg)

    await msg.answer(messages.start)


@dp.message_handler(commands=['show_dev'])
async def st(msg):
    global statistics
    print('show_dev')
    print(msg)

    await msg.answer(str(statistics))


'''
@dp.message_handler(commands=['show'])
async def show(msg):
    return
    print(msg)
    global statistics

    channel_username = msg.message.sender_chat.title
    if msg.message.sender_chat.username != None:
        channel_username = msg.message.sender_chat.username

    person = statistics[channel_username]['person']
    general = statistics[channel_username]['general']
    text = ('Ты сделал ' + str(person) + ' дел\n' +
            'Твои подписчики сделали ' + str(general) + ' дел\n' +
            'Всего ' + str(person + general))

    await msg.answer(text)
'''

@dp.message_handler(commands=['show_all'])
async def show_all(msg):
    global statistics
    print(statistics)

    if not msg.from_user.id in id_map.keys():
        await msg.answer('Вы не ведете свой канал и не можете просматривать статистику')
        return

    all_person = 0
    all_general = 0
    text = ''
    for item in statistics.keys():
        person = statistics[item]['person']
        general = statistics[item]['general']
        all_person += person
        all_general += general

        text = (text + '@' + item + '\n' +
                'Пользователь ' + str(person) + '\n' +
                'Подписчики ' + str(general) + '\n\n')

    text = text + 'Все пользователи ' + str(all_person) + '\n' + 'Все подписчики ' + str(all_general)
    await msg.answer(text)


def validate_forwarded_msg_type(msg):
    return (msg.forward_from_chat != None and
            msg.forward_from_chat.type != None and
            msg.forward_from_chat.type == 'channel')


@dp.channel_post_handler(content_types=["text"])
async def write_plan(msg):
    print(msg)
    global callback_data
    global file_callback

    # callback_data = read_data(file_callback)

    if msg.text[:4] == 'План':
        try:
            callback_data[msg.message_id] = {}
            points = put_string(msg.text[6:])

            key = types.InlineKeyboardMarkup()
            for i in range(0, len(points)):
                callback_data[msg.message_id][i] = []

                but = types.InlineKeyboardButton(text=NOK + ' ' + points[i],
                    callback_data=str(i+1))
                key.add(but)

            await bot.edit_message_text(chat_id=msg.chat.id,
                message_id=msg.message_id, text='План:', reply_markup=key)
        except Exception as e:
            print(e)
            await bot.send_message(msg.chat.id, messages.wrong_format)

    write_data(callback_data, file_callback)

def add_pros(text, pros):
    if text[-1] == ')':
        text = ' '.join(text.split()[:-1])

    if pros > 0:
        text = text + ' (+' + str(pros) + ')'

    return text


@dp.callback_query_handler(lambda c:True)
async def inline(call):
    print(call)

    global file_id
    global id_map
    global file_callback
    global callback_data
    global file_callback
    global file_statistics
    global statistics

    user_id = call['from']['id']
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    data = int(call.data)
    point_index = abs(data) - 1

    # id_map = read_data(file_id)

    # callback_data = read_data(file_callback)
    # statistics = read_data(file_statistics)

    if not message_id in callback_data:
        await call.answer(text=messages.past_day, show_alert=True)
        return

    if user_id in id_map.keys() and chat_id == id_map[user_id]:
        pass
    else:
        time_now = int(time.time())
        if not user_id in last_time.keys():
            last_time[user_id] = {point_index: time_now}

        elif not point_index in last_time[user_id].keys():
            last_time[user_id][point_index] = time_now

        else:
            time_delta_admin = 30
            time_delta_user = time_now - last_time[user_id][point_index]
            if time_delta_user < time_delta_admin:
                await call.answer(
                    text=messages.wait + str(time_delta_admin - time_delta_user) + ' сек.',
                    show_alert=True)
                return
            else:
                last_time[user_id][point_index] = time_now

    action_general = 1
    action_personal = 0
    if user_id in callback_data[message_id][point_index]:
        callback_data[message_id][point_index].remove(user_id)
        action_general = -1
    else:
        callback_data[message_id][point_index].append(user_id)
    
    count_pros = len(callback_data[message_id][point_index])

    #if call.message.sender_chat.username != None:
    #    await bot.send_message(my_id, '@' + call.message.sender_chat.username)

    keyb = call['message']['reply_markup']
    text_button = keyb['inline_keyboard'][point_index][0]['text']

    prefix = text_button[:2]
    new_data = str(data)

    if user_id in id_map.keys() and chat_id == id_map[user_id]:
        action_general = 0
        new_data = str(-data)
        if data > 0:
            prefix = OK + ' '
            action_personal = 1
        else:
            prefix = NOK + ' '
            action_personal = -1

    if prefix[0] == OK:
        count_pros -= 1
    new_text = add_pros(text_button[2:], count_pros)

    keyb['inline_keyboard'][point_index][0] = types.InlineKeyboardButton(
        text=prefix + new_text, callback_data=new_data)

    user_username = call.from_user.first_name
    if call.from_user.username != None:
        user_username = '@' + call.from_user.username

    channel_username = call.message.sender_chat.title
    if call.message.sender_chat.username != None:
        channel_username = call.message.sender_chat.username

    if channel_username in statistics.keys():
        action_general += statistics[channel_username]['general']
        action_personal += statistics[channel_username]['person']

    statistics[channel_username] = {'general': action_general,
                                        'person': action_personal}

    await bot.send_message(my_id,
        user_username + ' in @' + channel_username + '\n' + text_button)

    await bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id,
        reply_markup=keyb)

    write_data(callback_data, file_callback)
    write_data(statistics, file_statistics)


@dp.message_handler()
async def forwarded_msg(msg):
    print(msg)
    if not validate_forwarded_msg_type(msg):
        await msg.answer(messages.forward)
        return

    user_id = msg.from_user.id
    channel_id = msg.forward_from_chat.id
    id_map[user_id] = channel_id
    write_data(id_map, file_id)

    await msg.answer(messages.success)


async def run_bot():
    print('run bot')
    time.sleep(5)
    start_webhook(
            dispatcher=dp,
            webhook_path=WEBHOOK_PATH,
            on_startup=on_startup,
            on_shutdown=on_shutdown,
            skip_updates=True,
            host=WEBAPP_HOST,
            port=WEBAPP_PORT,
        )


async def run_save_loop():
    print('run save loop')
    global file_id
    global id_map
    global file_callback
    global callback_data
    global file_callback
    global file_statistics
    global statistics

    id_map = check_data(id_map, file_id)
    callback_data = check_data(callback_data, file_callback)
    statistics = check_data(statistics, file_statistics)
    print('read data')
    print(str(statistics))

    while True:

        await asyncio.sleep(3600)

        print('New save iter')
        write_data(id_map, file_id)
        write_data(statistics, file_statistics)
        write_data(callback_data, file_callback)
        


def main():
    global file_id
    global id_map
    global file_callback
    global callback_data
    global file_callback
    global file_statistics
    global statistics

    id_map = check_data(id_map, file_id)
    callback_data = check_data(callback_data, file_callback)
    statistics = check_data(statistics, file_statistics)

    start_webhook(
            dispatcher=dp,
            webhook_path=WEBHOOK_PATH,
            on_startup=on_startup,
            on_shutdown=on_shutdown,
            skip_updates=True,
            host=WEBAPP_HOST,
            port=WEBAPP_PORT,
        )
    # tasks = [asyncio.create_task(run_bot()), asyncio.create_task(run_save_loop())]

    # await asyncio.gather(*tasks)

    # await run_save_loop()
    # await run_bot()
    # pass
    # run_save_loop())


if __name__ == '__main__':
    # pr1 = Process(target=main)
    # pr2 = Process(target=run_bot)

    # pr1.start()
    # pr2.start()
    asyncio.run(main())