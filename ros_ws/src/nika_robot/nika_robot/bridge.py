import json
import os
from pathlib import Path
import threading
import time
import paho.mqtt.client as mqtt
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from .core import BASE, aggregate, discoveries

class Bridge(Node):
    def __init__(self):
        super().__init__('nika_server_bridge')
        self.samples = {}
        self.connected = threading.Event()
        self.rediscover = threading.Event()
        self.subscriptions_owned = [self.create_subscription(
            String, '/nika/' + name, lambda msg, key=name: self.receive(key, msg), 10
        ) for name in ('diagnostics', 'motion', 'odometry')]
        self.client = mqtt.Client(client_id='nika-khadas-vim3l', protocol=mqtt.MQTTv311)
        password_file = os.environ['MQTT_PASSWORD_FILE']
        self.client.username_pw_set(os.environ['MQTT_USERNAME'], Path(password_file).read_text().rstrip('\r\n'))
        if os.environ.get('MQTT_CA_FILE'):
            self.client.tls_set(ca_certs=os.environ['MQTT_CA_FILE'])
        self.client.will_set(BASE + '/availability', 'offline', qos=1, retain=True)
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message
        self.client.reconnect_delay_set(1, 30)
        self.client.connect_async(os.environ['MQTT_HOST'], int(os.environ.get('MQTT_PORT', '1883')), 20)
        self.client.loop_start()
        self.create_timer(3.0, self.tick)

    def receive(self, key, msg):
        try:
            value = json.loads(msg.data)
            if isinstance(value, dict):
                self.samples[key] = (time.monotonic(), value)
        except (ValueError, TypeError):
            self.get_logger().warning('Invalid diagnostic message')

    def on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            self.connected.set()
            self.rediscover.set()
            client.subscribe('homeassistant/status', qos=1)

    def on_disconnect(self, client, userdata, rc, properties=None):
        self.connected.clear()

    def on_message(self, client, userdata, msg):
        if msg.topic == 'homeassistant/status' and msg.payload == b'online':
            self.rediscover.set()

    def tick(self):
        if not self.connected.is_set():
            return
        if self.rediscover.is_set():
            self.rediscover.clear()
            for topic, config in discoveries():
                self.client.publish(topic, json.dumps(config), qos=1, retain=True)
        self.client.publish(BASE + '/state', json.dumps(aggregate(self.samples), allow_nan=False), qos=1, retain=False)
        self.client.publish(BASE + '/availability', 'online', qos=1, retain=True)

    def close(self):
        if self.connected.is_set():
            self.client.publish(BASE + '/availability', 'offline', qos=1, retain=True).wait_for_publish(timeout=2)
        self.client.disconnect()
        self.client.loop_stop()

def main():
    rclpy.init()
    node = Bridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.close()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
