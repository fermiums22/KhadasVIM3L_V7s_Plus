"""Download via CT103's verified direct WAN, stream to Windows over local SSH."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1] / 'downloads'
URLS = [
    'https://dl.khadas.com/products/vim3/tools/usb-burning-tool-v2.2.0.zip',
    'https://dl.khadas.com/products/vim3l/firmware/ubuntu/emmc/ubuntu-24.04/vim3l-ubuntu-24.04-server-linux-5.15-fenix-1.7.5-250925-emmc.img.xz',
]

def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    for url in URLS:
        target = ROOT / url.rsplit('/', 1)[1]
        manifest = target.with_name(target.name + '.json')
        if target.exists() and manifest.exists():
            with target.open('rb') as f:
                if hashlib.file_digest(f, 'sha256').hexdigest() == json.loads(manifest.read_text())['sha256']:
                    print('Already verified locally:', target.name, flush=True)
                    continue
        remote = '''import socket,subprocess,sys,urllib.request
from urllib.parse import urlsplit
url = URL
class DirectOnly(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,newurl):
  raise RuntimeError('Unexpected redirect; inspect source before downloading')
for result in socket.getaddrinfo(urlsplit(url).hostname,443,type=socket.SOCK_STREAM):
 route=subprocess.check_output(['ip','route','get',result[4][0]],text=True)
 if 'via 192.168.0.1 dev eth0' not in route: raise RuntimeError('Non-direct route: '+route)
 print(route.strip(),file=sys.stderr,flush=True)
op=urllib.request.build_opener(urllib.request.ProxyHandler({}),DirectOnly())
with op.open(url,timeout=60) as response:
 while True:
  chunk=response.read(1024*1024)
  if not chunk: break
  sys.stdout.buffer.write(chunk)
'''.replace('url = URL', 'url = ' + repr(url))
        partial = target.with_name(target.name + '.partial')
        print('Downloading:', target.name, flush=True)
        with partial.open('wb') as output:
            result = subprocess.run([
                'ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10',
                '-i', 'D:/HAOS/proxmox/id_rsa', 'root@192.168.0.2',
                'pct exec 103 -- python3 -'
            ], input=remote.encode(), stdout=output, timeout=1800)
        result.check_returncode()
        with partial.open('rb') as f:
            digest = hashlib.file_digest(f, 'sha256').hexdigest()
        partial.replace(target)
        manifest.write_text(json.dumps({'url': url, 'sha256': digest,
            'bytes': target.stat().st_size, 'route': 'CT103 via 192.168.0.1 dev eth0',
            'verification': 'HTTPS download; local SHA256, not a vendor-signed checksum'}, indent=2))
        print('Saved:', target.name, target.stat().st_size, flush=True)

if __name__ == '__main__':
    main()
