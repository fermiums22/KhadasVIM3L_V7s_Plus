import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'ros_ws/src/nika_robot'))
from nika_robot.core import aggregate, discoveries, read_metrics

class CoreTests(unittest.TestCase):
    def test_no_hardware_or_fake_pose(self):
        state = aggregate({}, now=100)
        self.assertEqual(state['stm32'], 'not_connected')
        self.assertEqual(state['ros'], 'degraded')
        self.assertEqual(state['odometry'], 'unknown')
        self.assertNotIn('position', state)

    def test_stale_samples_are_removed(self):
        samples = {'diagnostics': (99, {'temperature': 48}),
                   'motion': (99, {'state': 'disabled_no_hardware'}),
                   'odometry': (99, {'state': 'unavailable_no_encoders'})}
        self.assertEqual(aggregate(samples, 100)['ros'], 'running')
        expired = aggregate(samples, 115)
        self.assertEqual(expired['ros'], 'degraded')
        self.assertNotIn('temperature', expired)
        self.assertEqual(expired['motion'], 'unknown')

    def test_real_metrics_and_missing_temperature(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root/'meminfo').write_text('MemTotal: 1000 kB\nMemAvailable: 250 kB\n')
            (root/'loadavg').write_text('0.35 0.20 0.10 1/10 123')
            metrics = read_metrics(root, root, folder)
            self.assertIsNone(metrics['temperature'])
            self.assertEqual(metrics['memory_used_percent'], 75)
            self.assertEqual(metrics['load1'], 0.35)
            zone = root/'thermal_zone0'
            zone.mkdir()
            (zone/'type').write_text('cpu-thermal')
            (zone/'temp').write_text('48000')
            self.assertEqual(read_metrics(root, root, folder)['temperature'], 48)
            (zone/'temp').write_text('invalid')
            self.assertIsNone(read_metrics(root, root, folder)['temperature'])

    def test_discovery_has_expiry_and_common_device(self):
        configs = list(discoveries())
        self.assertEqual(len(configs), 8)
        for topic, config in configs:
            self.assertTrue(topic.startswith('homeassistant/sensor/'))
            self.assertEqual(config['expire_after'], 30)
            self.assertEqual(config['device']['identifiers'], ['nika_khadas_vim3l'])
            json.dumps(config, allow_nan=False)

if __name__ == '__main__':
    unittest.main()
