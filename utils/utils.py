import asyncio
import logging
import json
import re
from string import Formatter

def get_conf(module_name):
    with open("conf/modules.json") as f:
        conf = json.loads(f.read())
    return conf.get(module_name)

async def launch_module(module_name, target):
    module_class = getattr(__import__(f'modules.{module_name}',
            fromlist=[module_name]), module_name)
    return module_class(target)

def prepare_conf_string(string, target):
    return string.format(**target.stored)

def get_fields(string):
    """
    Return the fields contained in the given string.
    fields in "{test}" is test ;)
    """
    return [i[1] for i in Formatter().parse(string) if i[1]]

async def run_cmd(element, target, event_manager, logger):
    cmd = prepare_conf_string(element['cmd'], target)
    logger.info(f"Starting {element['name']}: {cmd}")
    process = await asyncio.create_subprocess_shell(cmd, 
            stdout=asyncio.subprocess.PIPE, 
            stderr=asyncio.subprocess.STDOUT, 
            executable='/bin/bash')
    # Add all static variables configured
    if 'store_static' in element.keys():
        for dictionnary in element['store_static']:
            for key, to_store in dictionnary.items():
                async with target.lock:
                    to_store = prepare_conf_string(to_store, target)
                    await event_manager.store(key, to_store)
    while True:
        line = await process.stdout.readline()
        if line:
            line = str(line.rstrip(), 'utf8', 'ignore')
            logger.debug(line)
            # Check if a regex match meaning we have to store something
            if 'store' in element.keys():
                for dictionnary in element['store']:
                    for key, regex in dictionnary.items():
                        match = re.findall(regex, line)
                        if match:
                            async with target.lock:
                                await event_manager.store(key, match[0])
            # Check if a pattern launching a new event is detected
            if 'patterns' in element.keys():
                for dictionnary in element['patterns']:
                    for pattern, events in dictionnary.items():
                        matches = re.findall(pattern, line)
                        if matches:
                            for event in events:
                                await event_manager.new_event(event)
        else:
            break
    await process.wait()
    logger.info(f"Ending {element['name']}")

def generate_graph(workflow):
    import json
    from graphviz import Digraph
    dot = Digraph(comment='Workflow', format='png')
    workflow = json.loads(open(f"conf/{workflow}.json").read())
    commands = json.loads(open("conf/commands.json").read())
    workflow = {
        event: [
            {**commands[cmd['name']], **cmd} for cmd in cmds
        ]
        for event, cmds in workflow.items()
    }
    edges = set()
    for event, commands in workflow.items():
        dot.node(event)
        for command in commands:
            for pattern in command.get('patterns', []):
                for events_to_fire in pattern.values():
                    for event_to_fire in events_to_fire:
                        edges.add((event, event_to_fire))
    for edge in edges:
        dot.edge(edge[0], edge[1])
    dot.render('workflow.gv', view=True)
