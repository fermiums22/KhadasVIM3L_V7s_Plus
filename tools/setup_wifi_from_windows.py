"""Provision owner's saved WLAN profiles over pinned SSH; never print PSKs."""
import re
import subprocess
from remote import sudo

profiles = []
for ssid, band, priority in [('Fermiums', 'a', 100), ('Fermiums_2.4', 'bg', 50)]:
    result = subprocess.run(['netsh', 'wlan', 'show', 'profile', 'name=' + ssid,
                             'key=clear'], capture_output=True, check=True)
    text = result.stdout.decode('oem', errors='replace')
    match = re.search(r'Key Content\s*:\s*(.+)', text)
    if not match:
        raise RuntimeError('Saved WLAN key unavailable for ' + ssid)
    profiles.append({'id': 'nika-home-' + ('5g' if band == 'a' else '24g'),
                     'ssid': ssid, 'band': band, 'priority': priority,
                     'psk': match.group(1).strip()})

script = '''python3 - <<'PY'
import configparser,os,subprocess,uuid
from pathlib import Path
profiles=PROFILES
for p in profiles:
 path=Path('/etc/NetworkManager/system-connections')/(p['id']+'.nmconnection')
 c=configparser.ConfigParser(interpolation=None)
 if path.exists():
  c.read(path)
  if c.get('wifi','ssid') != p['ssid']: raise RuntimeError('Unexpected existing WLAN profile')
 ident=c.get('connection','uuid',fallback=str(uuid.uuid4()))
 c['connection']={'id':p['id'],'uuid':ident,'type':'wifi','interface-name':'wlan0','autoconnect':'true','autoconnect-priority':str(p['priority'])}
 c['wifi']={'mode':'infrastructure','ssid':p['ssid'],'band':p['band'],'powersave':'2','cloned-mac-address':'permanent'}
 c['wifi-security']={'key-mgmt':'wpa-psk','psk':p['psk']}
 c['ipv4']={'method':'auto','route-metric':'50'}
 c['ipv6']={'method':'auto','route-metric':'50'}
 fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
 os.fchmod(fd,0o600)
 with os.fdopen(fd,'w') as f:c.write(f)
subprocess.run(['nmcli','connection','reload'],check=True)
subprocess.run(['nmcli','--wait','30','connection','up','nika-home-5g'],check=True)
print(subprocess.check_output(['nmcli','-f','GENERAL.STATE,GENERAL.CONNECTION,IP4.ADDRESS','device','show','wlan0'],text=True))
print(subprocess.check_output(['iw','dev','wlan0','link'],text=True))
PY'''.replace('PROFILES', repr(profiles))
result = sudo(script, timeout=50)
print(result.stdout.decode(errors='replace'))
if result.returncode:
    # Remote exceptions never contain the PSK: it is only in stdin, not argv.
    print(result.stderr.decode(errors='replace'))
    raise SystemExit(result.returncode)
