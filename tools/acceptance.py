"""Live checks on the actual VIM3L and HA; bounded MQTT outage with rollback."""
import json
from pathlib import Path
import time
from remote import run, sudo
from ha_status import read as ha_read

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / 'acceptance-2026-10-26.json'
evidence = {}

def save():
    REPORT.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding='utf-8')

def wait_ha(predicate, timeout=100):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        snapshot = ha_read()
        if predicate(snapshot):
            return snapshot
        time.sleep(5)
    raise RuntimeError('HA condition not reached')

def ros_state(snapshot):
    return next((s['state'] for s in snapshot['states']
                 if s['attributes'].get('friendly_name', '').endswith('ROS state')), None)

def main():
    before = sudo('runuser -u nika-robot -- bash /opt/nika-robot/verify.sh', timeout=110)
    if before.returncode:
        raise RuntimeError(before.stderr.decode())
    evidence['before'] = json.loads(before.stdout)
    baseline = evidence['before']
    assert baseline['model'] == 'Khadas VIM3L', baseline['model']
    assert baseline['architecture'] == 'aarch64'
    assert baseline['service']['stdout'] == 'active'
    assert baseline['autostart']['stdout'] == 'enabled'
    for name in ('diagnostics', 'motion', 'odometry'):
        assert baseline[name].get('rc') == 0, baseline[name]
    assert all('/nika_' + name in baseline['nodes']['stdout']
               for name in ('diagnostics', 'motion', 'odometry', 'server_bridge'))
    evidence['ha_initial'] = wait_ha(lambda h: len(h['states']) == 8 and ros_state(h) == 'running')
    save()
    print('Real ROS + HA initial checks passed', flush=True)

    # Stop one heartbeat without killing its process; always resume it.
    locate = r'''python3 - <<'PY'
from pathlib import Path
for p in Path('/proc').glob('[0-9]*/cmdline'):
 try:
  args=p.read_bytes().split(b'\0')
  if len(args)>1 and args[1].endswith(b'/lib/nika_robot/motion'):
   print(p.parent.name)
 except OSError: pass
PY'''
    pids = sudo(locate).stdout.decode().split()
    if len(pids) != 1 or not pids[0].isdigit():
        raise RuntimeError('Motion process not uniquely identified')
    pid = pids[0]
    try:
        sudo('kill -STOP ' + pid).check_returncode()
        evidence['ha_heartbeat_stale'] = wait_ha(lambda h: ros_state(h) == 'degraded', 40)
    finally:
        sudo('kill -CONT ' + pid).check_returncode()
    evidence['ha_heartbeat_restored'] = wait_ha(lambda h: ros_state(h) == 'running', 30)
    save()
    print('Stale heartbeat and recovery passed', flush=True)

    rule = '-m owner --uid-owner nika-robot -d 192.168.0.8 -p tcp --dport 1883 -j DROP'
    # A local timer removes the rule even if this Windows process disappears.
    sudo('systemd-run --unit=nika-mqtt-test-recover --on-active=75s /usr/sbin/iptables -D OUTPUT ' + rule).check_returncode()
    try:
        sudo('/usr/sbin/iptables -I OUTPUT ' + rule).check_returncode()
        evidence['ha_mqtt_unavailable'] = wait_ha(
            lambda h: len(h['states']) == 8 and all(s['state'] == 'unavailable' for s in h['states']), 65)
        print('MQTT network outage detected in HA', flush=True)
    finally:
        sudo('/usr/sbin/iptables -D OUTPUT ' + rule + '\nsystemctl stop nika-mqtt-test-recover.timer').check_returncode()
    evidence['ha_mqtt_reconnected'] = wait_ha(lambda h: ros_state(h) == 'running', 70)
    save()
    print('MQTT automatic reconnection passed', flush=True)

    old_boot = evidence['before']['boot_id']
    sudo('systemctl reboot', timeout=20)
    deadline = time.monotonic() + 180
    boot = None
    while time.monotonic() < deadline:
        time.sleep(5)
        r = run('cat /proc/sys/kernel/random/boot_id; systemctl is-active nika-robot', timeout=15)
        lines = r.stdout.decode().splitlines()
        if r.returncode == 0 and len(lines) == 2 and lines[0] != old_boot and lines[1] == 'active':
            boot = lines[0]
            break
    if not boot:
        raise RuntimeError('Reboot recovery did not complete in 180 seconds')
    evidence['boot_id_after'] = boot
    evidence['ha_after_reboot'] = wait_ha(lambda h: ros_state(h) == 'running', 70)
    final = sudo('runuser -u nika-robot -- bash /opt/nika-robot/verify.sh', timeout=110)
    final.check_returncode()
    evidence['after'] = json.loads(final.stdout)
    assert evidence['after']['service']['stdout'] == 'active'
    assert evidence['after']['autostart']['stdout'] == 'enabled'
    save()
    print('Actual reboot, ROS autostart and HA recovery passed', flush=True)

if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        evidence['error'] = str(error)
        save()
        raise
