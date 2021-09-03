#!/usr/bin/python3

import argparse
import asyncio
import json
import logging
import os

import rich
from rich.console import Console
from rich.layout import Layout

from events.EventManager import EventManager
from utils.logger import AutoWorkflowAdapter
from utils.utils import generate_graph, parse_url


class Target:
    def __init__(self):
        self.lock = asyncio.Lock()
        self.stored = {}

    def __repr__(self):
        return json.dumps(self.stored, sort_keys=True, indent=4)


async def start(target, logger, workflow, status):
    logger.status = status
    try:
        event_manager = EventManager(target, logger, workflow)
        await event_manager.new_event("START")
        while True:
            await asyncio.sleep(5)
            if event_manager.tasks or event_manager.listeners:
                workaround = 0
                to_await = event_manager.tasks + event_manager.listeners
                # await asyncio.gather(*to_await)
                async with event_manager.lock:
                    event_manager.tasks = []
            # else:
            #    workaround +=1
            #    if workaround == 3:
            #        break
    except:
        status.stop()
        tasks = [task for task in asyncio.all_tasks() if task is not
                 asyncio.current_task()]
        list(map(lambda task: task.cancel(), tasks))
    #        traceback.print_exc()
    status.stop()
    logger.info("Done")


def setup_console():
    layout = Layout(name="Autoworkflow")

    layout.split(
        Layout(name="main", ratio=1),
        Layout(name="footer", size=7),
    )
    layout["main"].split(
        Layout(name="side"),
        Layout(name="body", ratio=2, minimum_size=60)
    )
    return layout


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AutoWorkflow - Automate tools chaining as part of a workflow")
    parser.add_argument('-d', '--debug', action='store_true', help='Enable debug output')
    parser.add_argument('-i', '--ip', action='store', help='Target IP')
    parser.add_argument('-u', '--url', action='store', help='Target URL')
    parser.add_argument('-e', '--env', action='store', help='Environment file to add at start')
    parser.add_argument('-w', '--workflow', action='store', help='Workflow to follow', required=True)
    parser.add_argument('--visualize', action='store_true')
    args = parser.parse_args()
    if args.visualize:
        generate_graph(args.workflow)
        exit(0)
    level = logging.INFO
    if args.debug:
        level = logging.DEBUG
    console = Console()
    logger = AutoWorkflowAdapter(console, level=level)
    target = Target()
    if args.env:
        with open(args.env) as f:
            target.stored = json.loads(f.read())
    if not (args.url or args.ip):
        logger.error("URL or IP needs to be provided")
        exit(0)
    if args.url:
        domain, top_domain, base_url = parse_url(args.url)
        target_id = domain
        output_dir = os.path.join(os.getcwd(), 'output', target_id, '')
        if os.path.exists(os.path.join(output_dir, 'stored_values.txt')):
            with open(os.path.join(output_dir, 'stored_values.txt'), 'r') as f:
                target.stored = json.load(f)
                logger.info(f"Loaded existing configuration")
        else:
            target.stored['url'] = args.url
            target.stored['domain'] = domain
            target.stored['top_domain'] = top_domain
            target.stored['base_url'] = base_url
            target.stored['output_dir'] = output_dir
    if args.ip:
        target_id = args.ip
        output_dir = os.path.join(os.getcwd(), 'output', target_id, '')
        if os.path.exists(os.path.join(output_dir, 'stored_values.txt')):
            with open(os.path.join(output_dir, 'stored_values.txt'), 'r') as f:
                target.stored = json.load(f)
                logger.info(f"Loaded existing configuration")
                logger.info(json.dumps(target.stored))
        else:
            target.stored['ip'] = args.ip
            target.stored['output_dir'] = output_dir

    try:
        os.makedirs(output_dir)
    except FileExistsError:
        logger.debug("Directory already exists")
    logger.info(f"Output dir: {output_dir}")
    try:
        with console.status("Starting....") as status:
            asyncio.run(start(target, logger, args.workflow, status), debug=0)
    except KeyboardInterrupt:
        logger.info("User interrupted")
    finally:
        logger.success(f"{target}")
