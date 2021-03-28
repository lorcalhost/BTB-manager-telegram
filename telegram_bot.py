# -*- coding: utf-8 -*-
import logging
import yaml
import psutil
import subprocess
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler,
    CallbackContext
)

def get_token_from_yaml():
    telegram_url = None
    with open(YAML_FILE_PATH) as f:
        parsed_urls = yaml.load(f, Loader=yaml.FullLoader)['urls']
        for url in parsed_urls:
            if url.startswith('tgram'):
                telegram_url = url.split('//')[1]
    if not telegram_url:
        print('ERROR: No telegram configuration was found in your yaml file.\nAborting.')
        exit(-1)
    try:
        tok = telegram_url.split('/')[0]
        uid = telegram_url.split('/')[1]
    except:
        print('ERROR: No user_id has been set in the yaml configuration, anyone would be able to control your bot.\nAborting.')
        exit(-1)
    return tok, uid


def start(update: Update, _: CallbackContext) -> int:
    logger.info('Start.')

    keyboard = [['Begin']]
    message = f'Hi *{update.message.from_user.first_name}*\!\nWelcome to _Binace Trade Bot manager_\.\n\nThis telegram bot was developed by @lorcalhost\nFind out more about the project [here](http://www.example.com/)\.'
    reply_markup=ReplyKeyboardMarkup(
        keyboard,
        one_time_keyboard=True,
        resize_keyboard=True
    )
    update.message.reply_text(
        message,
        reply_markup=reply_markup,
        parse_mode='MarkdownV2'
    )
    return MENU

def menu(update: Update, _: CallbackContext) -> int:
    logger.info(f'Operation selector. ({update.message.text})')

    keyboard = [
        ['⚠ Check bot status', '👛 Edit coins list'],
        ['▶ Start trade bot', '⚙ Edit user.cfg'],
        ['⏹ Stop trade bot', '❌ Delete database']
    ]
    reply_markup = ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True
    )

    if update.message.text == 'Begin':
        message = 'Please select one of the options in your keyboard.'
        update.message.reply_text(
            message, 
            reply_markup=reply_markup
        )
    
    elif update.message.text == '⚠ Check bot status':
        update.message.reply_text(
            btn_check_status(),
            reply_markup=reply_markup
        )

    elif update.message.text == '👛 Edit coins list':
        update.message.reply_text(
            btn_edit_coins(),
            reply_markup=reply_markup,
            parse_mode='MarkdownV2'
        )

    elif update.message.text == '▶ Start trade bot':
        update.message.reply_text(
            btn_start_bot(),
            reply_markup=reply_markup
        )

    elif update.message.text == '⏹ Stop trade bot':
        update.message.reply_text(
            btn_stop_bot(),
            reply_markup=reply_markup
        )
    return MENU

def find_process():
    for p in psutil.process_iter():
        if 'binance_trade_bot' in p.name() or 'binance_trade_bot' in ' '.join(p.cmdline()):
            return True
    return False

def find_and_kill_process():
    try:
        for p in psutil.process_iter():
            if 'binance_trade_bot' in p.name() or 'binance_trade_bot' in ' '.join(p.cmdline()):
                p.terminate()
                p.wait()
    except Exception as e:
        logger.warning(e)

def btn_check_status():
    logger.info('Check status.')

    message = '❌ Binance Trade Bot is not running.'
    if find_process():
        message = '✔ Binance Trade Bot is running.'
    return  message

def btn_edit_coins():
    logger.info('Edit coins.')

    message = '⚠ Please stop Binance Trade Bot before editing the coin list\.'
    if not find_process():
        with open('./supported_coin_list') as f:
            message = 'Current coin list is:\n```\n' + f.read() + '\n```'
    return message

def btn_start_bot():
    logger.info('Start bot.')

    message = '⚠ Binance Trade Bot is already running.'
    if not find_process():
        subprocess.call('$(which python) binance_trade_bot.py &', shell=True)
        if not find_process():
            message = '❌ Unable to start Binance Trade Bot.'
        else:
            message = '✔ Binance Trade Bot successfully started.'
    return message

def btn_stop_bot():
    logger.info('Stop bot.')

    message = '⚠ Binance Trade Bot is not running.'
    if find_process():
        find_and_kill_process()
        if not find_process():
            message = '✔ Successfully stopped the bot'
        else:
            message = '❌ Unable to stop Binance Trade Bot.\n\nIf you are running the telegram bot on Windows make sure to run with administrator privileges.'
    return message

def cancel(update: Update, _: CallbackContext) -> int:
    logger.info('Conversation canceled.')
    update.message.reply_text(
        'Bye! I hope we can talk again some day.', reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END

YAML_FILE_PATH = './config/apprise.yml'

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

MENU = range(1)

TOKEN, USER_ID = get_token_from_yaml()

def main() -> None:
    updater = Updater(TOKEN)
    dispatcher = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start, Filters.user(user_id=eval(USER_ID)))],
        states={
            MENU: [MessageHandler(Filters.regex('^(Begin|⚠ Check bot status|👛 Edit coins list|▶ Start trade bot|⏹ Stop trade bot|❌ Delete database|⚙ Edit user.cfg)$'), menu)]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        per_user=True
    )

    dispatcher.add_handler(conv_handler)

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()