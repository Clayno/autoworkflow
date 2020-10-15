import logging
import sys
import re
import asyncio
from termcolor import colored
from datetime import datetime

#The following hooks the FileHandler.emit function to remove ansi chars before logging to a file
#There must be a better way of doing this, but this way we might save some penguins!

ansi_escape = re.compile(r'\x1b[^m]*m')

def antiansi_emit(self, record):

    if self.stream is None:
        self.stream = self._open()

    record.msg = ansi_escape.sub('', record.message)
    logging.StreamHandler.emit(self, record)

logging.FileHandler.emit = antiansi_emit

####################################################################

class AutoWorkflowAdapter(logging.LoggerAdapter):
    nb_tasks = 0
    nb_listeners = 0
    display_bar = False

    def __init__(self, logger_name='autoworkflow'):
        self.logger = logging.getLogger(logger_name)

    def info(self, msg, *args, **kwargs):
        if self.display_bar:
            sys.stdout.write('\033[F')
            sys.stdout.write('\033[K')
        msg = u'{} {}'.format(colored("[*]", 'blue', attrs=['bold']), msg)
        self.logger.info(msg, *args, **kwargs)
        if self.display_bar:
            sys.stdout.flush()
            self.bar()

    def error(self, msg, *args, **kwargs):
        if self.display_bar:
            sys.stdout.write('\033[F')
            sys.stdout.write('\033[K')
        msg = u'{} {}'.format(colored("[x]", 'red', attrs=['bold']), msg)
        self.logger.error(msg, *args, **kwargs)
        if self.display_bar:
            sys.stdout.flush()
            self.bar()

    def debug(self, msg, *args, **kwargs):
        if self.display_bar:
            sys.stdout.write('\033[F')
            sys.stdout.write('\033[K')
        msg = u'{} {}'.format(colored("[d]", 'green'), msg)
        self.logger.debug(msg, *args, **kwargs)
        if self.display_bar:
            sys.stdout.flush()
            self.bar()

    def success(self, msg, *args, **kwargs):
        if self.display_bar:
            sys.stdout.write('\033[F')
            sys.stdout.write('\033[K')
        msg = u'{} {}'.format(colored("[+]", 'green', attrs=['bold']), msg)
        self.logger.info(msg, *args, **kwargs)
        if self.display_bar:
            sys.stdout.flush()
            self.bar()

    def added(self, msg, value, *args, **kwargs):
        if self.display_bar:
            sys.stdout.write('\033[F')
            sys.stdout.write('\033[K')
        msg = u'{} {} {}'.format(colored("[+]", 'green', attrs=['bold']), msg, 
                colored(value, 'white', attrs=['bold']))
        self.logger.info(msg, *args, **kwargs)
        if self.display_bar:
            sys.stdout.flush()
            self.bar()


    def event(self, msg, *args, **kwargs):
        if self.display_bar:
            sys.stdout.write('\033[F')
            sys.stdout.write('\033[K')
        msg = u'{} New event: {}'.format(colored("[!]", 'yellow', attrs=['bold']), 
                colored(msg, 'yellow', attrs=['bold']))
        self.logger.info(msg, *args, **kwargs)
        if self.display_bar:
            sys.stdout.flush()
            self.bar()
    
    def bar(self):
        print(colored(f"Tasks: {self.nb_tasks}    Listeners: {self.nb_listeners}    Loop: {len(asyncio.all_tasks())}", 'white', 'on_grey'))

def setup_debug_logger():
    debug_output_string = "{} %(message)s".format(colored('DEBUG', 'magenta', attrs=['bold']))
    formatter = logging.Formatter(debug_output_string)
    streamHandler = logging.StreamHandler(sys.stdout)
    streamHandler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.propagate = False
    root_logger.addHandler(streamHandler)
    #root_logger.addHandler(fileHandler)
    root_logger.setLevel(logging.DEBUG)
    return root_logger

def setup_logger(level=logging.INFO, log_to_file=False, log_prefix=None, logger_name='autoworkflow'):

    formatter = logging.Formatter("%(message)s")

    if log_to_file:
        if not log_prefix:
            log_prefix = 'log'

        log_filename = '{}_{}.log'.format(log_prefix.replace('/', '_'), datetime.now().strftime('%Y-%m-%d'))
        fileHandler = logging.FileHandler('./logs/{}'.format(log_filename))
        fileHandler.setFormatter(formatter)

    streamHandler = logging.StreamHandler(sys.stdout)
    streamHandler.setFormatter(formatter)

    logger = logging.getLogger(logger_name)
    logger.propagate = False
    logger.addHandler(streamHandler)

    if log_to_file:
        logger.addHandler(fileHandler)

    logger.setLevel(level)

    return logger
