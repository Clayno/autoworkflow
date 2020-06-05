import asyncio
import logging
import toml
from base64 import b64decode
from utils.utils import run_cmd, get_fields, prepare_conf_string

class EventManager:

    def __init__(self, target, logger, workflow):
        self.target = target
        self.tasks = []
        self.waiting = []
        self.events = []
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
        return sub

    async def new_event(self, event_name):
        elements = self.workflow.get(event_name, [])
        for element in elements:
            if "run_once" in element and element['run_once'] and element['name'] in self.events:
                self.logger.debug(f"Command {element['name']} already happened")
            else:
                self.logger.highlight(f'New event: {event_name}') 
                sub = await self.launch_command(element)
                if sub:
                    self.logger.error(f"Not yet the time for {element['name']} - Lacking {sub}")
                    self.waiting.append(element)
    
    async def store(self, key, to_store):
        self.logger.success(f"Added value - {key}: {to_store}")  
        self.target.stored[key] = to_store
        for element in self.waiting:
            sub = await self.launch_command(element)
            if not sub:
                self.waiting.remove(element)

    async def append(self, array, to_store):
        if array not in self.target.stored.keys():
            self.target.stored[array] = []
        if to_store not in self.target.stored[array]:
            self.target.stored[array].append(to_store)
            self.logger.success(f"Added value to array - {array}: {to_store}")  
            # If we have iterators registered for this array launch commands associated
            if array in self.iterators.keys():
                for element in self.iterators[array]:
                    sub = await self.launch_command(element, {'array_element': to_store})
                    if sub:
                        self.logger.error(f"Not yet the time for {element['name']} - Lacking {sub}")
                        self.waiting.append(element)

    def load_conf(self, workflow):
        self.logger.info(f"Loading workflow {self.workflow}")
        workflow = toml.load(f"conf/{workflow}.toml")
        commands = toml.load(f"conf/commands.toml")
        for key, command in commands.items():
            base64 = command.get("base64", None)
            if base64:
                commands[key]['cmd'] = b64decode(command['cmd']).decode('utf-8')
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
