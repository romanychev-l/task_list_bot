import config
import messages
import time
import os
import asyncio
import random
from multiprocessing import Process
from pathlib import Path
import pymongo
import requests
from datetime import datetime, timezone
import whisper

from aiogram import Bot, Dispatcher, executor, types
from aiogram.utils.executor import start_webhook
from aiogram.utils.deep_linking import get_start_link
from aiogram.dispatcher.filters import IsReplyFilter

WEBHOOK_HOST = 'https://pmpu.site'
WEBHOOK_PATH = '/tasks/'
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

WEBAPP_HOST = '127.0.0.1'
WEBAPP_PORT = 7771

mongo_client = pymongo.MongoClient("mongodb://localhost:27017/")
mongo_db = mongo_client["task-list-bot-DB"]

mongo_callback_data = mongo_db["callback_data"]  # channel_username, message_id, список users нажавших на каждое дело
mongo_id = mongo_db["id"]  # user_id, channel_id
mongo_statistics = mongo_db["statistics"]  # channel_username, person, general
mongo_last_time = mongo_db["last_time"]  # user_id, список point_ind, список time_now

model = whisper.load_model('base')

bot = Bot(token=config.token)
dp = Dispatcher(bot)

channel_id = -1001381328759
my_id = 248603604

OK = '✅'
NOK = '❌'

fruits = {
    '🍏': 'зелёных яблочек',
    '🍎': 'красных яблочек',
    '🍐': 'грушек',
    '🍊': 'апельсинчиков',
    '🍋': 'лимончиков',
    '🍌': 'бананчиков',
    '🍉': 'арбузиков',
    '🍇': 'виноградинок',
    '🍓': 'клубничек',
    '🫐': 'черничек',
    '🍈': 'дынек',
    '🍒': 'вишенек',
    '🍑': 'персиков',
    '🥭': 'манго',
    '🍍': 'ананасиков',
    '🥥': 'кокосиков',
    '🥝': 'киви',
    '🍅': 'помидорок',
    '🍆': 'баклажанчиков',
    '🥑': 'авокадиков',
    '🥦': 'брокколи'
}

fruit_timer_minutes = 25


async def on_startup(dp):
    await bot.set_webhook(WEBHOOK_URL)


async def on_shutdown(dp):
    await bot.delete_webhook()


def removeFile(file):
    if os.path.isfile(file):
        os.remove(file)
    else:  ## Show an error ##
        print("Error: %s file not found" % file)


def put_string(s):
    a = s.split('\n')
    a = [str(i + 1) + '. ' + a[i] for i in range(0, len(a))]
    return a


def validate_forwarded_msg_type(msg):
    return (msg.forward_from_chat is not None and
            msg.forward_from_chat.type is not None and
            msg.forward_from_chat.type == 'channel')


def add_pros(text, pros):
    if text[-1] == ')':
        text = ' '.join(text.split()[:-1])
    if pros > 0:
        text = text + ' (+' + str(pros) + ')'

    return text


@dp.message_handler(commands=['start'])
async def start(msg):
    print('start')
    print(msg)

    args = msg.get_args()
    if args == 'show_all':
        await show_all(msg)
    elif args == 'show_steps':
        await show_steps(msg)
    else:
        await msg.answer(messages.start)


@dp.message_handler(commands=['show_dev'])
async def show_dev(msg):
    print('show_dev')
    print(msg)
    for x in mongo_statistics.find({}, {'_id': 0}):
        print(x)
        await msg.answer(x)


'''
@dp.message_handler(commands=['show'])
async def show(msg):
    return
    print(msg)

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


@dp.message_handler(commands=['show_steps'])
async def show_steps(msg):
    await msg.answer('Функция пока не доступна, попробуйте позже')


@dp.message_handler(commands=['show_all'])
async def show_all(msg):
    """Вызывается для просмотра статистики по кол-ву сделанных дел"""

    '''
    if mongo_id.find_one({'user_id': msg.from_user.id}) is None:
        await msg.answer(messages.no_channel)
        return
    '''

    all_person = 0
    all_general = 0
    text = ''
    for item in mongo_statistics.find().sort('person', -1):
        person = item['person']
        general = item['general']
        all_person += int(person)
        all_general += int(general)

        if person < 10:
            continue

        text = (text + '@' + item['channel_username'] + '\n' +
                'Пользователь ' + str(person) + '\n' +
                'Подписчики ' + str(general) + '\n\n')

    text = text + 'Все пользователи ' + str(all_person) + '\n' + 'Все подписчики ' + str(all_general)
    await msg.answer(text)


@dp.channel_post_handler(IsReplyFilter(is_reply=True), content_types=["voice"])
async def add_case_audio(msg):
    print('voice')
    print(msg)
    await msg.delete()

    file_id = msg.voice.file_id
    file = await bot.get_file(file_id)
    file_path = file.file_path
    file_name = f'{file_id}.ogg'
    file_on_disk = Path('tmp', file_name)
    await bot.download_file(file_path, destination=file_on_disk)

    result = model.transcribe('tmp/' + file_name)
    text = result['text']

    chat_id = msg.reply_to_message.chat.id
    message_id = msg.reply_to_message.message_id
    keyb = msg.reply_to_message.reply_markup

    channel_username = msg.sender_chat.username
    if channel_username == None:
        channel_username = msg.sender_chat.title

    amount = len(keyb.inline_keyboard)
    but = types.InlineKeyboardButton(text=NOK + ' ' + str(amount) + '. ' + text[0].upper() + text[1:], callback_data=str(amount))

    channel_id_data = mongo_id.find_one({'channel_id': msg.chat.id})
    index = amount - 1
    if 'fruit_number' in channel_id_data:
        index = amount - 2
        but_fruit = keyb.inline_keyboard[amount - 2][0]
        but_fruit['callback_data'] = f'fruit_{amount}'
        keyb.inline_keyboard[amount - 1][0] = but_fruit

        but = types.InlineKeyboardButton(text=NOK + ' ' + str(amount - 1) + '. ' +  text[0].upper() + text[1:], callback_data=str(amount - 1))

    keyb.inline_keyboard[index][0] = but

    link = await get_start_link('show_all')
    but = types.InlineKeyboardButton(text='ℹ️ Статистика по каналам', url=link),
    keyb.add(*but)

    # await msg.delete()
    mongo_callback_data.update_one({'message_id': message_id, 'channel_username':channel_username},
                                     {'$push': {'users': []}})

    await bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id, reply_markup=keyb)

    # await msg.reply(result['text'])

    id_data = {'key': dict(keyb)}
    mongo_id.update_one({'channel_id': chat_id}, {'$set': id_data})

    removeFile('tmp/' + file_name)


@dp.channel_post_handler(IsReplyFilter(is_reply=True), content_types=["text"])
async def add_case(msg):
    print('add')
    print(msg)

    if 'text' not in msg.reply_to_message or msg.reply_to_message.text[:4] != 'План':
        return

    try:
        await msg.delete()
    except Exception as e:
        return
    # user_id = msg.reply_to_message.from_user.id
    chat_id = msg.reply_to_message.chat.id
    message_id = msg.reply_to_message.message_id
    keyb = msg.reply_to_message.reply_markup

    channel_username = msg.sender_chat.username
    if channel_username == None:
        channel_username = msg.sender_chat.title

    print(keyb)

    amount = len(keyb.inline_keyboard)
    but = types.InlineKeyboardButton(text=NOK + ' ' + str(amount) + '. ' +  msg.text, callback_data=str(amount))

    channel_id_data = mongo_id.find_one({'channel_id': msg.chat.id})
    index = amount - 1
    if 'fruit_number' in channel_id_data:
        index = amount - 2
        but_fruit = keyb.inline_keyboard[amount - 2][0]
        but_fruit['callback_data'] = f'fruit_{amount}'
        keyb.inline_keyboard[amount - 1][0] = but_fruit

        but = types.InlineKeyboardButton(text=NOK + ' ' + str(amount - 1) + '. ' +  msg.text, callback_data=str(amount - 1))

    keyb.inline_keyboard[index][0] = but

    link = await get_start_link('show_all')
    but = types.InlineKeyboardButton(text='ℹ️ Статистика по каналам', url=link),
    keyb.add(*but)

    await bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id, reply_markup=keyb)

    # await msg.delete()
    mongo_callback_data.update_one({'message_id': message_id, 'channel_username': channel_username},
                                     {'$push': {'users': []}})

    id_data = {'key': dict(keyb)}
    mongo_id.update_one({'channel_id': chat_id}, {'$set': id_data})


@dp.channel_post_handler(content_types=["text"])
async def write_plan(msg):
    """ Вызывается при добавлении Плана в ТГ канал
        Добавляет соответствующий документ в БД в коллекцию callback_data"""

    print('added new plan \n', msg, "\n")
    channel_username = msg.chat.username

    if channel_username is None:
        channel_username = msg.sender_chat.title

    if msg.text[:4] == 'План':
        try:
            data = {'channel_username': channel_username, 'message_id': msg.message_id, 'users': []}
            points = put_string(msg.text[6:])

            key = types.InlineKeyboardMarkup()
            for i in range(0, len(points)):
                data['users'].append([])

                but = types.InlineKeyboardButton(text=NOK + ' ' + points[i],
                                                 callback_data=str(i + 1))
                key.add(but)

            channel_id_data = mongo_id.find_one({'channel_id': msg.chat.id})

            if 'fruit_number' in channel_id_data:
                fruit = random.choice(list(fruits))
                string = f'0 {fruit} {fruits[fruit]}'
                but = types.InlineKeyboardButton(text=string,
                                                callback_data=f'fruit_{len(points)+1}')
                key.add(but)

            # mongo_id.update_one({'channel_id': msg.chat.id}, {'$set': {'fruit_number': 0}})

            future_flag = False
            if future_flag and 'nocodeapi' in channel_id_data:
                step_count = await get_step_count(channel_id_data['nocodeapi'])
                step_limit = 10000
                string = f'{NOK} {len(points)+1}. Пройдено {step_count} шагов из {step_limit}'
                link = await get_start_link('show_steps')
                but = types.InlineKeyboardButton(text=string, url=link)
                key.add(but)

            link = await get_start_link('show_all')
            but = types.InlineKeyboardButton(text='ℹ️ Статистика по каналам', url=link),
            key.add(*but)

            await bot.edit_message_text(chat_id=msg.chat.id,
                                        message_id=msg.message_id,
                                        text='План:',
                                        reply_markup=key)

            id_data = {'last_message_id': msg.message_id, 'key': dict(key)}
            mongo_id.update_one({'channel_id': msg.chat.id}, {'$set': id_data})
            mongo_callback_data.insert_one(data)

        except Exception as e:
            print(e)
            await bot.send_message(msg.chat.id, messages.wrong_format)


@dp.callback_query_handler(lambda c: True)
async def inline(call): # !!!!!!11
    """ Реализована логика нажатия на кнопки с делами и подсчета сделанных дел"""

    print("tapped button  \n", call, "\n")

    user_id = call.from_user.id
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    channel_username = call.message.sender_chat.username
    if channel_username == None:
        channel_username = call.message.sender_chat.title

    user_username = call.from_user.first_name

    find_last_time = mongo_last_time.find_one({"user_id": user_id})
    find_callback = mongo_callback_data.find_one({"message_id": message_id, 'channel_username': channel_username})
    find_statistics = mongo_statistics.find_one({"channel_username": channel_username})

    if find_callback is None:
        await call.answer(text=messages.past_day, show_alert=True)
        return

    flag = 0
    # проверяем является ли юзер, тыкающий на кнопку владельцем канала
    for x in mongo_id.find({"user_id": user_id}):  # у пользователя, нажавшего на кнопку есть канал, подкл к боту
        if x['channel_id'] == chat_id:  # пользователь нажал кнопку в своем канале с channel_id = chat_id
            flag = 1
            break

    if call.data[:5] == 'fruit':
        if flag:
            point_index = int(call.data.split('_')[1])

            keyb = call['message']['reply_markup']
            text_button = keyb['inline_keyboard'][point_index - 1][0]['text']

            if text_button[-1] == ')':
                await call.answer(text='Текущий таймер еще работает', show_alert=True)
            else:
                text_button += ' (' + str(fruit_timer_minutes) + ' мин)'
                keyb['inline_keyboard'][point_index - 1][0]['text'] = text_button

                time_now = int(datetime.now(timezone.utc).timestamp())
                mongo_id.update_one({'channel_id': chat_id}, {"$set": {"fruit_timer": time_now}})

                await bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id, reply_markup=keyb)

                id_data = {'key': dict(keyb)}
                mongo_id.update_one({'channel_id': chat_id}, {'$set': id_data})
        else:
            await call.answer(text='Эта кнопка только для администратора', show_alert=True)
        return

    data = int(call.data)
    point_index = abs(data)

    keyb = call['message']['reply_markup']
    text_button = keyb['inline_keyboard'][point_index - 1][0]['text']

    prefix = text_button[:2]
    new_data = str(data)

    # логика возможности нажать на кнопку
    if flag == 1:
        new_data = str(-data)
        if data > 0:
            prefix = OK + ' '
        else:
            prefix = NOK + ' '
    else:
        time_now = int(time.time())

        # юзера нет в БД last_time - добавляем юзера в БД
        if find_last_time is None:
            data_lt = {'user_id': user_id, 'point_ind': [point_index], 'time_now': [time_now]}
            mongo_last_time.insert_one(data_lt)

        # юзер есть в БД и он нажал на кнопку point_ind, которой нет в БД - добавляем кнопку в БД к этому юзеру
        elif point_index not in find_last_time['point_ind']:
            data_pi = find_last_time['point_ind']
            data_tn = find_last_time['time_now']
            data_pi.append(point_index)
            data_tn.append(time_now)
            mongo_last_time.update_one({'user_id': user_id}, {'$set': {"point_ind": data_pi, "time_now": data_tn}})

        # юзер есть в БД и он нажал на кнопку point_ind, которая есть в БД - проверяем 30 сек. с последнего нажатия
        # или обновляем время time_now в БД
        else:
            time_delta_admin = 30
            ind = find_last_time['point_ind'].index(point_index)
            time_delta_user = time_now - find_last_time['time_now'][ind]  # last_time[user_id][point_index]
            if time_delta_user < time_delta_admin:
                await call.answer(
                    text=messages.wait + str(time_delta_admin - time_delta_user) + ' сек.',
                    show_alert=True)
                return
            else:
                data_tn = find_last_time['time_now']
                data_tn[ind] = time_now
                mongo_last_time.update_one({"user_id": user_id}, {"$set": {"time_now": data_tn}})

    # логика подсчета дел, сделанных пользователями
    action_personal = find_statistics['person']
    action_general = find_statistics['general']

    data_cb = find_callback['users']  # массив массивов пользователей по кнопкам
    if len(data_cb) < point_index:
        print('index out')
        return

    data_cu = data_cb[point_index - 1]  # массив пользователей, нажавших на кнопку point_ind
    if user_id in data_cu:
        data_cu.remove(user_id)
        action_general -= 1
        if flag == 1:
            action_personal -= 1
    else:
        data_cu.append(user_id)
        action_general += 1
        if flag == 1:
            action_personal += 1

    data_cb[point_index - 1] = data_cu
    mongo_callback_data.update_one({'message_id': message_id, 'channel_username': channel_username},
                                     {"$set": {'users': data_cb}})
    mongo_statistics.update_one({"channel_username": channel_username}, {"$set": {"person": action_personal,
                                                                                  "general": action_general}})

    count_pros = len(data_cu)
    if prefix[0] == OK:
        count_pros -= 1
    new_text = add_pros(text_button[2:], count_pros)

    keyb['inline_keyboard'][point_index - 1][0] = types.InlineKeyboardButton(
        text=prefix + new_text, callback_data=new_data)

    if call.from_user.username is not None:
        user_username = '@' + call.from_user.username

    await bot.send_message(my_id, user_username + ' in @' + channel_username + '\n' + text_button)

    await bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id, reply_markup=keyb)

    id_data = {'key': dict(keyb)}
    mongo_id.update_one({'channel_id': chat_id}, {'$set': id_data})


@dp.message_handler()
async def forwarded_msg(msg): # !!!!!!!!
    """Вызывается при пересылке сообщения из ТГ канала в бота для его настройки
       Добавляет в БД соответствующие документы в коллекции id и statistics"""

    print("new user\n", msg, "\n")
    if not validate_forwarded_msg_type(msg):
        await msg.answer(messages.forward)
        return

    user_id = msg.from_user.id
    channel_id = msg.forward_from_chat.id
    channel_username = msg.forward_from_chat.username

    if channel_username is None:
        channel_username = msg.forward_from_chat.title

    data_id = {"user_id": user_id, "channel_id": channel_id}
    data_stat = {'channel_username': channel_username, 'person': 0, 'general': 0}

    if mongo_id.find_one(data_id) is None:
        mongo_id.insert_one(data_id)

    if mongo_statistics.find_one({'channel_username': channel_username}) is None:
        mongo_statistics.insert_one(data_stat)

    await msg.answer(messages.success)


async def get_step_count(url_token):
    dt = datetime.now(timezone.utc)
    dt_str = dt.strftime("%-m-%-d-%Y")
    print(dt_str)
    url = url_token + f'/aggregatesDatasets?dataTypeName=steps_count&customTimePeriod=["{dt_str} 00:00:00 GMT","{dt_str} 23:59:00 GMT"]'
    params = {}
    r = requests.get(url = url, params = params)
    result = r.json()
    print(result)

    return result['steps_count'][0]['value']


async def background_steps():
    try:
        while True:
            print('new iter background_steps')

            for channel in mongo_id.find({'nocodeapi': {'$exists': True}}):
                chat_id = channel['channel_id']
                message_id = channel['last_message_id']
                url_token = channel['nocodeapi']
                step_count = await get_step_count(url_token)

                if not 'key' in channel:
                    continue

                keyb = channel['key']
                amount = len(keyb['inline_keyboard'])

                step_count = await get_step_count(channel['nocodeapi'])
                step_limit = 10000
                string = f'{NOK} {amount-1}. Пройдено {step_count} шагов из {step_limit}'
                link = await get_start_link('show_steps')
                but = {'text':string, 'url':link}
                # print(but)
                # print(keyb['inline_keyboard'][amount - 2][0])
                if but != keyb['inline_keyboard'][amount - 2][0]:
                    keyb['inline_keyboard'][amount - 2][0] = but

                    await bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id, reply_markup=keyb)

                    id_data = {'key': dict(keyb)}
                    mongo_id.update_one({'channel_id': chat_id}, {'$set': id_data})

            await asyncio.sleep(10*60)
    except Exception as e:
        print('background')
        print(e)


async def background_fruit_timer():
    try:
        while True:
            print('new iter background_fruit_timer')
            for channel in mongo_id.find({'fruit_timer': {'$exists': True}}):
                chat_id = channel['channel_id']
                message_id = channel['last_message_id']

                if not 'key' in channel:
                    continue

                keyb = channel['key']
                amount = len(keyb['inline_keyboard'])
                text_button = keyb['inline_keyboard'][amount - 2][0]['text']

                dt_start = channel['fruit_timer']
                dt_now = int(datetime.now(timezone.utc).timestamp())

                string = ''
                string_list = text_button.split()

                if dt_now - dt_start < fruit_timer_minutes*60:
                    string_list = string_list[:3]
                    string_list[2] = fruits[string_list[1]]
                    string = ' '.join(string_list) + ' (' + str(fruit_timer_minutes - (dt_now - dt_start) // 60) + ' мин)'

                else:
                    print(string_list)
                    string_list[0] = str(int(string_list[0]) + 1)
                    string_list[2] = fruits[string_list[1]]
                    string_list = string_list[:3]
                    string = ' '.join(string_list)

                    await bot.send_message(channel['user_id'], 'Таймер истёк')

                    mongo_id.update_one({'channel_id': chat_id}, {'$set': {'fruit_number': channel['fruit_number'] + 1}})
                    mongo_id.update_one({'channel_id': chat_id}, {'$unset': {'fruit_timer': 1}})

                but = {'text': string, 'callback_data': f'fruit_{amount-1}'}

                print(but)
                print(keyb['inline_keyboard'][amount - 2][0])
                if but != keyb['inline_keyboard'][amount - 2][0]:
                    keyb['inline_keyboard'][amount - 2][0] = but

                    await bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id, reply_markup=keyb)

                    id_data = {'key': dict(keyb)}
                    mongo_id.update_one({'channel_id': chat_id}, {'$set': id_data})

            await asyncio.sleep(60)
    except Exception as e:
        print('fruit_timer')
        print(e)


async def on_bot_start_up(dp):
    await on_startup(dp)
    asyncio.ensure_future(background_fruit_timer())
    # asyncio.ensure_future(background_steps())


def run_bot_with_webhook():
    print('run bot with webhook')
    start_webhook(
            dispatcher=dp,
            webhook_path=WEBHOOK_PATH,
            on_startup=on_bot_start_up,
            on_shutdown=on_shutdown,
            skip_updates=True,
            host=WEBAPP_HOST,
            port=WEBAPP_PORT,
        )


def run_bot_with_polling(on=False):
    """Вызывайте с оn=True, если запускаете бота для локального тестирования в первый раз"""

    print('run bot with polling')
    if on:
        on_shutdown(dp)
    executor.start_polling(dp, skip_updates=True)


def main():
    #run_bot_with_polling()
    run_bot_with_webhook()


if __name__ == '__main__':
    # pr1 = Process(target=main)
    # pr2 = Process(target=run_bot)

    # pr1.start()
    # pr2.start()
    asyncio.run(main())
