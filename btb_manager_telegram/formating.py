import telegram


def format_float(num):
    return f"{num:0.8f}".rstrip("0").rstrip(".")


def escape_tg(message, exclude_parenthesis=False):
    escape_char = [".", "-", "?", "!", ">", "{", "}", "=", "+", "|"]
    if exclude_parenthesis:
        escape_char += ["(", ")", "[", "]"]
    escaped_message = ""
    is_escaped = False
    for cur_char in message:
        if cur_char in escape_char and not is_escaped:
            escaped_message += "\\"
        escaped_message += cur_char
        is_escaped = cur_char == "\\" and not is_escaped
    return escaped_message


def reply_text_escape(reply_text_fun):
    def reply_text_escape_fun(message, **kwargs):
        return reply_text_fun(escape_tg(message), **kwargs)

    return reply_text_escape_fun


def telegram_text_truncator(m_list, padding_chars_head="", padding_chars_tail=""):
    message = [padding_chars_head]
    index = 0
    for mes in m_list:
        if (
            len(message[index]) + len(mes) + len(padding_chars_tail)
            <= telegram.constants.MAX_MESSAGE_LENGTH
        ):
            message[index] += mes
        else:
            message[index] += padding_chars_tail
            message.append(padding_chars_head + mes)
            index += 1
    message[index] += padding_chars_tail
    return message
