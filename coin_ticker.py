import logging
from argparse import ArgumentParser
from functools import partial

from telegram.ext import Updater, CommandHandler, InlineQueryHandler, CallbackQueryHandler, ConversationHandler

from coinmarketcap import CoinMarketCapAPI
from commands import get_help, set_notifications, clear_notifications, inline_query, start, coin_handler, start_branch_handler


def error(_, update, error_message):
    logger = logging.getLogger(__name__)
    logger.warning('Update "%s" caused error "%s"' % (update, error_message))


def main(token):
    updater = Updater(token)
    coin_api = CoinMarketCapAPI()
    coin_api.update()

    updater.dispatcher.add_handler(CommandHandler('help', get_help))

    # Notification commands
    handle_set_notifications = partial(set_notifications, coin_api)
    updater.dispatcher.add_handler(
        CommandHandler("setnotifs",
                       handle_set_notifications,
                       pass_args=True,
                       pass_chat_data=True,
                       pass_job_queue=True))

    updater.dispatcher.add_handler(CommandHandler("clearnotifs",
                                                  clear_notifications,
                                                  pass_args=False,
                                                  pass_chat_data=True))

    # Inline queries
    coin_inline_query = partial(inline_query, coin_api)
    updater.dispatcher.add_handler(InlineQueryHandler(coin_inline_query))

    # Inline keyboard
    state_start_branch_handler = partial(start_branch_handler, coin_api)
    state_coin_handler = partial(coin_handler, coin_api)

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            0: [CallbackQueryHandler(state_start_branch_handler, pass_chat_data=True)],
            1: [CallbackQueryHandler(state_coin_handler)]
        },
        fallbacks=[CommandHandler('start', start)],
        per_message=False
    )

    updater.dispatcher.add_handler(conv_handler)

    updater.dispatcher.add_error_handler(error)

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    parser = ArgumentParser()
    parser.add_argument("token")
    passed_args = parser.parse_args()
    main(passed_args.token)