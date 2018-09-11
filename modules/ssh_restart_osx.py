#!/usr/bin/python3

import subprocess
import sys

OSX = "../hosts.txt"
# Ports are handled in ~/.ssh/config since we use OpenSSH
COMMAND = "uname -a"

def restart_osx():
    with open(OSX, 'r', encoding='utf-8') as machines:
        for HOST in machines:
            ssh = subprocess.Popen(["ssh", "%s" % HOST, COMMAND],
                                   shell=False,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
            result = ssh.stdout.readlines()

            if not result:
                error = ssh.stderr.readlines()
                print(sys.stderr, "ERROR: %s" % error)
            else:
                print(result)


if __name__ == "__main__":
    restart_osx()