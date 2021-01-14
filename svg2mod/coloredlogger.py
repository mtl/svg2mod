import logging


class Formatter(logging.Formatter):
    color = {
        logging.CRITICAL: "\033[91m\033[7m", #Set red and swap background and foreground
        logging.ERROR: "\033[91m", #Set red
        logging.WARNING: "\033[93m", #Set yellow
        logging.DEBUG: "\033[90m", #Set dark gray/black
        logging.INFO: "" #Do nothing
    }
    reset = "\033[0m"
    def __init__(self, fmt="%(message)s", datefmt=None, style="%"):
        super().__init__(fmt, datefmt, style)

    def format(self, record):
        fmt_org = self._style._fmt
        self._style._fmt = Formatter.color[record.levelno] + fmt_org + Formatter.reset
        result = logging.Formatter.format(self, record)
        self._style._fmt = fmt_org
        return result