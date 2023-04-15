import config
import messages
import time
import asyncio
from multiprocessing import Process
import pymongo

from aiogram import Bot, Dispatcher, executor, types
from aiogram.utils.executor import start_webhook

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

bot = Bot(token=config.token)
dp = Dispatcher(bot)

channel_id = -1001381328759
my_id = 248603604

OK = '✅'
NOK = '❌'


async def on_startup(dp):
    await bot.set_webhook(WEBHOOK_URL)


async def on_shutdown(dp):
    await bot.delete_webhook()


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


@dp.message_handler(commands=['show_all'])
async def show_all(msg):
    """Вызывается для просмотра статистики по кол-ву сделанных дел"""

    if mongo_id.find_one({'user_id': msg.from_user.id}) is None:
        await msg.answer(messages.no_channel)
        return

    all_person = 0
    all_general = 0
    text = ''
    for item in mongo_statistics.find():
        person = item['person']
        general = item['general']
        all_person += int(person)
        all_general += int(general)

        text = (text + '@' + item['channel_username'] + '\n' +
                'Пользователь ' + str(person) + '\n' +
                'Подписчики ' + str(general) + '\n\n')

    text = text + 'Все пользователи ' + str(all_person) + '\n' + 'Все подписчики ' + str(all_general)
    await msg.answer(text)


@dp.channel_post_handler(content_types=["text"])
async def write_plan(msg):
    """ Вызывается при добавлении Плана в ТГ канал
        Добавляет соответствующий документ в БД в коллекцию callback_data"""

    print('added new plan \n', msg, "\n")
    channel_username = msg.chat.username

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

            await bot.edit_message_text(chat_id=msg.chat.id,
                                        message_id=msg.message_id,
                                        text='План:',
                                        reply_markup=key)

            mongo_callback_data.insert_one(data)

        except Exception as e:
            print(e)
            await bot.send_message(msg.chat.id, messages.wrong_format)


@dp.callback_query_handler(lambda c: True)
async def inline(call):
    """ Реализована логика нажатия на кнопки с делами и подсчета сделанных дел"""

    print("tapped button  \n", call, "\n")

    user_id = call.from_user.id
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    channel_username = call.message.sender_chat.username
    user_username = call.from_user.first_name
    data = int(call.data)
    point_index = abs(data)

    find_last_time = mongo_last_time.find_one({"user_id": user_id})
    find_callback = mongo_callback_data.find_one({"message_id": message_id})
    find_statistics = mongo_statistics.find_one({"channel_username": channel_username})

    if find_callback is None:
        await call.answer(text=messages.past_day, show_alert=True)
        return

    # проверяем является ли юзер, тыкающий на кнопку владельцем канала
    flag = 0
    for x in mongo_id.find({"user_id": user_id}):  # у пользователя, нажавшего на кнопку есть канал, подкл к боту
        if x['channel_id'] == chat_id:  # пользователь нажал кнопку в своем канале с channel_id = chat_id
            flag = 1
            break

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
    mongo_callback_data.update_one({'message_id': message_id}, {"$set": {'users': data_cb}})
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

    if channel_username is None:
        channel_username = call.message.sender_chat.title

    await bot.send_message(my_id, user_username + ' in @' + channel_username + '\n' + text_button)

    await bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id, reply_markup=keyb)


@dp.message_handler()
async def forwarded_msg(msg):
    """Вызывается при пересылке сообщения из ТГ канала в бота для его настройки
       Добавляет в БД соответствующие документы в коллекции id и statistics"""

    print("new user\n", msg, "\n")
    if not validate_forwarded_msg_type(msg):
        await msg.answer(messages.forward)
        return

    user_id = msg.from_user.id
    channel_id = msg.forward_from_chat.id
    channel_username = msg.forward_from_chat.username

    data_id = {"user_id": user_id, "channel_id": channel_id}
    data_stat = {'channel_username': channel_username, 'person': 0, 'general': 0}

    if mongo_id.find_one(data_id) is None:
        mongo_id.insert_one(data_id)

    if mongo_statistics.find_one({'channel_username': channel_username}) is None:
        mongo_statistics.insert_one(data_stat)

    await msg.answer(messages.success)


async def run_bot_with_webhook():
    print('run bot with webhook')
    start_webhook(
            dispatcher=dp,
            webhook_path=WEBHOOK_PATH,
            on_startup=on_startup,
            on_shutdown=on_shutdown,
            skip_updates=True,
            host=WEBAPP_HOST,
            port=WEBAPP_PORT,
        )


async def run_bot_with_polling(on=False):
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
