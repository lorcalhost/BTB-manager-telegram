# -*- coding: utf-8 -*-
import logging
import yaml
import psutil
import subprocess
import os
import argparse
from shutil import copyfile
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler,
    CallbackContext
)

MENU, EDIT_COIN_LIST, EDIT_USER_CONFIG = range(3)


class BTBManagerTelegram:
    def __init__(self, root_path='./', from_yaml=True, token=None, user_id=None):
        self.root_path = root_path
        logging.basicConfig(
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
        )
        self.logger = logging.getLogger(__name__)

        if from_yaml:
            token, user_id = self.__get_token_from_yaml()


        updater = Updater(token)
        dispatcher = updater.dispatcher

        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', self.__start, Filters.user(user_id=eval(user_id)))],
            states={
                MENU: [MessageHandler(Filters.regex('^(Begin|⚠ Check bot status|👛 Edit coin list|▶ Start trade bot|⏹ Stop trade bot|❌ Delete database|⚙ Edit user.cfg|📜 Read last log lines|Go back)$'), self.__menu)],
                EDIT_COIN_LIST: [MessageHandler(Filters.regex('(.*?)'), self.__edit_coin)],
                EDIT_USER_CONFIG: [MessageHandler(Filters.regex('(.*?)'), self.__edit_user_config)]
            },
            fallbacks=[CommandHandler('cancel', self.__cancel)],
            per_user=True
        )

        dispatcher.add_handler(conv_handler)
        updater.start_polling()
        updater.idle()

    def __get_token_from_yaml(self):
        telegram_url = None
        yaml_file_path = f'{self.root_path}config/apprise.yml'
        with open(yaml_file_path) as f:
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


    def __start(self, update: Update, _: CallbackContext) -> int:
        self.logger.info('Started conversation.')

        keyboard = [['Begin']]
        message = f'Hi *{update.message.from_user.first_name}*\!\nWelcome to _Binace Trade Bot Manager Telegram_\.\n\nThis telegram bot was developed by @lorcalhost\.\nFind out more about the project [here](https://github.com/lorcalhost/BTB-manager-telegram)\.'
        reply_markup=ReplyKeyboardMarkup(
            keyboard,
            one_time_keyboard=True,
            resize_keyboard=True
        )
        update.message.reply_text(
            message,
            reply_markup=reply_markup,
            parse_mode='MarkdownV2',
            disable_web_page_preview=True
        )
        return MENU

    def __menu(self, update: Update, _: CallbackContext) -> int:
        self.logger.info(f'Menu selector. ({update.message.text})')

        keyboard = [
            ['⚠ Check bot status', '👛 Edit coin list'],
            ['▶ Start trade bot', '⚙ Edit user.cfg'],
            ['⏹ Stop trade bot', '❌ Delete database'],
            ['📜 Read last log lines', '📈 Calculate gains']
        ]
        reply_markup = ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True
        )

        if update.message.text in ['Begin', 'Go back']:
            message = 'Please select one of the options.'
            update.message.reply_text(
                message,
                reply_markup=reply_markup
            )

        elif update.message.text == '⚠ Check bot status':
            update.message.reply_text(
                self.__btn_check_status(),
                reply_markup=reply_markup
            )

        elif update.message.text == '👛 Edit coin list':
            re = self.__btn_edit_coin()
            if re[1]:
                update.message.reply_text(
                    re[0],
                    reply_markup=ReplyKeyboardRemove(),
                    parse_mode='MarkdownV2'
                )
                return EDIT_COIN_LIST
            else:
                update.message.reply_text(
                    re[0],
                    reply_markup=reply_markup,
                    parse_mode='MarkdownV2'
                )

        elif update.message.text == '▶ Start trade bot':
            update.message.reply_text(
                self.__btn_start_bot(),
                reply_markup=reply_markup,
                parse_mode='MarkdownV2'
            )

        elif update.message.text == '⏹ Stop trade bot':
            update.message.reply_text(
                self.__btn_stop_bot(),
                reply_markup=reply_markup
            )

        elif update.message.text == '❌ Delete database':
            update.message.reply_text(
                self.__btn_delete_db(),
                reply_markup=reply_markup,
                parse_mode='MarkdownV2'
            )

        elif update.message.text == '⚙ Edit user.cfg':
            re = self.__btn_edit_user_cfg()
            if re[1]:
                update.message.reply_text(
                    re[0],
                    reply_markup=ReplyKeyboardRemove(),
                    parse_mode='MarkdownV2'
                )
                return EDIT_USER_CONFIG
            else:
                update.message.reply_text(
                    re[0],
                    reply_markup=reply_markup,
                    parse_mode='MarkdownV2'
                )

        elif update.message.text == '📜 Read last log lines':
            update.message.reply_text(
                self.__btn_read_log(),
                reply_markup=reply_markup,
                parse_mode='MarkdownV2'
            )

        return MENU

    def __edit_coin(self, update: Update, _: CallbackContext) -> int:
        self.logger.info(f'Editing coin list. ({update.message.text})')

        message = f'✔ Successfully edited coin list file to:\n\n```\n{update.message.text}\n```'.replace('.', '\.')
        coin_file_path = f'{self.root_path}supported_coin_list'
        try:
            copyfile(coin_file_path, f'{coin_file_path}.backup')
            with open(coin_file_path, 'w') as f:
                f.write(update.message.text + '\n')
        except:
            message = '❌ Unable to edit coin list file\.'

        keyboard = [['Go back']]
        reply_markup = ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True
        )
        update.message.reply_text(
            message,
            reply_markup=reply_markup,
            parse_mode='MarkdownV2'
        )

        return MENU

    def __edit_user_config(self, update: Update, _: CallbackContext) -> int:
        self.logger.info(f'Editing user configuration. ({update.message.text})')

        message = f'✔ Successfully edited user configuration file to:\n\n```\n{update.message.text}\n```'.replace('.', '\.')
        user_cfg_file_path = f'{self.root_path}user.cfg'
        try:
            copyfile(user_cfg_file_path, f'{user_cfg_file_path}.backup')
            with open(user_cfg_file_path, 'w') as f:
                f.write(update.message.text + '\n\n\n')
        except:
            message = '❌ Unable to edit user configuration file\.'

        keyboard = [['Go back']]
        reply_markup = ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True
        )
        update.message.reply_text(
            message,
            reply_markup=reply_markup,
            parse_mode='MarkdownV2'
        )

        return MENU

    @staticmethod
    def __find_process():
        for p in psutil.process_iter():
            if 'binance_trade_bot' in p.name() or 'binance_trade_bot' in ' '.join(p.cmdline()):
                return True
        return False

    def __find_and_kill_process(self):
        try:
            for p in psutil.process_iter():
                if 'binance_trade_bot' in p.name() or 'binance_trade_bot' in ' '.join(p.cmdline()):
                    p.terminate()
                    p.wait()
        except Exception as e:
            self.logger.info(f'ERROR: {e}')

    def __btn_check_status(self):
        self.logger.info('Check status button pressed.')

        message = '⚠ Binance Trade Bot is not running.'
        if self.__find_process():
            message = '✔ Binance Trade Bot is running.'
        return  message

    def __btn_edit_coin(self):
        self.logger.info('Edit coin list button pressed.')

        message = '⚠ Please stop Binance Trade Bot before editing the coin list\.'
        edit = False
        coin_file_path = f'{self.root_path}supported_coin_list'
        if not self.__find_process():
            if os.path.exists(coin_file_path):
                with open(coin_file_path) as f:
                    message = f'Current coin list is:\n\n```\n{f.read()}\n```\n\n_*Please reply with a message containing the updated coin list*_.'.replace('.', '\.')
                    edit = True
            else:
                message = f'❌ Unable to find coin list file at `{coin_file_path}`.'.replace('.', '\.')
        return [message, edit]

    def __btn_start_bot(self):
        self.logger.info('Start bot button pressed.')

        message = '⚠ Binance Trade Bot is already running\.'
        if not self.__find_process():
            if os.path.exists(f'{self.root_path}binance_trade_bot/'):
                subprocess.call('$(which python3) -m binance_trade_bot &', shell=True)
                if not self.__find_process():
                    message = '❌ Unable to start Binance Trade Bot\.'
                else:
                    message = '✔ Binance Trade Bot successfully started\.'
            else:
                message = '❌ Unable to find _Binance Trade Bot_ installation in this directory\.\nMake sure the `BTBManagerTelegram.py` file is in the _Binance Trade Bot_ installation folder\.'
        return message

    def __btn_stop_bot(self):
        self.logger.info('Stop bot button pressed.')

        message = '⚠ Binance Trade Bot is not running.'
        if self.__find_process():
            self.__find_and_kill_process()
            if not self.__find_process():
                message = '✔ Successfully stopped the bot.'
            else:
                message = '❌ Unable to stop Binance Trade Bot.\n\nIf you are running the telegram bot on Windows make sure to run with administrator privileges.'
        return message

    def __btn_delete_db(self):
        self.logger.info('Delete database button pressed.')

        message = '⚠ Please stop Binance Trade Bot before deleting the database file\.'
        db_file_path = f'{self.root_path}data/crypto_trading.db'
        if not self.__find_process():
            if os.path.exists(db_file_path):
                try:
                    copyfile(db_file_path, f'{db_file_path}.backup')
                    os.remove(db_file_path)
                    message = '✔ Successfully deleted database file\.'
                except:
                    message = '❌ Unable to delete database file\.'
            else:
                message = f'⚠ Unable to find database file at `{db_file_path}`.'.replace('.', '\.')
        return message

    def __btn_edit_user_cfg(self):
        self.logger.info('Edit user configuration button pressed.')

        message = '⚠ Please stop Binance Trade Bot before editing user configuration file\.'
        edit = False
        user_cfg_file_path = f'{self.root_path}user.cfg'
        if not self.__find_process():
            if os.path.exists(user_cfg_file_path):
                with open(user_cfg_file_path) as f:
                    message = f'Current configuration file is:\n\n```\n{f.read()}\n```\n\n_*Please reply with a message containing the updated configuration*_.'.replace('.', '\.')
                    edit = True
            else:
                message = f'❌ Unable to find user configuration file at `{user_cfg_file_path}`.'.replace('.', '\.')
        return [message, edit]

    def __btn_read_log(self):
        self.logger.info('Read log button pressed.')

        log_file_path = f'{self.root_path}logs/crypto_trading.log'
        message = f'❌ Unable to find log file at `{log_file_path}`.'.replace('.', '\.')
        if os.path.exists(log_file_path):
            with open(log_file_path) as f:
                file_content = f.read().replace('.', '\.')[-4000:]
                message = f'Last *4000* characters in log file:\n\n```\n{file_content}\n```'
        return message

    def __cancel(self, update: Update, _: CallbackContext) -> int:
        self.logger.info('Conversation canceled.')

        update.message.reply_text(
            'Bye! I hope we can talk again some day.',
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--docker', help='If this arg is passed in, the script will run in a docker container')

    args = parser.parse_args()
    if args.docker:
        os.system("docker build -t py-container .")
        os.system("docker run --rm -it py-container")
        os.system("docker rmi -f py-container")

    BTBManagerTelegram()
