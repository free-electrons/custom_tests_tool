import logging

class CTTFormatter(logging.Formatter):
    def __green(self, arg):
        return "\033[32m%s\033[39m" % arg

    def __orange(self, arg):
        return "\033[33m%s\033[39m" % arg

    def __red(self, arg):
        return "\033[31m%s\033[39m" % arg

    def format(self, record):
        msg = super(CTTFormatter, self).format(record)
        if record.levelno == logging.WARNING:
            return self.__orange(msg)
        elif (record.levelno == logging.ERROR or
              record.levelno == logging.CRITICAL):
            return self.__red(msg)
        else:
            return msg
