import logging
import sys
import re
import asyncio
import rich
from rich.logging import RichHandler
from termcolor import colored
from datetime import datetime

class AutoWorkflowAdapter(logging.LoggerAdapter):
    nb_tasks = 0
    nb_listeners = 0
    display_bar = False
    status = None

    def __init__(self, console, level=logging.INFO, logger_name='autoworkflow'):
        self.logger = logging.getLogger(logger_name)
        logging.basicConfig(
            level=level,
            format="%(message)s",
            datefmt="[%X]",
            handlers=[RichHandler(console=console, 
                show_level=False, 
                show_path=False)]
        )

    def info(self, msg, *args, **kwargs):
        msg = u'[blue]{}[/] {}'.format("[*]", msg)
        self.logger.info(msg, extra={"markup": True}, *args, **kwargs)
        self.bar()

    def error(self, msg, *args, **kwargs):
        msg = u'[red]{}[/] {}'.format("\[x]", msg)
        self.logger.error(msg, extra={"markup": True}, *args, **kwargs)
        self.bar()

    def debug(self, msg, *args, **kwargs):
        msg = u'{} {}'.format("[d]", msg)
        self.logger.debug(msg, extra={"markup": True}, *args, **kwargs)
        self.bar()

    def success(self, msg, *args, **kwargs):
        msg = u'{} {}'.format("[+]", msg)
        self.logger.info(msg, extra={"markup": True}, *args, **kwargs)
        self.bar()

    def added(self, msg, value, *args, **kwargs):
        msg = u'[green]{}[/] {} [bold white]{}[/]'.format("[+]", msg, value)
        self.logger.info(msg, extra={"markup": True}, *args, **kwargs)
        self.bar()


    def event(self, msg, *args, **kwargs):
        msg = u'[yellow]{}[/] New event: [bold yellow]{}[/]'.format("[!]", msg)
        self.logger.info(msg, extra={"markup": True}, *args, **kwargs)
        self.bar()
    
    def bar(self):
        if self.status:
            self.status.update(f"[green]Tasks: {self.nb_tasks}    Listeners: {self.nb_listeners}    Loop: {len(asyncio.all_tasks())}[/]")

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
