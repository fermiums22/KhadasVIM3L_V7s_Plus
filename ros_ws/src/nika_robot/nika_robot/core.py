"""Linux measurements and HA discovery, independent of ROS/MQTT for testing."""
import os
from pathlib import Path
import shutil
import time

BASE = 'nika/robot/khadas_vim3l'
SENSORS = {
    'temperature': ('CPU temperature', '°C', 'temperature'),
    'load1': ('Load average 1m', None, None),
    'memory_used_percent': ('Memory used', '%', None),
    'disk_used_percent': ('Root disk used', '%', None),
    'ros': ('ROS state', None, None),
    'stm32': ('STM32 link', None, None),
    'motion': ('Motion state', None, None),
    'odometry': ('Odometry state', None, None),
}

def read_metrics(proc=Path('/proc'), thermal=Path('/sys/class/thermal'), disk='/'):
    memory = {}
    for line in (proc / 'meminfo').read_text().splitlines():
        key, value = line.split(':', 1)
        memory[key] = int(value.strip().split()[0])
    temperature = None
    for zone in sorted(thermal.glob('thermal_zone*')):
        try:
            kind = (zone / 'type').read_text().strip().lower()
            if 'cpu' in kind or 'soc' in kind:
                value = float((zone / 'temp').read_text()) / 1000
                if -40 <= value <= 150:
                    temperature = value
                    break
        except (OSError, ValueError):
            continue
    total, used, _ = shutil.disk_usage(disk)
    return {'sample_unix': time.time(), 'temperature': temperature,
            'load1': float((proc / 'loadavg').read_text().split()[0]),
            'memory_used_percent': round(100 * (1 - memory['MemAvailable'] / memory['MemTotal']), 2),
            'disk_used_percent': round(100 * used / total, 2)}

def aggregate(samples, now=None, ttl=15):
    now = time.monotonic() if now is None else now
    fresh = {key: value for key, (received, value) in samples.items()
             if 0 <= now - received < ttl}
    state = dict(fresh.get('diagnostics', {}))
    state['ros'] = 'running' if all(k in fresh for k in ('diagnostics', 'motion', 'odometry')) else 'degraded'
    state['motion'] = fresh.get('motion', {}).get('state', 'unknown')
    state['odometry'] = fresh.get('odometry', {}).get('state', 'unknown')
    # No STM32 transport exists yet. Network connectivity is not hardware connectivity.
    state['stm32'] = 'not_connected'
    return state

def discoveries():
    for key, (name, unit, device_class) in SENSORS.items():
        config = {'name': name, 'unique_id': 'nika_khadas_vim3l_' + key,
                  'state_topic': BASE + '/state',
                  'value_template': '{{ value_json.' + key + ' | default(none) }}',
                  'availability_topic': BASE + '/availability', 'expire_after': 30,
                  'device': {'identifiers': ['nika_khadas_vim3l'],
                             'name': 'Nika Robot / Khadas VIM3L',
                             'manufacturer': 'Khadas', 'model': 'VIM3L'}}
        if unit:
            config['unit_of_measurement'] = unit
        if key in ('temperature', 'load1', 'memory_used_percent', 'disk_used_percent'):
            config['state_class'] = 'measurement'
        if device_class:
            config['device_class'] = device_class
        yield 'homeassistant/sensor/nika_khadas_vim3l/' + key + '/config', config
