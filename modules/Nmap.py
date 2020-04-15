import asyncio
import traceback
import logging
from modules.Module import Module

class Nmap(Module):
    command = "nmap -v -sVC -Pn {target}"

    def __init__(self, target):
        super(Nmap, self).__init__("nmap", target)

    async def _work(self):
        print(self.target.ip)
        print(self.command.format(target=self.target.ip))
        process = await asyncio.create_subprocess_shell(self.command.format(target=self.target.ip), 
                stdout=asyncio.subprocess.PIPE, 
                stderr=asyncio.subprocess.STDOUT, 
                executable='/bin/bash')
        while True:
            line = await process.stdout.readline()
            if line:
                line = str(line.rstrip(), 'utf8', 'ignore')
                print(line)
            else:
                break
        await process.wait()


    def to_html(self):
        return ""

    def to_string(self):
        return ""
