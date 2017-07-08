import logging
from argparse import ArgumentParser
from functools import partial

from telegram import ParseMode
from telegram.ext import Updater, CommandHandler

from coinmarketcap import CoinMarketCapAPI


def format_coin(coin):
    return '%(name)s\n\
BTC*%(price_btc)s* USD*%(price_usd)s* EUR*%(price_eur)s*\n\
Hour *%(percent_change_1h)s%%* | Day *%(percent_change_24h)s%%* | Week *%(percent_change_7d)s%%*' % coin


def start(bot, update):
    update.message.reply_text(
        'Hi, I\'m the Crypto Coin Ticker Bot!.\n\
I can help you follow the current crypto coin prices.\n\
/help for more info')


def get_help(bot, update):
    update.message.reply_text('Currently available commands:\n \
    /list - lists currently tracked coin symbols\n \
    /coin ARG - gets the specified coin\'s ticker\n \
    /setnotifs ARG,ARG,ARG - sends hourly notifications for selected symbols\n \
    /clearnotifs - clears hourly notifications')


def list_coins(api, bot, update):
    message = 'Tracked coins:\n' + '\n'.join('{0}'.format(symbol) for symbol in api.list())
    update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)


def get_coin(api, bot, update, args):
    if len(args) == 0:
        message = 'This commands takes one argument.'
    elif args[0].upper() not in api.list():
        message = 'What\'s a {}?'.format(args[0])
    else:
        message = format_coin(api.get_coin(args[0]))

    update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)


def set_notifications(api, bot, update, args, job_queue, chat_data):
    if len(args) == 0:
        update.message.reply_text('This commands takes one argument.')
        return

    coins = set(coin.upper() for coin in args[0].split(','))
    if 'job' in chat_data:
        chat_data['job'].schedule_removal()
        del chat_data['job']

    if coins.issubset(set(api.list())):
        send_notification = partial(notification, *(api, coins))
        send_notification.__name__ = "send_notification"
        job = job_queue.run_repeating(send_notification, 3600, context=update.message.chat_id)
        chat_data['job'] = job
        update.message.reply_text('Notifications set!')
    else:
        update.message.reply_text('Something wrong with the input, check the symbols.', parse_mode=ParseMode.MARKDOWN)


def clear_notifications(bot, update, chat_data):
    if 'job' in chat_data:
        chat_data['job'].schedule_removal()
        del chat_data['job']
        update.message.reply_text('Notifications cleared')
    else:
        update.message.reply_text('No notifications scheduled')


def notification(api, coins, bot, job):
    formatted_coins = [format_coin(api.get_coin(coin)) for coin in coins]
    message = '\n\n'.join(formatted_coins)
    bot.send_message(job.context, text=message)


def main(token):
    updater = Updater(token)
    coin_api = CoinMarketCapAPI()

    updater.dispatcher.add_handler(CommandHandler('start', start))
    updater.dispatcher.add_handler(CommandHandler('help', get_help))

    send_coin_list = partial(list_coins, coin_api)
    updater.dispatcher.add_handler(CommandHandler('list', send_coin_list))

    send_coin = partial(get_coin, coin_api)
    updater.dispatcher.add_handler(CommandHandler('coin', send_coin, pass_args=True))

    handle_set_notifs = partial(set_notifications, coin_api)
    updater.dispatcher.add_handler(
        CommandHandler("setnotifs", handle_set_notifs, pass_args=True, pass_chat_data=True, pass_job_queue=True))
    updater.dispatcher.add_handler(CommandHandler("clearnotifs",
                                                  clear_notifications,
                                                  pass_args=False,
                                                  pass_chat_data=True))

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    parser = ArgumentParser()
    parser.add_argument("token")
    args = parser.parse_args()
    main(args.token)
