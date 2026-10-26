"""Pinned SSH transport for the owner's VIM3L. Never print credentials."""
from pathlib import Path
import os
import subprocess

KEY = Path('D:/HAOS/ssh/khadas_vim3l_ed25519')
KNOWN = Path('D:/HAOS/ssh/khadas_vim3l_known_hosts')
PASSWORD = Path('D:/HAOS/ssh/khadas_vim3l_password.txt')
HOST = os.environ.get('KHADAS_SSH_TARGET', 'khadas@192.168.0.125')

def run(command, data=None, timeout=60, capture=True):
    return subprocess.run(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10',
                           '-o', 'UserKnownHostsFile=' + str(KNOWN),
                           '-i', str(KEY), HOST, command], input=data,
                          capture_output=capture, timeout=timeout)

def sudo(script, timeout=60, capture=True):
    password = PASSWORD.read_text().strip()
    return run("sudo -k -S -p '' bash -s", (password + '\n' + script).encode(), timeout, capture)
