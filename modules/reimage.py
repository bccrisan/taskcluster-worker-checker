import paramiko

data = {"username": "danut",
        "hostname": "192.168.118.200",
        "port": "65222",
        "password": "123"}

mdc2_range = list(range(21, 237))
mdc1_range = list(range(237, 473))

mdc1_command = "ls"
mdc2_command = "w"
reboot_command = "sudo reboot now"

mdc1_fqdn = "{}.test.releng.mdc1.mozilla.com"
mdc2_fqdn = "{}.test.releng.mdc2.mozilla.com"

def question_loop():
    with open("hosts.txt") as hosts:
            for host in hosts:
                if host:
                    helptxt = "Answer with 'y'/'n' for reimage, 'r' for reboot or 'e' to exit application\n"
                    reply = input("Reimage {}".format(host) + helptxt)

                    if reply[:1] == "y":
                        if int(host[-3:]) <= int(mdc2_range[-1]):
                            try:
                                ssh = paramiko.SSHClient()
                                ssh.load_system_host_keys()
                                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                                ssh.connect(mdc2_fqdn.format(host.split("\n")[0]))
                                stdin, stdout, stderr = ssh.exec_command(mdc1_command)
                                print(stdout.read().decode())
                                ssh.close()
                            finally:
                                pass

                        else:
                            try:
                                ssh = paramiko.SSHClient()
                                ssh.load_system_host_keys()
                                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                                ssh.connect(mdc1_fqdn.format(host.split("\n")[0]))
                                stdin, stdout, stderr = ssh.exec_command(mdc2_command)
                                print(stdout.read().decode())
                                ssh.close()
                            finally:
                                pass
                    elif reply[:1] == "n":
                        print("Skipping ".format(host))

                    elif reply[:1] == "r":
                        if int(host[-3:]) <= int(mdc2_range[-1]):
                            try:
                                ssh = paramiko.SSHClient()
                                ssh.load_system_host_keys()
                                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                                ssh.connect(mdc2_fqdn.format(host.split("\n")[0]))
                                stdin, stdout, stderr = ssh.exec_command(reboot_command)
                                print(stdout.read().decode())
                                ssh.close()
                            finally:
                                pass

                        else:
                            try:
                                ssh = paramiko.SSHClient()
                                ssh.load_system_host_keys()
                                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                                ssh.connect(mdc1_fqdn.format(host.split("\n")[0]))
                                stdin, stdout, stderr = ssh.exec_command(reboot_command)
                                print(stdout.read().decode())
                                ssh.close()
                            finally:
                                pass

                    elif reply[:1] == "e":
                        print("Exiting application.")
                        exit(0)
                else:
                    print("No more ")

if __name__ == "__main__":
    question_loop()