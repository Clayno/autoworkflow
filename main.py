#!/usr/bin/python3

import asyncio
import logging
import os
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
    event_manager = EventManager(target, logger, workflow)
    await event_manager.new_event("START")
    while True:
        await asyncio.sleep(1)
        if event_manager.tasks:
            logger.info(f"Number of tasks: {len(event_manager.tasks)}")
            await asyncio.gather(*event_manager.tasks)
            async with event_manager.lock:
                event_manager.tasks = []
        else:
            break
    logger.success(f"{target}")
    logger.info("Done")

if __name__ == "__main__":
    parser  = argparse.ArgumentParser(description="AutoWorkflow - Automate tools chaining as part of a workflow")
    parser.add_argument('-d', '--debug', action='store_true', help='Enable debug output')
    parser.add_argument('-i', '--ip', action='store', help='Target IP')
    parser.add_argument('-u', '--url', action='store', help='Target URL')
    parser.add_argument('-w', '--workflow', action='store', help='Workflow to follow', required=True)
    parser.add_argument('-v', '--visualize_graph', action='store_true')
    args = parser.parse_args()
    if args.visualize_graph:
        generate_graph(args.workflow)
        exit(0)
    level = logging.INFO
    if args.debug:
        level = logging.DEBUG
    setup_logger(level=level)
    logger = AutoWorkflowAdapter()
    if args.url :
        domain, top_domain = parse_url(args.url)
        target_id = domain
        target = Target()
        target.stored['url'] = args.url
        target.stored['domain'] = domain
        target.stored['top_domain'] = top_domain
    if args.ip:
        target_id = args.ip
        target = Target()
        target.stored['ip'] = args.ip 
    output_dir = os.path.join(os.getcwd(), 'output', target_id)
    output_dir = os.path.join(output_dir, '')
    target.stored['output_dir'] = output_dir
    try:
        os.makedirs(output_dir)
    except FileExistsError:
        logger.debug("Directory already exists")
    logger.info(f"Output dir: {output_dir}")
    asyncio.run(start(target, logger, args.workflow))
