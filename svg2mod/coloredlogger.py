# A simple modification to the formatter class in the python logger to allow
# ANSI color codes based on the logged message's level

import sys
import logging


class Formatter(logging.Formatter):
    color = {
        logging.CRITICAL: "\033[91m\033[7m", #Set red and swap background and foreground
        logging.ERROR: "\033[91m", #Set red
        logging.WARNING: "\033[93m", #Set yellow
        logging.DEBUG: "\033[90m", #Set dark gray/black
        logging.INFO: "" #Do nothing
    }
    reset = "\033[0m" # Reset the terminal back to default color/emphasis
    def __init__(self, fmt="%(message)s", datefmt=None, style="%"):
        super().__init__(fmt, datefmt, style)

    def format(self, record):
        fmt_org = self._style._fmt
        self._style._fmt = Formatter.color[record.levelno] + fmt_org + Formatter.reset
        result = logging.Formatter.format(self, record)
        self._style._fmt = fmt_org
        return result

# This will split logging messegaes at breakpoint. Anything higher will be sent 
# to sys.stderr and everything else to sys.stdout
def split_logger(logger, formatter=Formatter(), breakpoint=logging.WARNING):
    hdlrerr = logging.StreamHandler(sys.stderr)
    hdlrerr.addFilter(lambda msg: breakpoint <= msg.levelno)

    hdlrout = logging.StreamHandler(sys.stdout)
    hdlrout.addFilter(lambda msg: breakpoint > msg.levelno)

    hdlrerr.setFormatter(formatter)
    hdlrout.setFormatter(formatter)
    logger.addHandler(hdlrerr)
    logger.addHandler(hdlrout)

    