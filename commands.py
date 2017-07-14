from telegram import ParseMode, InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardButton, InlineKeyboardMarkup
from uuid import uuid4
from functools import partial
'''
STATE MAP

_ : Start
0 : Select State
1 : Coins
5 : Notifications
'''


def get_help(_, update):
    message = 'Use the /start command to list the top coins, pick one to see more details.\n' \
              'You can also use the bot for quick inline queries.\n\n' \
              'Other commands:\n' \
              '/setnotifs ARG,ARG,ARG - sends hourly notifications for selected symbols\n' \
              '/clearnotifs - clears hourly notifications'
    update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)


def inline_query(api, _, update):
    query = update.inline_query.query
    symbols = api.list()
    filtered_list = stupid_filter(query, symbols)
    results = [InlineQueryResultArticle(id=uuid4(),
                                        title=('{0} - {1}'.format(*symbol)),
                                        input_message_content=InputTextMessageContent(
                                            format_coin(api.get_coin(symbol[0])),
                                            parse_mode=ParseMode.MARKDOWN))
               for symbol in filtered_list]
    update.inline_query.answer(results)

def start(_, update):
    message = 'Hi, I\'m the Crypto Coin Ticker Bot!.\n\
I can help you follow the current crypto coin prices.'
    keyboard = [[InlineKeyboardButton('Top 50', callback_data='1'), InlineKeyboardButton('Notifications', callback_data='5')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    return 0


def start_branch_handler(api, bot, update, chat_data):
    query = update.callback_query
    next_state = int(query.data)
    symbols = api.list()
    if next_state == 1:
        columns = 3
        text = 'Top 50 Coins:'
        buttons = [InlineKeyboardButton('{}. {}'.format(index + 1, symbol[1]), callback_data=symbol[0]) for
                    index, symbol in enumerate(symbols)]
        keyboard = [buttons[i:i + columns] for i in range(0, len(buttons), columns)]

    elif next_state == 5:
        if 'coins' not in chat_data:
            chat_data['coins'] = ['None']
        watched_coins = ', '.join(chat_data['coins'])
        text = 'Notifications: {}\n' \
               'Watched Coins: {}'.format('job' in chat_data, watched_coins)
        #WIP
        keyboard = []
        next_state = -1

    reply_markup = InlineKeyboardMarkup(keyboard)
    bot.edit_message_text(text=text,
                          chat_id=query.message.chat_id,
                          message_id=query.message.message_id,
                          reply_markup=reply_markup)
    return next_state


def coin_handler(api, bot, update):
    query = update.callback_query
    message = format_coin(api.get_coin(query.data))
    bot.edit_message_text(text=message,
                          chat_id=query.message.chat_id,
                          message_id=query.message.message_id,
                          parse_mode=ParseMode.MARKDOWN)
    return -1


def format_coin(coin):
    return '%(name)s\n' \
           'BTC*%(price_btc)s* USD*%(price_usd)s* EUR*%(price_eur)s*\n' \
           'Hour *%(percent_change_1h)s%%* | Day *%(percent_change_24h)s%%* | Week *%(percent_change_7d)s%%*' % coin


def stupid_filter(query, input_list):
    query_set = set(query.lower())
    result = filter(lambda x: query_set <= set((x[0].join(x[1])).lower()), input_list)
    return result

def set_notifications(api, _, update, args, job_queue, chat_data):
    if len(args) == 0:
        message = 'This commands takes one argument.'
    else:
        coins = set(coin.upper() for coin in args[0].split(','))
        if 'job' in chat_data:
            chat_data['job'].schedule_removal()
            del chat_data['job']

        if coins<=(set([i[0] for i in api.list()])):
            send_notification = partial(notification, *(api, coins))
            send_notification.__name__ = "send_notification"
            job = job_queue.run_repeating(send_notification, 3600, context=update.message.chat_id)
            chat_data['job'] = job
            chat_data['coins'] = coins
            message = 'Notifications set!'
        else:
            message = 'Something is wrong with the input, check the symbols.'

    update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)


def clear_notifications(_, update, chat_data):
    if 'job' in chat_data:
        chat_data['job'].schedule_removal()
        del chat_data['job']
        del chat_data['coins']
        message = 'Notifications cleared'
    else:
        message = 'No notifications scheduled'

    update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)


def notification(api, coins, bot, job):
    formatted_coins = [format_coin(api.get_coin(coin)) for coin in coins]
    message = '\n\n'.join(formatted_coins)
    bot.send_message(job.context, text=message, parse_mode=ParseMode.MARKDOWN)
