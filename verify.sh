#!/usr/bin/env bash
# Run as nika-robot (sudo -u nika-robot bash /opt/nika-robot/verify.sh).
set -eo pipefail
source /opt/ros/jazzy/setup.bash
source /opt/nika-robot/ros_ws/install/setup.bash
export ROS_DOMAIN_ID=73
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
python3 - <<'PY'
import json, os, pathlib, platform, subprocess, time
def command(args):
    try:
        p = subprocess.run(args, text=True, capture_output=True, timeout=20)
        return {'rc': p.returncode, 'stdout': p.stdout.strip(), 'stderr': p.stderr.strip()}
    except subprocess.TimeoutExpired:
        return {'error': 'timeout'}
p = pathlib.Path
print(json.dumps({
    'captured_unix': time.time(),
    'model': p('/proc/device-tree/model').read_text().strip('\0'),
    'architecture': platform.machine(),
    'os': p('/etc/os-release').read_text(),
    'boot_id': p('/proc/sys/kernel/random/boot_id').read_text().strip(),
    'root_mount': command(['findmnt', '-no', 'SOURCE,FSTYPE', '/']),
    'block_devices': command(['lsblk', '-o', 'NAME,TYPE,SIZE,MOUNTPOINTS']),
    'service': command(['systemctl', 'is-active', 'nika-robot']),
    'autostart': command(['systemctl', 'is-enabled', 'nika-robot']),
    'nodes': command(['ros2', 'node', 'list', '--no-daemon', '--spin-time', '5']),
    'diagnostics': command(['ros2', 'topic', 'echo', '/nika/diagnostics', '--once', '--full-length']),
    'motion': command(['ros2', 'topic', 'echo', '/nika/motion', '--once']),
    'odometry': command(['ros2', 'topic', 'echo', '/nika/odometry', '--once']),
}, ensure_ascii=False, indent=2))
PY
