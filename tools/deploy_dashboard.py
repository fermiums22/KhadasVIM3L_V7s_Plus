"""Create/update only the robot dashboard through HA's live WebSocket API."""
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / 'home-assistant/robot-dashboard.json'
remote = (Path(__file__).parent / 'ha_ws_remote.py').read_text(encoding='utf-8')
remote += '\nconfig = ' + repr(json.loads(CONFIG.read_text(encoding='utf-8'))) + '\n'
remote += '''
from pathlib import Path
from datetime import datetime, timezone
ws=HAWebSocket()
try:
 dashboards=ws.call('lovelace/dashboards/list')
 existing=next((d for d in dashboards if d['url_path']=='nika-robot'),None)
 if existing:
  old=ws.call('lovelace/config',url_path='nika-robot')
  backup=Path('/config/backups/nika-robot-dashboard')
  backup.mkdir(parents=True,exist_ok=True)
  (backup/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'.json')).write_text(json.dumps(old))
 else:
  existing=ws.call('lovelace/dashboards/create',url_path='nika-robot',title='Робот',icon='mdi:robot',show_in_sidebar=True,require_admin=False)
 states=ws.call('get_states')
 live={s['entity_id']:s['state'] for s in states}
 needed=set()
 def collect(x):
  if isinstance(x,dict):
   if isinstance(x.get('entity'),str):needed.add(x['entity'])
   for v in x.values():collect(v)
  elif isinstance(x,list):
   for v in x:collect(v)
 collect(config)
 missing=needed-live.keys()
 if missing:raise RuntimeError('Missing entities: '+str(sorted(missing)))
 ws.call('lovelace/config/save',url_path='nika-robot',config=config)
 actual=ws.call('lovelace/config',url_path='nika-robot')
 assert actual==config,'Saved dashboard differs'
 print(json.dumps({'dashboard':existing,'url':'http://192.168.0.4:8123/nika-robot/overview','entities':{k:live[k] for k in sorted(needed)},'readback_matches':True}))
finally:
 ws.close()
'''
r = subprocess.run(['plink', '-batch', '-i', 'D:/HAOS/ssh/priv_for_haos.ppk',
                    '-hostkey', 'SHA256:/PnlrOOYh9z/qAEKK4qqQJvX/4gTZo8SKVe6CSmmCwg',
                    'root@192.168.0.4', 'python3 -'], input=remote, text=True,
                   encoding='utf-8', capture_output=True, timeout=60)
if r.returncode:
    print(r.stderr)
    raise SystemExit(r.returncode)
result = json.loads(r.stdout)
(ROOT / 'home-assistant/deploy-result.json').write_text(
    json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(result, ensure_ascii=True, indent=2))
