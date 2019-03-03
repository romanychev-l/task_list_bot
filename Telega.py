import config
import telebot
from telebot import types

bot = telebot.TeleBot(config.token)
T = #id чата или канала

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

@bot.message_handler(content_types=["text"])
def inline(message):
	a = put_string(message.text)
	for i in range(0, len(a)):
		key = types.InlineKeyboardMarkup()
		but = types.InlineKeyboardButton(text="❌", callback_data="not")
		key.add(but)
		bot.send_message(T, a[i], reply_markup=key)

@bot.callback_query_handler(func=lambda c:True)
def inline(c):
	if c.data == "not":
		but = types.InlineKeyboardButton(text="✅", callback_data="yes")
	else:
		but = types.InlineKeyboardButton(text="❌", callback_data="not")
	key = types.InlineKeyboardMarkup()
	key.add(but)
	bot.edit_message_reply_markup(chat_id=T, message_id=c.message.message_id, reply_markup = key)

if __name__ == '__main__':
     bot.polling(none_stop=True)
