import json
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from .core import read_metrics

class StatusNode(Node):
    def __init__(self, name, sample):
        super().__init__('nika_' + name)
        self.sample = sample
        self.publisher = self.create_publisher(String, '/nika/' + name, 10)
        self.create_timer(3.0, self.tick)

    def tick(self):
        try:
            value = self.sample()
        except (OSError, ValueError, KeyError, ZeroDivisionError) as error:
            self.get_logger().error('Measurement failed: ' + type(error).__name__)
            return  # Stop heartbeat; bridge detects stale diagnostics.
        self.publisher.publish(String(data=json.dumps(value, allow_nan=False)))

def run(name, sample):
    rclpy.init()
    node = StatusNode(name, sample)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

def diagnostics():
    run('diagnostics', read_metrics)

def motion():
    # Deliberately no cmd_vel subscription, serial device, GPIO, or motor output.
    run('motion', lambda: {'state': 'disabled_no_hardware'})

def odometry():
    # No /odom or TF until real timestamped encoder measurements are available.
    run('odometry', lambda: {'state': 'unavailable_no_encoders'})
