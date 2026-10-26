"""Pinned SSH transport for the owner's VIM3L. Never print credentials."""
from pathlib import Path
import subprocess

KEY = Path('D:/HAOS/ssh/khadas_vim3l_ed25519')
KNOWN = Path('D:/HAOS/ssh/khadas_vim3l_known_hosts')
PASSWORD = Path('D:/HAOS/ssh/khadas_vim3l_password.txt')
HOST = 'khadas@192.168.0.241'

def run(command, data=None, timeout=60, capture=True):
    return subprocess.run(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10',
                           '-o', 'UserKnownHostsFile=' + str(KNOWN),
                           '-i', str(KEY), HOST, command], input=data,
                          capture_output=capture, timeout=timeout)

def sudo(script, timeout=60, capture=True):
    password = PASSWORD.read_text().strip()
    return run("sudo -k -S -p '' bash -s", (password + '\n' + script).encode(), timeout, capture)
