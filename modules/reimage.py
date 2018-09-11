import sys
import os

data = {"user": "danut",
        "host": "192.168.118.200",
        "port": "65222",
        "password": "123",
        "commands": " " .join(sys.argv[1:])}
commands = "ls"
command = "ssh {user}@{host} -p {port} {commands}"
os.system(command.format(**data))