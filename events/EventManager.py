import asyncio
import json
import os

import aiofiles
import toml

from utils.utils import run_cmd, get_fields, prepare_conf_string, listen


class EventManager:

    def __init__(self, target, logger, workflow):
        self.target = target
        self.tasks = []
        self.waiting = []
        self.events = []
        self.triggered = []
        self.listeners = []
        self.iterators = dict()
        self.logger = logger
        self.lock = asyncio.Lock()
        self.workflow = workflow
        self.load_conf(self.workflow)

    async def launch_command(self, event_action, kwargs=None):
        storage = self.target.stored.copy()

        if kwargs is not None:
            storage.update(kwargs)
        # We get the required arguments in command, and compare it with what we have. If something's missing, command
        # is not executed, and missing info are returned
        missing_prerequisites = list(set(get_fields(event_action['cmd'])) - set(storage.keys()))

        if not missing_prerequisites:
            async with self.lock:
                # Adding event action to event list, to check if already happened for run_once events
                self.events.append(event_action['name'])
                # Make a copy to format command in copy, but not in original
                event_action_cpy = event_action.copy()
                event_action_cpy['cmd'] = prepare_conf_string(event_action_cpy['cmd'], storage)
                # Run event action
                self.tasks.append(asyncio.create_task(run_cmd(event_action_cpy, self.target, self, self.logger, storage)))
                self.logger.nb_tasks = len([t for t in self.tasks if not t.cancelled() and not t.done()])
                # Log executed commands in commands.txt
                async with aiofiles.open(os.path.join(self.target.stored['output_dir'], 'commands.txt'), mode='a') as f:
                    await f.write(f"{event_action_cpy['cmd']}\n{'-' * 80}\n")
        return missing_prerequisites

    async def new_event(self, event_name):
        self.triggered.append(event_name)
        event_actions = self.workflow.get(event_name, [])
        self.logger.event(event_name)
        for event_action in list(event_actions):
            if "run_once" in event_action and event_action['run_once'] and event_action['name'] in self.events:
                self.logger.debug(f"Command {event_action['name']} already happened")
            else:
                missing_prerequisites = []
                if "iterate_over" in event_action and event_action['name'] not in self.events:
                    self.logger.info("{} has been triggered, and will iterate over {}".format((event_action['name']), event_action['iterate_over']))
                    for iterator_values in self.target.stored[event_action['iterate_over']]:
                        missing_prerequisites = await self.launch_command(event_action, {'array_element': iterator_values})
                elif "iterate_over" not in event_action:
                    missing_prerequisites = await self.launch_command(event_action)
                else:
                    continue
                if missing_prerequisites:
                    self.logger.error(f"Not yet the time for {event_action['name']} - Lacking {missing_prerequisites}")
                    self.waiting.append(event_action)

    async def store(self, key, to_store):
        self.logger.added(f"Added value - {key}:", to_store)
        self.target.stored[key] = to_store
        for event_action in list(self.waiting):
            missing_prerequisites = await self.launch_command(event_action)
            if not missing_prerequisites:
                self.waiting.remove(event_action)

    async def append(self, array, to_store):
        if array not in self.target.stored.keys():
            self.target.stored[array] = []
        test = to_store.upper() if isinstance(to_store, str) else to_store
        if test not in [e.upper() if isinstance(e, str) else e for e in self.target.stored[array]]:
            self.target.stored[array].append(to_store)
            self.logger.added(f"Added value to array - {array}:", to_store)
            # If we have iterators registered for this array launch commands associated
            if array in self.iterators.keys():
                for event_details in self.iterators[array]:
                    if event_details['trigger'] in self.triggered:
                        missing_prerequisites = await self.launch_command(event_details['event'], {'array_element': to_store})
                        if missing_prerequisites:
                            self.logger.error(f"Not yet the time for {event_details['event']['name']} - Lacking {missing_prerequisites}")
                            self.waiting.append(event_details['event'])

    async def start_listener(self, listener):
        storage = self.target.stored.copy()
        prepared = listener.copy()
        prepared['file'] = prepare_conf_string(prepared['file'], storage)
        if not os.path.exists(prepared['file']):
            with open(prepared['file'], 'a'):
                os.utime(prepared['file'], None)
        async with self.lock:
            self.listeners.append(asyncio.create_task(listen(prepared, self.target, self, self.logger, storage)))
        self.logger.nb_listeners = len(self.listeners)

    def load_conf(self, workflow):
        self.logger.info(f"Loading workflow {self.workflow}")
        workflow = toml.load(os.path.join(os.path.dirname(__file__), f"../conf/{workflow}.toml"))
        self.workflow = dict()
        for event, event_actions in workflow.items():
            if event == "LISTENERS":
                for event_action in event_actions:
                    loop = asyncio.get_event_loop()
                    loop.create_task(self.start_listener(event_action))
            else:
                self.workflow[event] = []
                for event_action in event_actions:
                    # In case we have a command iterating over an array
                    if 'iterate_over' in event_action:
                        event_action_iterator = event_action['iterate_over']
                        if event_action_iterator not in self.iterators.keys():
                            self.iterators[event_action_iterator] = []
                        # Adding the command name to the "iterators" launched everytime an item is added to the array
                        # if the event it depends on was emitted already
                        self.iterators[event_action_iterator].append({"event": event_action, "trigger": event})
                        self.logger.debug(f"Adding iterator {event_action['name']} for {event_action_iterator}")
                    self.workflow[event].append(event_action)
