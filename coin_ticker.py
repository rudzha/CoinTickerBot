import logging
from argparse import ArgumentParser
from functools import partial
from uuid import uuid4

from telegram import ParseMode, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import Updater, CommandHandler, InlineQueryHandler

from coinmarketcap import CoinMarketCapAPI


def stupid_filter(query, input_list):
    query_set = set(query.lower())
    result = filter(lambda x: query_set <= set((x[0].join(x[1])).lower()), input_list)
    return result


def format_coin(coin):
    return '%(name)s\n\
BTC*%(price_btc)s* USD*%(price_usd)s* EUR*%(price_eur)s*\n\
Hour *%(percent_change_1h)s%%* | Day *%(percent_change_24h)s%%* | Week *%(percent_change_7d)s%%*' % coin


def start(_, update):
    message = 'Hi, I\'m the Crypto Coin Ticker Bot!.\n\
I can help you follow the current crypto coin prices.\n\
/help for more info\n\n\
What\'s new?\n\
I can now list top 50 coins, ordered by market cap\n\
I also support inline queries for easy sharing now'
    update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)


def get_help(_, update):
    message = 'Currently available commands:\n \
    /list - lists currently tracked coin symbols\n \
    /coin ARG - gets the specified coin\'s ticker\n \
    /setnotifs ARG,ARG,ARG - sends hourly notifications for selected symbols\n \
    /clearnotifs - clears hourly notifications'
    update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)


def list_coins(api, _, update):
    symbols_names = api.list()
    message = 'Top Tracked coins:\n' \
              + '\n'.join('{0}. {2} - {1}'.format(i + 1, *symbol) for i, symbol in enumerate(symbols_names))
    update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)


def get_coin(api, _, update, args):
    symbols = [i[0] for i in api.list()]
    if len(args) == 0:
        message = 'This commands takes one argument.'

    elif args[0].upper() not in symbols:
        message = 'What\'s a {}?'.format(args[0])
    else:
        message = format_coin(api.get_coin(args[0]))

    update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)


def set_notifications(api, _, update, args, job_queue, chat_data):
    if len(args) == 0:
        message = 'This commands takes one argument.'
    else:
        coins = set(coin.upper() for coin in args[0].split(','))
        if 'job' in chat_data:
            chat_data['job'].schedule_removal()
            del chat_data['job']

        if coins.issubset(set(api.list())):
            send_notification = partial(notification, *(api, coins))
            send_notification.__name__ = "send_notification"
            job = job_queue.run_repeating(send_notification, 3600, context=update.message.chat_id)
            chat_data['job'] = job
            message = 'Notifications set!'
        else:
            message = 'Something wrong with the input, check the symbols.'

    update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)


def clear_notifications(_, update, chat_data):
    if 'job' in chat_data:
        chat_data['job'].schedule_removal()
        del chat_data['job']
        message = 'Notifications cleared'
    else:
        message = 'No notifications scheduled'

    update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)


def notification(api, coins, bot, job):
    formatted_coins = [format_coin(api.get_coin(coin)) for coin in coins]
    message = '\n\n'.join(formatted_coins)
    bot.send_message(job.context, text=message, parse_mode=ParseMode.MARKDOWN)


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


def error(_, update, error_message):
    logger = logging.getLogger(__name__)
    logger.warning('Update "%s" caused error "%s"' % (update, error_message))


def main(token):
    updater = Updater(token)
    coin_api = CoinMarketCapAPI()
    coin_api.update()

    updater.dispatcher.add_handler(CommandHandler('start', start))
    updater.dispatcher.add_handler(CommandHandler('help', get_help))

    send_coin_list = partial(list_coins, coin_api)
    updater.dispatcher.add_handler(CommandHandler('list', send_coin_list))

    send_coin = partial(get_coin, coin_api)
    updater.dispatcher.add_handler(CommandHandler('coin', send_coin, pass_args=True))

    handle_set_notifications = partial(set_notifications, coin_api)
    updater.dispatcher.add_handler(
        CommandHandler("setnotifs", handle_set_notifications, pass_args=True, pass_chat_data=True, pass_job_queue=True))
    updater.dispatcher.add_handler(CommandHandler("clearnotifs",
                                                  clear_notifications,
                                                  pass_args=False,
                                                  pass_chat_data=True))

    coin_inline_query = partial(inline_query, coin_api)
    updater.dispatcher.add_handler(InlineQueryHandler(coin_inline_query))

    updater.dispatcher.add_error_handler(error)

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    parser = ArgumentParser()
    parser.add_argument("token")
    passed_args = parser.parse_args()
    main(passed_args.token)
