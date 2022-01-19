class btbmtException(Exception):
    def __init__(self, message=None):
        self.message = message

    def __str__(self):
        if self.message is None:
            return ""
        else:
            return self.message


class BTBConfigNotFound(btbmtException):
    def __init__(self, path=None):
        message = "Binance Trade Bot config file cannot be found"
        if path is not None:
            message += " at " + str(path)
        super().__init__(message)


class NoChatID(btbmtException):
    def __init__(self):
        super().__init__(
            "No chat_id has been set in the yaml configuration, anyone would be able to control your bot."
        )


class NoRootPath(btbmtException):
    def __init__(self):
        super().__init__("No root_path has been specified.")


class NoTgConfig(btbmtException):
    def __init__(self):
        super().__init__(
            "No telegram configuration was found in your apprise.yml file."
        )


class TgConfigNotFound(btbmtException):
    def __init__(self, path=None):
        message = "Telegram config file (apprise.yml) cannot be found"
        if path is not None:
            message += " at " + str(path)
        super().__init__(message)
