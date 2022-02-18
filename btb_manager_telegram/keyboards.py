import i18n
import telegram

menu = telegram.ReplyKeyboardMarkup(
    [
        [i18n.t("keyboard.current_value"), i18n.t("keyboard.bot_stats")],
        [i18n.t("keyboard.progress"), i18n.t("keyboard.next_coin")],
        [i18n.t("keyboard.trade_history"), i18n.t("keyboard.graph")],
        [i18n.t("keyboard.configurations")],
        [i18n.t("keyboard.check_status"), i18n.t("keyboard.maintenance")],
    ],
    resize_keyboard=True,
)

config = telegram.ReplyKeyboardMarkup(
    [
        [i18n.t("keyboard.start"), i18n.t("keyboard.stop")],
        [i18n.t("keyboard.read_logs"), i18n.t("keyboard.delete_db")],
        [i18n.t("keyboard.edit_cfg"), i18n.t("keyboard.edit_coin_list")],
        [i18n.t("keyboard.export_db"), i18n.t("keyboard.back")],
    ],
    resize_keyboard=True,
)

maintenance = telegram.ReplyKeyboardMarkup(
    [
        [i18n.t("keyboard.update_tgb")],
        [i18n.t("keyboard.execute_script")],
        [i18n.t("keyboard.update_btb")],
        [i18n.t("keyboard.back")],
    ],
    resize_keyboard=True,
)
