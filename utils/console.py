import logging
import sys
from datetime import datetime
from rich import box
from rich.logging import RichHandler
from rich.live import Live
from rich.align import Align
from rich.console import Console, RenderGroup
from rich.layout import Layout
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
from time import sleep
from termcolor import colored

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


def setup_logger(level=logging.INFO, log_to_file=False, log_prefix=None, logger_name='autoworkflow'):

    formatter = logging.Formatter("%(message)s")

    streamHandler = logging.StreamHandler(sys.stdout)
    streamHandler.setFormatter(formatter)

    logger = logging.getLogger("rich")
    logger.propagate = False
#    logger.addHandler(RichHandler)

    if log_to_file:
        logger.addHandler(fileHandler)

    logger.setLevel(level)

    return logger




def setup_console():
    layout = Layout(name="Autoworkflow")
    layout.split(
        Layout(name="main", ratio=1),
    )
    layout["main"].split(
        Layout(name="side"),
        Layout(name="body", ratio=2, minimum_size=60),
            direction="horizontal",
    )
    return layout


#logger = setup_logger()
#FORMAT = "%(message)s"
#logging.basicConfig(
#    level="INFO", format=FORMAT, datefmt="[%X]", handlers=[AutoWorkflowAdapter(console=console)]
#)
console = Console()
layout = setup_console()
#layout.get("body").update(Panel(""))
tasks = 1
with Live(layout, console=console) as live:
    logger = AutoWorkflowAdapter(live.console)
    while True:
        tasks += 1
        logger.added("ok", "test")
        sleep(1)



#layout = setup_console()
#output = Text("Starting...")
#layout.get("body").update(Panel(
#    output,
#    title="Output"
#    ))
#with Live(layout, refresh_per_second=10, screen=True) as live:
#    while True:
#        output.append('ok\n')
#        #console.print('ok')
#        sleep(1)
