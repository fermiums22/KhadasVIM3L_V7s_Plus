"""Read HA robot states through its existing SSH add-on. No token export."""
import json
import subprocess

SCRIPT = '''import json,os,urllib.request
from pathlib import Path
req=urllib.request.Request('http://supervisor/core/api/states',headers={'Authorization':'Bearer '+os.environ['SUPERVISOR_TOKEN']})
with urllib.request.urlopen(req,timeout=15) as r: states=json.load(r)
devices=json.loads(Path('/config/.storage/core.device_registry').read_text())['data']['devices']
result={'states':[s for s in states if 'khadas' in s['entity_id']],
        'devices':[{'id':d['id'],'name':d.get('name'),'model':d.get('model'),'manufacturer':d.get('manufacturer')} for d in devices if 'Khadas' in str(d.get('name',''))]}
print(json.dumps(result))
'''

def read():
    r = subprocess.run(['plink', '-batch', '-i', 'D:/HAOS/ssh/priv_for_haos.ppk',
                        '-hostkey', 'SHA256:/PnlrOOYh9z/qAEKK4qqQJvX/4gTZo8SKVe6CSmmCwg',
                        'root@192.168.0.4', 'python3 -'],
                       input=SCRIPT, text=True, capture_output=True, timeout=25, check=True)
    return json.loads(r.stdout)

if __name__ == '__main__':
    print(json.dumps(read(), ensure_ascii=True, indent=2))
