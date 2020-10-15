#!/usr/bin/python3

import asyncio
import logging
import os
import sys
import json
import argparse
from utils.logger import setup_logger, AutoWorkflowAdapter
from utils.utils import generate_graph, parse_url
from events.EventManager import EventManager

class Target:
    def __init__(self):
        self.lock = asyncio.Lock()
        self.stored = {}
    
    def __repr__(self):
        return json.dumps(self.stored, sort_keys=True, indent=4)

async def start(target, logger, workflow):
    print()
    logger.display_bar = True
    #workaround = 0
    try:
        event_manager = EventManager(target, logger, workflow)
        await event_manager.new_event("START")
        while True:
            await asyncio.sleep(5)
            if event_manager.tasks or event_manager.listeners:
                workaround = 0
                to_await = event_manager.tasks + event_manager.listeners
                #await asyncio.gather(*to_await)
                async with event_manager.lock:
                    event_manager.tasks = []
            #else:
            #    workaround +=1
            #    if workaround == 3:
            #        break
    except:
        tasks = [task for task in asyncio.all_tasks() if task is not
             asyncio.current_task()]
        list(map(lambda task: task.cancel(), tasks))
    logger.display_bar = False
    logger.info("Done")

if __name__ == "__main__":
    parser  = argparse.ArgumentParser(description="AutoWorkflow - Automate tools chaining as part of a workflow")
    parser.add_argument('-d', '--debug', action='store_true', help='Enable debug output')
    parser.add_argument('-i', '--ip', action='store', help='Target IP')
    parser.add_argument('-u', '--url', action='store', help='Target URL')
    parser.add_argument('-e', '--env', action='store', help='Environment file to add at start')
    parser.add_argument('-w', '--workflow', action='store', help='Workflow to follow', required=True)
    parser.add_argument('--visualize_graph', action='store_true')
    args = parser.parse_args()
    if args.visualize_graph:
        generate_graph(args.workflow)
        exit(0)
    level = logging.INFO
    if args.debug:
        level = logging.DEBUG
    setup_logger(level=level)
    logger = AutoWorkflowAdapter()
    target = Target()
    if args.env:
        with open(args.env) as f:
            target.stored = json.loads(f.read())
    if args.url :
        domain, top_domain, base_url = parse_url(args.url)
        target_id = domain
        target.stored['url'] = args.url
        target.stored['domain'] = domain
        target.stored['top_domain'] = top_domain
        target.stored['base_url'] = base_url
    if args.ip:
        target_id = args.ip
        target.stored['ip'] = args.ip 
    output_dir = os.path.join(os.getcwd(), 'output', target_id)
    output_dir = os.path.join(output_dir, '')
    target.stored['output_dir'] = output_dir
    try:
        os.makedirs(output_dir)
    except FileExistsError:
        logger.debug("Directory already exists")
    logger.info(f"Output dir: {output_dir}")
    try:
        asyncio.run(start(target, logger, args.workflow), debug=0)
    except KeyboardInterrupt:
        logger.info("User interrupted")
    finally:
        logger.success(f"{target}")

