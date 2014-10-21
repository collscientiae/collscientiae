from __future__ import absolute_import, unicode_literals
import logging
from time import time


def mytitle(s):
    """
    my str.title() where camel-case isn't killed!
    :param s:
    :return:
    """
    return s[0].title() + s[1:]


def get_creation_date():
    """
    This must be UTC and ISO format, e.g. 2014-10-19T19:19:04
    """
    from datetime import datetime as dt
    now = dt.utcnow()
    now = now.replace(microsecond=0)
    return dt.isoformat(now)

class CollScientiaLoggingFilter(logging.Filter):

    def __init__(self):
        super(CollScientiaLoggingFilter, self).__init__()
        self.start = time()

    def filter(self, record):
        record.elapsed = time() - self.start
        record.where = "%s:%s" % (record.filename[:-3], record.lineno)
        return True


class ColoredFormatter(logging.Formatter):

    BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(8)

    RESET_SEQ = "\033[0m"
    COLOR_SEQ = "\033[0;%dm"
    COLOR_SEQ_BOLD = "\033[1;%dm"
    BOLD_SEQ = "\033[1m"

    COLORS = {
        'DEBUG': BLUE,
        'INFO': WHITE,
        'WARNING': YELLOW,
        'CRITICAL': MAGENTA,
        'ERROR': RED
    }

    def __init__(self):
        msg = '%(elapsed).2f %(where)-20s $BOLD%(levelname)-9s$RESET %(message)s'
        msg = msg.replace("$RESET", ColoredFormatter.RESET_SEQ).replace(
            "$BOLD", ColoredFormatter.BOLD_SEQ)
        logging.Formatter.__init__(self, fmt=msg)

    @staticmethod
    def colorize(string, color, bold=False):
        cs = ColoredFormatter.COLOR_SEQ_BOLD if bold else ColoredFormatter.COLOR_SEQ
        string = '%s%s%s' % (
            cs % (30 + color), string, ColoredFormatter.RESET_SEQ)
        string = "%-20s" % string
        return string

    def format(self, record):
        levelname = record.levelname
        if levelname in ColoredFormatter.COLORS:
            col = ColoredFormatter.COLORS[levelname]
            record.name = self.colorize(record.name, col, True)
            record.lineno = self.colorize(record.lineno, col, True)
            record.levelname = self.colorize(levelname, col, True)
            record.msg = self.colorize(record.msg, col)
        return logging.Formatter.format(self, record)


def create_logger(level=logging.DEBUG):
    logger = logging.getLogger("collscientiae")
    logger.addFilter(CollScientiaLoggingFilter())
    logger.setLevel(level)
    logger_sh = logging.StreamHandler()
    logger_sh.setLevel(level)
    logger_sh.setFormatter(ColoredFormatter())
    logger.addHandler(logger_sh)
    return logger


def get_yamls(path):
    return get_yaml(path, all=True)


def get_yaml(path, all=False):
    import yaml
    # import codecs
    # stream = codecs.open(path, "r", "utf8")
    stream = open(path, "r")
    if all:
        return yaml.load_all(stream)
    else:
        return yaml.load(stream)


def get_markdown(path):
    import codecs
    stream = codecs.open(path, "r", "utf8")
    return stream.read()
