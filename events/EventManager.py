import asyncio
import aiofiles
import logging
import toml
import os
from base64 import b64decode
from utils.utils import run_cmd, get_fields, prepare_conf_string, listen

class EventManager:

    def __init__(self, target, logger, workflow):
        self.target = target
        self.tasks = []
        self.waiting = []
        self.events = []
        self.listeners = []
        self.iterators = dict()
        self.logger = logger
        self.lock = asyncio.Lock()
        self.workflow = workflow
        self.load_conf(self.workflow)
        
    async def launch_command(self, element, kwargs=None):
        storage = self.target.stored.copy()
        if kwargs != None:
            storage.update(kwargs)
        sub = list(set(get_fields(element['cmd'])) - set(storage.keys()))
        if not sub: 
            async with self.lock:
                self.events.append(element['name'])
                prepared = element.copy()
                prepared['cmd'] = prepare_conf_string(prepared['cmd'], storage)
                self.tasks.append(asyncio.create_task(run_cmd(prepared, self.target, self, self.logger, storage)))
                self.logger.nb_tasks = len([t for t in self.tasks if not t.cancelled() and not t.done()])
                async with aiofiles.open(os.path.join(self.target.stored['output_dir'], 'commands.txt'), mode='a') as f:
                    await f.write(f"{prepared['cmd']}\n\n")
        return sub

    async def new_event(self, event_name):
        elements = self.workflow.get(event_name, [])
        self.logger.event(event_name) 
        for element in elements:
            if "run_once" in element and element['run_once'] and element['name'] in self.events:
                self.logger.debug(f"Command {element['name']} already happened")
            else:
                sub = await self.launch_command(element)
                if sub:
                    self.logger.error(f"Not yet the time for {element['name']} - Lacking {sub}")
                    self.waiting.append(element)
    
    async def store(self, key, to_store):
        self.logger.added(f"Added value - {key}:", to_store)  
        self.target.stored[key] = to_store
        for element in self.waiting:
            sub = await self.launch_command(element)
            if not sub:
                self.waiting.remove(element)

    async def append(self, array, to_store):
        if array not in self.target.stored.keys():
            self.target.stored[array] = [] 
        test = to_store.upper() if isinstance(to_store, str) else to_store
        if test not in [e.upper() if isinstance(e, str) else e for e in self.target.stored[array]]:
            self.target.stored[array].append(to_store)
            self.logger.added(f"Added value to array - {array}:", to_store)  
            # If we have iterators registered for this array launch commands associated
            if array in self.iterators.keys():
                for element in self.iterators[array]:
                    sub = await self.launch_command(element, {'array_element': to_store})
                    if sub:
                        self.logger.error(f"Not yet the time for {element['name']} - Lacking {sub}")
                        self.waiting.append(element)

    async def start_listener(self, listener):
        storage = self.target.stored.copy()
        prepared = listener.copy()
        prepared['file'] = prepare_conf_string(prepared['file'], storage)
        if not os.path.exists(prepared['file']):
            with open(prepared['file'], 'a'):
                os.utime(prepared['file'], None)
        async with self.lock:
            self.listeners.append(asyncio.create_task(listen(prepared, self.target, self, self.logger, storage)))

    def load_conf(self, workflow):
        self.logger.info(f"Loading workflow {self.workflow}")
        workflow = toml.load(os.path.join(os.path.dirname(__file__), f"../conf/{workflow}.toml"))
        commands = toml.load(os.path.join(os.path.dirname(__file__), f"../conf/commands.toml"))
        for key, command in commands.items():
            base64 = command.get("base64", False)
            listener = command.get("listener", False)
            if base64:
                commands[key]['cmd'] = b64decode(command['cmd']).decode('utf-8')
            if listener:
                loop = asyncio.get_event_loop()
                loop.create_task(self.start_listener(commands[key]))
            # In case we have a command iterating over an array
            if 'iterate_over' in command.keys():
                arr =  command['iterate_over'] 
                if arr not in self.iterators.keys():
                    self.iterators[arr] = []
                # Adding the command name to the "iterators" launched everytime an item is added to the array
                self.iterators[arr].append(commands[key])
                self.logger.debug(f"Adding iterator {commands[key]} for {arr}")
                pass
        self.workflow = {
                event: [
                    {**commands[cmd['name']], **cmd} for cmd in cmds
                    ]
                for event, cmds in workflow.items()
                }
