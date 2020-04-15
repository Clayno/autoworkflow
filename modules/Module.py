import asyncio
import traceback
import logging

logger = logging.getLogger('autochain')

class ModuleNotFinished(Exception):
    pass

class Module:
    def __init__(self, name, target):
        self.name = name
        self.status = None
        self.target = target

    async def run(self):
        try:
            self.status = 'started'
            logger.info(f"[{self.target.ip}] We are starting {self.name} module")
            await self._work()
            logger.info(f"[{self.target.ip}] Ending {self.name} module")
            self.status = 'terminated'
        except:
            self.status = 'error'
            traceback.print_exc()
            raise Exception()

    async def _work(self):
        raise NotImplementedError("A Module class needs to implement a _work method.")

    def to_html(self):
        return ""

    def to_string(self):
        return ""
