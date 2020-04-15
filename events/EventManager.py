import asyncio
import logging
import json
from utils.utils import run_cmd, get_fields

class EventManager:

    def __init__(self, target, logger, workflow):
        self.target = target
        self.tasks = []
        self.waiting = []
        self.events = []
        self.logger = logger
        self.lock = asyncio.Lock()
        self.workflow = workflow
        self.load_conf(self.workflow)
        
    async def new_event(self, event_name):
        self.logger.highlight(f'New event: {event_name}') 
        elements = self.workflow.get(event_name, [])
        for element in elements:
            if "run_once" in element and element['run_once'] and event_name in self.events:
                self.logger.debug(f"Event {event_name} already happened")
            else:
                sub = list(set(get_fields(element['cmd'])) - set(self.target.stored.keys()))
                if not sub: 
                    async with self.lock:
                        self.events.append(event_name)
                        self.tasks.append(asyncio.create_task(run_cmd(element, self.target, self, self.logger)))
                else:
                    self.logger.error(f"Not yet the time for {element['name']} - Lacking {sub}")
                    self.waiting.append(element)
    
    async def store(self, key, to_store):
        self.logger.success(f"Added value - {key}: {to_store}")  
        self.target.stored[key] = to_store
        for element in self.waiting:
            sub = list(set(get_fields(element['cmd'])) - set(self.target.stored.keys()))
            if sub:
                self.waiting.remove(element)
                async with self.lock:
                    self.tasks.append(asyncio.create_task(run_cmd(element, self.target, self, self.logger)))

    def load_conf(self, workflow):
        self.logger.info(f"Loading workflow {self.workflow}")
        with open(f"conf/{workflow}.json") as f:
            workflow = json.loads(f.read())
        with open(f"conf/commands.json") as f:
            commands = json.loads(f.read())
        self.workflow = {
                event: [
                    {**commands[cmd['name']], **cmd} for cmd in cmds
                    ]
                for event, cmds in workflow.items()               }

        
